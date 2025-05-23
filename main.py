
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials
import datetime
import os

app = FastAPI()

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SERVICE_ACCOUNT_FILE = 'service_account.json'
credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

gc = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

@app.post("/submit")
async def submit_form(request: Request):
    data = await request.json()

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    phone = data.get("phone")
    position = data.get("position")
    hours = data.get("hours")
    motivation = data.get("motivation")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet.append_row([
        timestamp, first_name, last_name, email, phone, position, hours, motivation, "Nieuw"
    ])

    return JSONResponse(content={"message": "Form submitted successfully."})
