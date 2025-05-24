from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

# Mount de dashboard map
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# E-mailfunctie
def send_email(to_email, subject, html_body, text_body):
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())

# Sollicitatie formulier endpoint
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

    # Mail naar sollicitant
    subject = "Bevestiging sollicitatie BagelBoy"
    text = f"Hi {first_name},\n\nBedankt voor je sollicitatie bij BagelBoy!"
    html = f"""
    <html><body>
        <p>Hi {first_name},<br><br>
        Bedankt voor je sollicitatie bij <strong>BagelBoy</strong>!<br>
        We nemen zo snel mogelijk contact met je op.<br><br>
        Met vriendelijke groet,<br>Het BagelBoy Team</p>
    </body></html>
    """
    send_email(email, subject, html, text)

    # Mail naar jezelf
    subject_admin = f"Nieuwe sollicitatie van {first_name} {last_name}"
    body_admin = f"""
    <html><body>
        <p>Er is een nieuwe sollicitatie binnengekomen:</p>
        <ul>
            <li>Naam: {first_name} {last_name}</li>
            <li>Email: {email}</li>
            <li>Telefoon: {phone}</li>
            <li>Functie: {position}</li>
            <li>Uren: {hours}</li>
            <li>Motivatie: {motivation}</li>
        </ul>
    </body></html>
    """
    send_email(os.environ.get("SMTP_EMAIL"), subject_admin, body_admin, body_admin)

    return JSONResponse(content={"message": "Formulier succesvol verzonden."})

# Endpoint voor uitnodiging of afwijzing versturen
@app.post("/mail")
async def send_decision(request: Request):
    form = await request.form()
    password = form.get("password")
    email = form.get("email")
    first_name = form.get("first_name")
    decision = form.get("decision")  # invite of reject

    if password != "BagelBoy123!":
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    if decision == "invite":
        subject = "Kennismaking BagelBoy"
        html = f"""
        <html><body>
            <p>Hi {first_name},<br><br>
            Leuk dat je hebt gesolliciteerd!<br>
            Plan hier een kennismaking in: <a href="https://calendly.com/">Klik hier om in te plannen</a>.<br><br>
            Tot snel!<br>
            Het BagelBoy Team</p>
        </body></html>
        """
        send_email(email, subject, html, html)
        return JSONResponse(content={"message": "Uitnodiging verstuurd"})

    elif decision == "reject":
        subject = "Reactie op je sollicitatie bij BagelBoy"
        html = f"""
        <html><body>
            <p>Hi {first_name},<br><br>
            Helaas hebben we besloten niet verder te gaan met je sollicitatie.<br>
            Mocht je vragen hebben, laat het ons weten.<br><br>
            Veel succes met je zoektocht!<br>
            Het BagelBoy Team</p>
        </body></html>
        """
        send_email(email, subject, html, html)
        return JSONResponse(content={"message": "Afwijzing verstuurd"})

    return JSONResponse(status_code=400, content={"message": "Ongeldige actie"})
