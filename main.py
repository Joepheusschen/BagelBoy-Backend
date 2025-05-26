from flask import Flask, request, render_template, redirect, url_for
import os
import json
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Setup Google Sheets
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
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    position = request.form.get('position')
    hours = request.form.get('hours')
    weekend = request.form.get('weekend')
    motivation = request.form.get('motivation')

    sheet.append_row([first_name, last_name, email, phone, position, hours, weekend, motivation, "New"])

    # Bevestigingsmail
    subject = "We received your application – BagelBoy"
    body = f"""Hi {first_name},\n\nThanks for applying at BagelBoy as a {position} 🍳\n\nWe’ll be in touch with you as soon as possible.\n\nHave a great day,\nBagelBoy HR"""
    send_email(subject, body, email)

    # Interne melding
    internal_body = f"New application:\n{first_name} {last_name}, {email}, {phone}, {position}"
    send_email(f"New application from {first_name} {last_name}", internal_body, os.environ["EMAIL_RECEIVER"])

    return render_template("thankyou.html")

@app.route('/dashboard')
def dashboard():
    rows = sheet.get_all_records()
    grouped = {"New": [], "Other": []}
    for i, row in enumerate(rows):
        row_with_id = dict(row)
        row_with_id["row_id"] = i + 2  # header = row 1
        if row.get("Status") == "New":
            grouped["New"].append(row_with_id)
        else:
            grouped["Other"].append(row_with_id)
    return render_template("dashboard.html", grouped=grouped)

@app.route('/invite/<int:row_id>')
def invite(row_id):
    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]

    # Update status in sheet
    sheet.update_cell(row_id, 9, "Invited")

    subject = "Invitation to meet – BagelBoy"
    body = f"""Hi {first_name},\n\nWe would love to invite you for a short meeting to see if we want to schedule a trial.\nPlease use this link to schedule yourself:\n\nhttps://calendar.google.com/calendar/u/0/selfsched?sstoken=UU50ZW... (korten kan)\n\nYou can schedule yourself any day at 9:00 or 11:00.\n\nBagelBoy HR"""
    send_email(subject, body, email)

    notify_me = f"{first_name} invited for a meeting. Check when they booked in Google Calendar."
    send_email("Candidate invited", notify_me, os.environ["EMAIL_RECEIVER"])
    return redirect(url_for('dashboard'))

@app.route('/reject/<int:row_id>')
def reject(row_id):
    row = sheet.row_values(row_id)
    email = row[2]
    first_name = row[0]

    # Update status in sheet
    sheet.update_cell(row_id, 9, "Rejected")

    subject = "Application update – BagelBoy"
    body = f"""Hi {first_name},\n\nUnfortunately we have decided not to proceed with your application.\nWe wish you all the luck in your future endeavours!\n\nBagelBoy HR"""
    send_email(subject, body, email)

    return redirect(url_for('dashboard'))

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
