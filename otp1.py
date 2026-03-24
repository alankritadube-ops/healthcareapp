from flask import Flask, render_template, request, redirect, url_for, session
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ssl import create_default_context
from datetime import datetime, timedelta
import os
print("Current Working Directory:", os.getcwd())
app = Flask(__name__)
app.secret_key = "supersecretkey"
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
# ================= EMAIL CONFIG =================
# Set these in terminal before running:
# set SENDER_EMAIL=yourgmail@gmail.com
# set APP_PASSWORD=your_app_password

SENDER_EMAIL = "alankritadube@gmail.com"
APP_PASSWORD = "ddrc ejyu htgc indq"


# ================= OTP GENERATOR =================
def generate_otp():
    return str(random.randint(100000, 999999))


# ================= SEND EMAIL FUNCTION =================
def send_otp_email(receiver, otp):
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = receiver
    message["Subject"] = "Your OTP Verification Code"

    body = f"""
    Hello,

    Your One-Time Password (OTP) is: {otp}

    This OTP is valid for 5 minutes.

    Thank you.
    """

    message.attach(MIMEText(body, "plain"))

    context = create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(message)


# ================= ROUTES =================

@app.route('/')
def login():
    return render_template('login_page.html')


@app.route('/send-otp', methods=['POST'])
def send_otp():

    now = datetime.now()

    # If OTP was already sent
    if session.get('otp_sent_time'):
        last_sent_time = datetime.strptime(
            session['otp_sent_time'], "%Y-%m-%d %H:%M:%S"
        )

        if (now - last_sent_time).total_seconds() < 60:
            return render_template(
                "otp.html",
                error="Please wait 1 minute before requesting a new OTP."
            )

    email = request.form['email']
    password = request.form['password']

    user = User.query.filter_by(email=email).first()

    if not user:
        return "User not found!"

    if not bcrypt.check_password_hash(user.password, password):
        return "Incorrect password!"

    username = user.first_name
    otp = generate_otp()

    session['otp'] = otp
    session['email'] = email
    session['otp_expiry'] = (now + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    session['otp_sent_time'] = now.strftime("%Y-%m-%d %H:%M:%S")

    send_otp_email(email, otp)
    session['username'] = username

    return render_template("otp.html", success="OTP sent successfully!")

@app.route('/otp')
def otp_page():
    return render_template('otp.html')


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    user_otp = request.form['otp']
    stored_otp = session.get('otp')
    otp_expiry = session.get('otp_expiry')

    # 🔴 If session data missing
    if not stored_otp or not otp_expiry:
        return redirect(url_for('login'))

    expiry_time = datetime.strptime(otp_expiry, "%Y-%m-%d %H:%M:%S")

    if datetime.now() > expiry_time:
        session.clear()
        return "OTP Expired! Please login again."

    if user_otp == stored_otp:
        return redirect(url_for('dashboard'))
    else:
        return render_template("otp.html", error="Invalid OTP! Try again.")
@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    return render_template('dashboard.html', username=username)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match!"

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "User already exists!"

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template("mini_project.html")

@app.route('/emergency')
def emergency():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('emergency.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/symptom-checker', methods=['GET', 'POST'])
def symptom_checker():

    if request.method == 'POST':
        selected_symptoms = request.form.getlist('symptoms')

        disease_data = {
            "Flu": ["fever", "cough", "body pain"],
            "Common Cold": ["cough", "sneezing", "runny nose"],
            "COVID-19": ["fever", "cough", "loss of smell"],
            "Malaria": ["fever", "chills", "sweating"]
        }

        best_disease = None
        highest_accuracy = 0

        for disease, symptoms in disease_data.items():
            match_count = len(set(selected_symptoms) & set(symptoms))
            accuracy = (match_count / len(symptoms)) * 100

            if accuracy > highest_accuracy:
                highest_accuracy = accuracy
                best_disease = disease

        return render_template(
            "symptom_checker.html",
            disease=best_disease,
            accuracy=round(highest_accuracy, 2)
        )

    return render_template("symptom_checker.html")

@app.route('/appointments')
def appointments():
    return render_template('appointments.html')

@app.route('/records')
def records():
    return render_template('records.html')

@app.route('/prescriptions')
def prescriptions():
    return render_template('prescriptions.html')

@app.route('/health-tips')
def health_tips():
    return render_template('health_tips.html')

@app.route('/check-users')
def check_users():
    users = User.query.all()
    return "<br>".join([user.email for user in users])

@app.route('/debug-users')
def debug_users():
    users = User.query.all()
    return "<br>".join([f"{u.first_name} - {u.email}" for u in users])
with app.app_context():
    db.create_all()
if __name__ == '__main__':
    app.run(debug=True)
