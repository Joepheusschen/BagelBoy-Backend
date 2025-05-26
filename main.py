from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    position = request.form.get('position')
    hours = request.form.get('hours')
    weekend = request.form.get('weekend')
    motivation = request.form.get('motivation')

    # ⛔️ Hier zou normaal sheet.append_row(...) staan – tijdelijk verwijderd

    subject = "We received your application – BagelBoy"
    body = f"""Hi {first_name},\n\nThanks for applying at BagelBoy as a {position} 🥯\n\nWe’ll be in touch with you as soon as possible.\n\nHave a great day,\nBagelBoy HR"""
    send_email(subject, body, email)

    internal_body = f"New application:\n{first_name} {last_name}, {email}, {phone}, {position}"
    send_email(f"New application from {first_name} {last_name}", internal_body, os.environ["EMAIL_RECEIVER"])

    return render_template("thankyou.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == os.environ.get("DASHBOARD_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Incorrect password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # ⛔️ Sheet- en calendarlogica verwijderd
    grouped = {"New": [], "1st meeting": [], "Trial": [], "Hired": [], "Not hired": [], "Other": []}

    return render_template("dashboard.html", grouped=grouped)

@app.route('/update-status/<int:row_id>/<new_status>')
def update_status(row_id, new_status):
    # ⛔️ sheet.update_cell(...) verwijderd
    return redirect(url_for('dashboard'))

@app.route('/invite/<int:row_id>')
def invite(row_id):
    # ⛔️ Gegevens uit sheet verwijderd
    email = "test@example.com"
    first_name = "Candidate"
    last_name = "Example"

    subject = "Invitation first meeting – BagelBoy"
    body = f"""Hi {first_name},\n\nWe would love to invite you for a short meeting to see if we want to schedule a trial.\n\nThe meeting will take 10–15 minutes max.\n\nPlease name your meeting in Google Calendar as follows: Intake {first_name} {last_name}\n\nUse this link to schedule yourself:\nhttps://calendar.google.com/calendar/embed?src=f50e90776a5e78db486c71757d236abbbda060c246c4fefa593c3b564066d961%40group.calendar.google.com&ctz=Europe%2FAmsterdam\n\nAvailable daily at 9:00 or 11:00.\n\nBagelBoy HR"""
    send_email(subject, body, email)

    return redirect(url_for('dashboard'))

@app.route('/reject/<int:row_id>')
def reject(row_id):
    email = "test@example.com"
    first_name = "Candidate"

    subject = "BagelBoy application update"
    body = f"""Hi {first_name},\n\nUnfortunately we have to let you know we have decided not to proceed with your application.\nWe thank you for your time and effort and wish you all of luck in your future endeavors.\n\nWould you wish to have more information on this decision please contact Joep on 0681142820.\n\nBagelBoy HR"""
    send_email(subject, body, email)

    return redirect(url_for('dashboard'))

@app.route('/reject-custom/<int:row_id>', methods=['POST'])
def reject_custom(row_id):
    data = request.get_json()
    message = data.get('message')
    email = "test@example.com"
    first_name = "Candidate"

    subject = "BagelBoy application update"
    body = f"Hi {first_name},\n\n{message}\n\nBagelBoy HR"
    send_email(subject, body, email)

    return jsonify({'status': 'ok'})

def send_email(subject, body, to):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_SENDER"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

if __name__ == '__main__':
    app.run(debug=True)
