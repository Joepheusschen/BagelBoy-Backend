from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()
security = HTTPBasic()

# CORS voor lokaal testen of frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Zet hier je domein in productie
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sheets authenticatie
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Basic auth
def check_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = os.environ.get("DASHBOARD_USER", "admin")
    correct_pass = os.environ.get("DASHBOARD_PASS", "BagelBoy123!")
    if credentials.username != correct_user or credentials.password != correct_pass:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

# Endpoint: serve dashboard html
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse("dashboard/dashboard.html")

# Endpoint: haal data op uit Google Sheet
@app.get("/data")
async def get_data(credentials: HTTPBasicCredentials = Depends(check_credentials)):
    rows = worksheet.get_all_records()
    return rows

# Endpoint: verstuur mail
@app.post("/send-mail")
async def send_custom_mail(
    recipient_email: str = Form(...),
    recipient_name: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    credentials: HTTPBasicCredentials = Depends(check_credentials),
):
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = recipient_email

    text = f"Hi {recipient_name},\n\n{message}"
    html = f"""
    <html>
      <body>
        <p>Hi {recipient_name},<br><br>{message.replace('\n', '<br>')}</p>
      </body>
    </html>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipient_email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"message": "E-mail verzonden naar sollicitant."})
