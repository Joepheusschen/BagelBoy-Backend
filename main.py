from flask import Flask, request, render_template, redirect
import smtplib
from email.mime.text import MIMEText
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Google Sheets configuratie
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("BagelBoy Sollicitaties").sheet1

# Gmail-configuratie
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_USER = "jouwmailadres@gmail.com"  # Vervang dit
GMAIL_PASS = "jouw app-wachtwoord"       # Vervang dit

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=["POST"])
def submit():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    location = request.form.get("location")
    motivation = request.form.get("motivation")
    salary = request.form.get("salary")
    availability = request.form.get("availability")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Voeg gegevens toe aan Google Sheets
    sheet.append_row([timestamp, name, email, phone, location, motivation, salary, availability])

    # Verstuur bevestigingsmail naar sollicitant
    subject = "Thanks for your application!"
    body = f"""Hi {name},

Thanks for applying at BagelBoy! We’ve received your application and will get in touch as soon as possible.

Have a lovely day 🍩,
The BagelBoy Team
"""
    send_email(email, subject, body)

    # Stuur een kopie naar jezelf
    admin_subject = f"New application from {name}"
    admin_body = f"""New application received:

Name: {name}
Email: {email}
Phone: {phone}
Location: {location}
Motivation: {motivation}
Salary expectation: {salary}
Availability: {availability}
Time: {timestamp}
"""
    send_email("joepheusschen@gmail.com", admin_subject, admin_body)

    return render_template("bedankt.html")

def send_email(to, subject, body):
    msg = MIMEText(body)
    msg["From"] = GMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to, msg.as_string())

if __name__ == "__main__":
    app.run(debug=True)
