from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
import smtplib
from email.mime.text import MIMEText
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import unquote
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# Google Sheets Setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("HR BagelBoy Database").sheet1
JOEP_EMAIL = "joepheusschen@gmail.com"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    position = request.form.get('position')
    hours = request.form.get('hours')
    weekend = request.form.get('weekend')
    motivation = request.form.get('motivation')

    sheet.append_row([
        first_name,
        last_name,
        email,
        phone,
        position,
        hours,
        weekend,
        motivation,
        "New"
    ])

    subject = "We received your application – BagelBoy"
    body = f"""Hi {first_name},\n\nThanks for applying at BagelBoy as a {position} 🥯\n\nWe’ll be in touch with you as soon as possible.\n\nHave a great day,\nBagelBoy HR"""
    send_email(subject, body, email)

    internal_body = f"New application:\n{first_name} {last_name}, {email}, {phone}, {position}"
    send_email(f"New application from {first_name} {last_name}", internal_body, os.environ["EMAIL_RECEIVER"])

    return render_template("thankyou.html")

@app.route('/schedule/<int:row_id>', methods=['GET', 'POST'])
def schedule(row_id):
    try:
        if request.method == 'GET':
            row = sheet.row_values(row_id)
            if not row:
                return "Invalid row ID", 404
            return render_template("schedule.html", row_id=row_id, first_name=row[0], last_name=row[1], email=row[2])

        if request.method == 'POST':
            date_str = request.form.get('date')
            time_str = request.form.get('time')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')

            logging.debug(f"Received: {date_str=} {time_str=} {first_name=} {last_name=} {email=}")

            if not all([date_str, time_str, first_name, last_name, email]):
                return "Missing data", 400

            subject = "Your appointment is scheduled – BagelBoy"
            body = f"""Hi {first_name},\n\nYour appointment has been scheduled for {date_str} at {time_str}.\n\nSee you then!\n\nBagelBoy HR"""
            send_email(subject, body, email)

            internal = f"Appointment scheduled for {first_name} {last_name} on {date_str} at {time_str}."
            send_email("New appointment scheduled", internal, JOEP_EMAIL)

            return render_template("thankyou.html")
    except Exception as e:
        logging.exception("Error in scheduling")
        return f"Internal Server Error: {str(e)}", 500

def send_email(subject, body, to):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_SENDER"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

if __name__ == '__main__':
    app.run(debug=True)
