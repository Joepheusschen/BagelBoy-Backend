from flask import Flask, request, render_template
import os
import json
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Setup voor Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("HR BagelBoy Database").sheet1

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    # Gegevens uit formulier
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    position = request.form.get('position')
    hours = request.form.get('hours')
    weekend = request.form.get('weekend')
    motivation = request.form.get('motivation')

    # Toevoegen aan Google Sheet (Status altijd 'New')
    sheet.append_row([first_name, last_name, email, phone, position, hours, weekend, motivation, "New"])

    # Bevestiging naar sollicitant
    subject = "We received your application – BagelBoy"
    body = f"""Hi {first_name},

Thanks for applying at BagelBoy as a {position} 🍳

We’ll be in touch with you as soon as possible.

Have a great day,
BagelBoy HR
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_SENDER"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

    # Interne melding
    internal_subject = f"New application: {first_name} {last_name}"
    internal_body = f"""
New application received:

Name: {first_name} {last_name}
Email: {email}
Phone: {phone}
Position: {position}
Hours/week: {hours}
Weekend availability: {weekend}

Motivation:
{motivation}
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
