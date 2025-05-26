from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="geheimetestsleutel")
templates = Jinja2Templates(directory="dashboard")


def get_open_applications():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account2.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("HR BagelBoy Database").worksheet("Sollicitaties")
    rows = sheet.get_all_records()

    # Filter op status ≠ 'afgewezen' of 'gesloten'
    filtered = [row for row in rows if row.get("Status", "").lower() not in ["afgewezen", "gesloten"]]
    return filtered


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user", "gast")
    sollicitaties = get_open_applications()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "sollicitaties": sollicitaties})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/dashboard")
