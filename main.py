from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()
templates = Jinja2Templates(directory="dashboard")

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

# E-mail verzenden
def send_email(to_email, subject, html_content):
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
    except Exception as e:
        print("Email verzendfout:", e)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, password: str = ""):
    if password != "BagelBoy123!":
        return HTMLResponse("<h3>Toegang geweigerd</h3>", status_code=403)

    rows = worksheet.get_all_values()[1:]  # skip header
    data = [
        {
            "timestamp": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "email": row[3],
            "phone": row[4],
            "position": row[5],
            "hours": row[6],
            "motivation": row[7],
            "status": row[8],
            "index": i + 2  # rows start from 2 in Sheets
        }
        for i, row in enumerate(rows)
    ]
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})

@app.post("/action")
async def post_action(index: int = Form(...), email: str = Form(...), name: str = Form(...), action: str = Form(...)):
    if action == "invite":
        html = f"""
        <p>Hi {name},<br><br>
        Leuk dat je hebt gesolliciteerd bij <strong>BagelBoy</strong>!<br>
        We willen je graag uitnodigen voor een kennismaking.<br><br>
        Laat ons weten wanneer je beschikbaar bent.<br><br>
        Groeten,<br>Het BagelBoy team</p>
        """
        send_email(email, "Kennismaking BagelBoy", html)
        worksheet.update_cell(index, 9, "Uitgenodigd")
    elif action == "reject":
        html = f"""
        <p>Hi {name},<br><br>
        Bedankt voor je sollicitatie bij <strong>BagelBoy</strong>.<br>
        Helaas hebben we besloten om niet verder te gaan met je sollicitatie.<br><br>
        Veel succes met je verdere zoektocht!<br><br>
        Groeten,<br>Het BagelBoy team</p>
        """
        send_email(email, "Sollicitatie BagelBoy", html)
        worksheet.update_cell(index, 9, "Afgewezen")

    return RedirectResponse(url="/dashboard?password=BagelBoy123!", status_code=303)
