from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Email functie
def send_confirmation_email(to_email, first_name, cc_email):
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Bevestiging sollicitatie BagelBoy"
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Cc"] = cc_email

    text = f"Hi {first_name},\n\nBedankt voor je sollicitatie bij BagelBoy!"
    html = f"""
    <html>
      <body>
        <p>Hi {first_name},<br><br>
           Bedankt voor je sollicitatie bij <strong>BagelBoy</strong>!<br>
           We nemen zo snel mogelijk contact met je op.<br><br>
           Met vriendelijke groet,<br>
           Het BagelBoy Team
        </p>
      </body>
    </html>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, [to_email, cc_email], msg.as_string())
    except Exception as e:
        print("Fout bij verzenden e-mail:", e)

# Submit endpoint
@app.post("/submit")
async def submit_form(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    hours: int = Form(...),
    motivation: str = Form(...)
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet.append_row([
        timestamp, first_name, last_name, email, phone, position, hours, motivation, "Nieuw"
    ])

    send_confirmation_email(email, first_name, cc_email="joepheusschen@gmail.com")

    return JSONResponse(content={"message": "Formulier succesvol verzonden."})
