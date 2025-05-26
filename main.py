from fastapi import FastAPI, Form, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Init
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecret")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="dashboard")

# Google Sheets setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "service_account.json"
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Credentials from environment
DASHBOARD_USER = os.environ.get("DASHBOARD_USER")
DASHBOARD_PASS = os.environ.get("DASHBOARD_PASS")

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    if username == DASHBOARD_USER and password == DASHBOARD_PASS:
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Onjuiste gegevens"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    rows = worksheet.get_all_values()[1:]  # skip header
    return templates.TemplateResponse("dashboard.html", {"request": request, "rows": rows})

@app.get("/data")
def get_data():
    rows = worksheet.get_a
