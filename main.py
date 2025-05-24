from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import gspread
from google.oauth2.service_account import Credentials
import os
import smtplib
from email.mime.text import MIMEText
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="."), name="static")

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
DASHBOARD_PASSWORD = "BagelBoy123!"

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    with open("dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard-data")
async def dashboard_data():
    records = worksheet.get_all_records()
    return [{"name": f"{r['Voornaam']} {r['Achternaam']}", "email": r['E-mail'], "status": r['Status']} for r in records]

@app.post("/dashboard-action")
async def dashboard_action(request: Request):
    body = await request.json()
    email = body.get("email")
    action = body.get("action")
    password = body.get("password")

    if password != DASHBOARD_PASSWORD:
        return JSONResponse(content={"message": "Ongeldig wachtwoord."}, status_code=403)

    records = worksheet.get_all_records()
    for i, row in enumerate(records):
        if row["E-mail"] == email:
            row_index = i + 2
            name = f"{row['Voornaam']} {row['Achternaam']}"
            if action == "interview":
                send_mail(email, name, "invite")
                worksheet.update_cell(row_index, 9, "Kennismaking gemaild")
            elif action == "reject":
                send_mail(email, name, "reject")
                worksheet.update_cell(row_index, 9, "Niet aangenomen")
            return {"message": f"Mail '{action}' verstuurd naar {email}"}

    return {"message": "Sollicitant niet gevonden."}

def send_mail(to_email, name, type):
    subject = ""
    body = ""

    if type == "invite":
        subject = "Kennismaking BagelBoy"
        body = f"""Hi {name},

Based on your motivation and resume we would love to invite you for a short meeting (10-15 min) at our Weteringschans location to see if we want to proceed and schedule a trial shift!

See you soon,
BagelBoy"""
    elif type == "reject":
        subject = "BagelBoy Application Update"
        body = f"""Hi {name},

Unfortunately we have decided not to proceed with your application. Please let us know if you have questions.

All the best in your job search,
BagelBoy"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())