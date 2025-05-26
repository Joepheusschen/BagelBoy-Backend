from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

# Sessies voor inloggen
app.add_middleware(SessionMiddleware, secret_key="supersecret")

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="dashboard")

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Email functie
SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

def send_email(to_email, subject, text_body, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
    except Exception as e:
        print("Email error:", e)

# Form endpoint
@app.post("/submit")
async def submit_form(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    hours: int = Form(...),
    motivation: str = Form(...)):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([timestamp, first_name, last_name, email, phone, position, hours, motivation, "Nieuw"])

    subject = "Bevestiging sollicitatie BagelBoy"
    text = f"Hi {first_name}, bedankt voor je sollicitatie bij BagelBoy!"
    html = f"""
    <html><body>
        <p>Hi {first_name},<br><br>
        Bedankt voor je sollicitatie bij <strong>BagelBoy</strong>!<br>
        We nemen zo snel mogelijk contact met je op.<br><br>
        Met vriendelijke groet,<br>Het BagelBoy Team</p>
    </body></html>
    """
    send_email(email, subject, text, html)

    admin_html = f"""
    <html><body>
        <p>Nieuwe sollicitatie:<br><br>
        Naam: {first_name} {last_name}<br>
        E-mail: {email}<br>
        Telefoon: {phone}<br>
        Functie: {position}<br>
        Uren: {hours}<br>
        Motivatie: {motivation}</p>
    </body></html>
    """
    send_email(SMTP_EMAIL, f"Nieuwe sollicitatie van {first_name}", text, admin_html)

    return JSONResponse(content={"message": "Formulier succesvol verzonden."})

# Dashboard login
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_login_page(request: Request):
    if request.session.get("logged_in"):
        data = worksheet.get_all_records()
        return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/dashboard")
async def dashboard_login(request: Request, username: str = Form(...), password: str = Form(...)):
    dashboard_user = os.environ.get("DASHBOARD_USER")
    dashboard_pass = os.environ.get("DASHBOARD_PASS")

    if username == dashboard_user and password == dashboard_pass:
        request.session["logged_in"] = True
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request, "error": "Toegang geweigerd"})

# Data endpoint
@app.get("/data")
async def get_data():
    rows = worksheet.get_all_records()
    return rows
