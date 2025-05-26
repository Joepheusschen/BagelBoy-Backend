from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

# Templates & static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Mailfunctie
def send_email(to_email, subject, html_content):
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email

    text = "Bekijk deze mail in HTML-modus."
    html = html_content

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())

# Formulier insturen
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

    html = f"""
    <html><body>
    <p>Hi {first_name},<br><br>
       Bedankt voor je sollicitatie bij <strong>BagelBoy</strong>!<br>
       We nemen zo snel mogelijk contact met je op.<br><br>
       Met vriendelijke groet,<br>
       Het BagelBoy Team
    </p></body></html>
    """
    send_email(email, "Bevestiging sollicitatie BagelBoy", html)

    # CC mail naar werkgever
    cc_html = f"""
    <html><body>
    <p>Nieuwe sollicitatie:<br><br>
       Naam: {first_name} {last_name}<br>
       Email: {email}<br>
       Telefoon: {phone}<br>
       Positie: {position}<br>
       Uren: {hours}<br>
       Motivatie: {motivation}
    </p></body></html>
    """
    send_email(os.environ.get("SMTP_EMAIL"), f"Nieuwe sollicitatie: {first_name} {last_name}", cc_html)

    return JSONResponse(content={"message": "Formulier succesvol verzonden."})

# Gegevens ophalen
@app.get("/data")
async def get_data():
    return worksheet.get_all_records()

# Dashboard
@app.get("/dashboard")
async def dashboard(request: Request, password: str = ""):
    if password != "BagelBoy123!":
        return HTMLResponse(content="<h1>Unauthorized</h1>", status_code=401)
    data = worksheet.get_all_records()
    return templates.TemplateResponse("dashboard.html", {"request": request, "applicants": data})

# Uitnodiging sturen
@app.post("/send_invite")
async def send_invite(request: Request):
    payload = await request.json()
    email = payload.get("email")
    rows = worksheet.get_all_records()
    match = next((r for r in rows if r["email"] == email), None)

    if match:
        html = f"""
        <html><body>
        <p>Hi {match['first_name']},<br><br>
        We’d love to meet you! Plan je kennismaking via deze link:<br>
        <a href="https://calendly.com/bagelboy/kennismaking">Afspraak plannen</a><br><br>
        Tot snel!<br>BagelBoy
        </p></body></html>
        """
        send_email(email, "Kennismaking BagelBoy", html)
        return JSONResponse(content={"message": "Uitnodiging verstuurd."})
    return JSONResponse(content={"message": "Sollicitant niet gevonden."}, status_code=404)

# Afwijzing sturen
@app.post("/send_rejection")
async def send_rejection(request: Request):
    payload = await request.json()
    email = payload.get("email")
    rows = worksheet.get_all_records()
    match = next((r for r in rows if r["email"] == email), None)

    if match:
        html = f"""
        <html><body>
        <p>Hi {match['first_name']},<br><br>
        Bedankt voor je sollicitatie. Helaas hebben we besloten om niet verder te gaan.<br>
        Heb je vragen? Laat het ons weten. Veel succes met je verdere zoektocht!<br><br>
        BagelBoy
        </p></body></html>
        """
        send_email(email, "Update sollicitatie BagelBoy", html)
        return JSONResponse(content={"message": "Afwijzing verstuurd."})
    return JSONResponse(content={"message": "Sollicitant niet gevonden."}, status_code=404)
