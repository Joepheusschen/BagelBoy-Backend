from flask import Flask, request, render_template
import os
import json
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Setup voor Google Sheets (via environment variable)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("HR BagelBoy Database").sheet1  # Naam van je spreadsheet

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    # Gegevens uit het formulier
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    location = request.form.get('location')
    motivation = request.form.get('motivation')
    salary = request.form.get('salary')
    availability = request.form.get('availability')

    # 1. Voeg toe aan Google Sheet
    sheet.append_row([name, email, phone, location, motivation, salary, availability])

    # 2. Bevestigingsmail naar sollicitant
    subject = "Application received – BagelBoy"
    body = f"""Hi {name},

Thanks for your application – we’ll be in touch as soon as possible!

Have a great day,
BagelBoy HR"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_SENDER"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

    # 3. Interne mail naar jezelf
    internal_subject = f"New application from {name}"
    internal_body = f"""
New application received:

Name: {name}
Email: {email}
Phone: {phone}
Location: {location}

Motivation:
{motivation}

Salary expectation: {salary}
Availability: {availability}
"""
    internal_msg = MIMEText(internal_body)
    internal_msg["Subject"] = internal_subject
    internal_msg["From"] = os.environ["EMAIL_SENDER"]
    internal_msg["To"] = os.environ["EMAIL_RECEIVER"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_SENDER"], os.environ["EMAIL_PASSWORD"])
        server.send_message(internal_msg)

    return render_template("thankyou.html")

if __name__ == '__main__':
    app.run(debug=True)
