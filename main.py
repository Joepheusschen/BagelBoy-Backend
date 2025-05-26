from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
import json
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# Setup Google Sheets & Calendar API
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.readonly"
]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("HR BagelBoy Database").sheet1
calendar_service = build('calendar', 'v3', credentials=creds)
CALENDAR_ID = "f50e90776a5e78db486c71757d236abbbda060c246c4fefa593c3b564066d961@group.calendar.google.com"

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

    sheet.append_row([first_name, last_name, email, phone, position, hours, weekend, motivation, "New"])

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
    upcoming = get_upcoming_events()
    grouped = {"New": [], "1st meeting": [], "Trial": [], "Hired": [], "Not hired": [], "Other": []}

    for i, row in enumerate(rows):
        row_with_id = dict(row)
        row_with_id["row_id"] = i + 2
        full_name = f"{row.get('First name', '').strip()} {row.get('Last name', '').strip()}"
        matching_event = next((e for e in upcoming if full_name.lower() in e["summary"].lower()), None)
        if matching_event:
            row_with_id["event"] = matching_event["start"]
            notify_meeting_detected(full_name, matching_event["start"])

        status = row.get("Status")
        if status in grouped:
            grouped[status].append(row_with_id)
        else:
            grouped["Other"].append(row_with_id)

    return render_template("dashboard.html", grouped=grouped)

def get_upcoming_events():
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=20,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    formatted = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'No Title')
        formatted.append({"start": start, "summary": summary})
    return formatted

def notify_meeting_detected(name, time):
    subject = f"{name} scheduled a meeting"
    body = f"{name} has scheduled a meeting on: {time}"
    send_email(subject, body, os.environ["EMAIL_RECEIVER"])

@app.route('/update-status/<int:row_id>/<new_status>')
def update_status(row_id, new_status):
    sheet.update_cell(row_id, 9, new_status)
    return redirect(url_for('dashboard'))

@app.route('/invite/<int:row_id>')
def invite(row_id):
    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]
    last_name = row[1]

    sheet.update_cell(row_id, 9, "Invited")

    subject = "Invitation first meeting – BagelBoy"
    body = f"""Hi {first_name},\n\nWe would love to invite you for a short meeting to see if we want to schedule a trial.\n\nThe meeting will take 10–15 minutes max.\n\nPlease name your meeting in Google Calendar as follows: Intake {first_name} {last_name}\n\nUse this link to schedule yourself:\nhttps://calendar.google.com/calendar/embed?src=f50e90776a5e78db486c71757d236abbbda060c246c4fefa593c3b564066d961%40group.calendar.google.com&ctz=Europe%2FAmsterdam\n\nAvailable daily at 9:00 or 11:00.\n\nBagelBoy HR"""
    send_email(subject, body, email)

    notify_me = f"{first_name} invited for a meeting. Check when they booked in Google Calendar."
    send_email("Candidate invited", notify_me, os.environ["EMAIL_RECEIVER"])
    return redirect(url_for('dashboard'))

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
