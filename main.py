from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
import smtplib
from email.mime.text import MIMEText
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import unquote
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# Google Sheets + Calendar Setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar"
]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("HR BagelBoy Database").sheet1
calendar_service = build('calendar', 'v3', credentials=creds)
CALENDAR_ID = "f50e90776a5e78db486c71757d236abbbda060c246c4fefa593c3b564066d961@group.calendar.google.com"
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == os.environ.get("DASHBOARD_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Incorrect password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    rows = sheet.get_all_records()
    grouped = {"New": [], "1st meeting": [], "Trial": [], "Hired": [], "Not hired": [], "Other": []}

    for i, row in enumerate(rows):
        row_with_id = dict(row)
        row_with_id["row_id"] = i + 2
        status = row.get("Status")
        if status in grouped:
            grouped[status].append(row_with_id)
        else:
            grouped["Other"].append(row_with_id)

    return render_template("dashboard.html", grouped=grouped)

@app.route('/update-status/<int:row_id>/<new_status>')
def update_status(row_id, new_status):
    new_status = unquote(new_status)
    sheet.update_cell(row_id, 9, new_status)

    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]
    last_name = row[1]

    if new_status == "1st meeting":
        subject = "Invitation first meeting – BagelBoy"
        link = f"https://bagel-boy-backend.vercel.app/schedule/{row_id}"
        body = f"""Hi {first_name},\n\nWe would love to invite you for a short meeting.\n\nYou can schedule your intake at 9 or 11 any day.\n\nPlease plan your intake here:\n{link}\n\nBagelBoy HR"""
        send_email(subject, body, email)

    elif new_status == "Trial":
        subject = "Invitation trial shift – BagelBoy"
        link = f"https://bagel-boy-backend.vercel.app/schedule/{row_id}"
        body = f"""Hi {first_name},\n\nWe would love to invite you for a trial shift!\n\nYou can schedule your intake at 9 or 11 any day.\n\nPlease plan your trial here:\n{link}\n\nBagelBoy HR"""
        send_email(subject, body, email)

    elif new_status == "Not hired":
        subject = "BagelBoy application update"
        body = f"""Hi {first_name},\n\nUnfortunately we have to let you know we have decided not to proceed with your application.\nWe thank you for your time and effort and wish you all of luck in your future endeavors.\n\nWould you wish to have more information on this decision please contact Joep on 0681142820.\n\nBagelBoy HR"""
        send_email(subject, body, email)

    return redirect(url_for('dashboard'))

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

            try:
                time_str = time_str.zfill(5)  # Ensures format like '09:00'
                start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            except ValueError as ve:
                logging.error("Date parsing error", exc_info=True)
                return f"Date format error: {ve}", 400

            end_dt = start_dt + timedelta(minutes=15)

            event = {
                'summary': f"Intake {first_name} {last_name}",
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Europe/Amsterdam',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Europe/Amsterdam',
                },
                'attendees': [
                    {'email': email},
                    {'email': JOEP_EMAIL}
                ],
                'reminders': {
                    'useDefault': True
                }
            }

            logging.debug(f"Creating event: {event}")

            calendar_service.events().insert(calendarId=CALENDAR_ID, body=event, sendUpdates='all').execute()

            logging.info(f"Event created successfully for {first_name} {last_name}")

            return render_template("thankyou.html")
    except Exception as e:
        logging.exception("Error in scheduling")
        return f"Internal Server Error: {str(e)}", 500

@app.route('/reject/<int:row_id>')
def reject(row_id):
    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]

    sheet.update_cell(row_id, 9, "Not hired")

    subject = "BagelBoy application update"
    body = f"""Hi {first_name},\n\nUnfortunately we have to let you know we have decided not to proceed with your application.\nWe thank you for your time and effort and wish you all of luck in your future endeavors.\n\nWould you wish to have more information on this decision please contact Joep on 0681142820.\n\nBagelBoy HR"""
    send_email(subject, body, email)

    return redirect(url_for('dashboard'))

@app.route('/reject-custom/<int:row_id>', methods=['POST'])
def reject_custom(row_id):
    data = request.get_json()
    message = data.get('message')
    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]

    sheet.update_cell(row_id, 9, "Not hired")

    subject = "BagelBoy application update"
    body = f"Hi {first_name},\n\n{message}\n\nBagelBoy HR"
    send_email(subject, body, email)

    return jsonify({'status': 'ok'})

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
