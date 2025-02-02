import logging
import os
import smtplib
import sqlite3
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pdfplumber
import pytz
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from fpdf import FPDF
from itsdangerous import BadTimeSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)


app.permanent_session_lifetime = timedelta(minutes=120)
# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger = logging.getLogger('adminLogger')
# logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('admin_login.log')
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

app.secret_key = 'onetwothree'  # Needed for session management
now = datetime.now()
current_year = now.year

password_email = 'your email password here'
sender_email_address = 'your email addres here'

s = URLSafeTimedSerializer(app.secret_key)


def replace_pdf(input_pdf, output_pdf, replacements):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', size=12)
    pdf.add_page()

    with pdfplumber.open(input_pdf) as pdf_reader:
        for page in pdf_reader.pages:
            text = page.extract_text()

            # Problematische Zeichen wie Gedankenstriche durch einfache Bindestriche ersetzen
            text = text.replace('\u2013', '-')  # Ersetzt Gedankenstriche

            for placeholder, value in replacements.items():
                value = str(value)
                text = text.replace(placeholder, value)

            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, text)

    # Speichern der neuen PDF-Datei
    pdf.output(output_pdf, 'F')


def generate_confirmation_token(email):
    return s.dumps(email, salt='email-confirm')


# Verifikationstoken bestätigen
def confirm_token(token, expiration=3600):
    try:
        email = s.loads(token, salt='email-confirm', max_age=expiration)
    except SignatureExpired:
        return False  # Token abgelaufen
    except BadTimeSignature:
        return False  # Falscher Token
    return email


def send_email(receiver_email, subject, message_body):
    sender_email = sender_email_address
    sender_password = password_email

    # E-Mail-Inhalt erstellen
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Nachricht als UTF-8 Text hinzufügen
    body = MIMEText(message_body, 'plain', 'utf-8')
    msg.attach(body)

    try:
        # SMTP-Server und Port festlegen (für web.de: smtp.web.de und Port 587)
        server = smtplib.SMTP('smtp.web.de', 587)
        server.starttls()  # TLS für Sicherheit
        server.login(sender_email, sender_password)  # Login

        # E-Mail senden
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        print("E-Mail erfolgreich gesendet!")
        logger.info(f"Sending email to {receiver_email}")
        server.quit()

    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")


# Beispielwerte für den Aufruf der Funktion


# Database setup
def init_db():
    if not os.path.exists('preise.db'):
        print('new price db got created')
        conn = sqlite3.connect('preise.db')
        c = conn.cursor()
        # Tabelle erstellen, wenn sie nicht existiert
        c.execute('''
            CREATE TABLE IF NOT EXISTS preise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                von TEXT NOT NULL,
                bis TEXT NOT NULL,
                preis REAL NOT NULL,
                farbe TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    if not os.path.exists('data.db'):
        print('new user db got created')
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            von TEXT,
            bis TEXT,
            date TEXT NOT NULL,
            von1 TEXT NOT NULL,
            bis1 TEXT NOT NULL,
            telephone TEXT NOT NULL,
            wohnmobil TEXT,
            preis TEXT,
            iban TEXT,
            status TEXT NOT NULL
        )
        ''')
        conn.commit()
        conn.close()


@app.route('/test/date-submit', methods=['POST', 'GET'])
def test_date_submit():
    print("\033[1m" + "\033[31m" + "submit startet" + "\033[0m" + "\033[0m")
    date = request.form['kalenderInput']
    print(date)
    return redirect(url_for('test_date'))



@app.route('/test/date')
def test_date():
    return render_template('/test/date.html')


@app.route('/test/pdf', methods=['POST', 'GET'])
def test_pdf_render():

    return render_template('/test/pdf_data.html')


@app.route('/test/pdf_submit', methods=['POST', 'GET'])
def test_pdf_render_submit():
    name = request.form['name']
    email = request.form['email']
    von = request.form['von']
    bis = request.form['bis']
    preis = request.form['preis']
    replacements = {
        "{{name}}": name,
        "{{email}}": email,
        "{{von}}": von,
        "{{bis}}": bis,
        "{{preis}}": preis,
    }

    replace_pdf("template.pdf", "output.pdf", replacements)
    path = "output.pdf"
    return send_file(path, as_attachment=True)


@app.route('/wohnmobile')
def wohnmobile():
    return render_template('/Wohnmobile.html')
@app.route('/impressum')
def impressum():
    return render_template('/impressum.html')

@app.route('/bild')
def bild():
    return render_template('/test.html')

@app.route('/admin/price')
def price_admin_view():
    conn = sqlite3.connect('preise.db')
    c = conn.cursor()
    c.execute('SELECT * FROM preise')
    preise = c.fetchall()
    conn.close()
    return render_template('/admin/price.html', preis=preise)

@app.route('/admin/price/delete/<int:price_id>', methods=['POST'])
def delete_price(price_id):
    conn = sqlite3.connect('preise.db')
    c = conn.cursor()
    c.execute('DELETE FROM preise WHERE id = ?', (price_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('price_admin_view'))



@app.route('/preis_submit', methods=['POST'])
def preis_submit():
    # Daten aus dem Formular abrufen
    von = request.form['von']
    bis = request.form['bis']
    preis = request.form['price']
    farbe = request.form['farbe']
    # Preis und Farbe in die Datenbank speichern
    if von and bis and preis and farbe:
        conn = sqlite3.connect('preise.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO preise (von, bis, preis, farbe) VALUES (?, ?, ?, ?)
        ''', (von, bis, preis, farbe))
        conn.commit()
        conn.close()
        return redirect(url_for('price_admin_view'))
    
    return "Fehler: Alle Felder müssen ausgefüllt werden!", 400 



@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email_noformat = request.form['email']
    telephone = request.form['telephone']
    email = email_noformat.lower()
    date = request.form['kalenderInput']
    wohnmobil = request.form['wohnmobil']
    preis = request.form['preis']

    if wohnmobil == "0":
        flash('bitte wohnmobil angeben oder "egal" auswählen')
        return redirect(url_for('buchen'))

    if date == "":
        flash('Bitte geben Sie eine gültige Datum ein.')
        return redirect(url_for('buchen'))

    von1, bis1 = date.split(" to ")

    print("\033[1m" + "\033[31m" + date + "\033[0m" + "\033[0m")

    # Überprüfen, ob der Benutzer bereits in der Datenbank ist

    status = "abgesendet"

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(
        """INSERT INTO users (
            name,
            email,
            date,
            von1,
            bis1,
            telephone,
            wohnmobil,
            preis,
            status
        
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ((name, email, date, von1, bis1, telephone, wohnmobil, preis, status)))
    conn.commit()
    conn.close()

    token = generate_confirmation_token(email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = 'Bitte bestaetigen Sie Ihre E-Mail-Adresse'
    message_body = f"""Hallo {name}, bitte bestaetigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken: 
    {confirm_url}"""
    send_email(email, subject, message_body)

    flash(
        'Eine Bestätigungs-E-Mail wurde gesendet. Bitte überprüfen Sie Ihr Postfach.'
    )

    return redirect(url_for('buchen'))


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('Der Bestätigungslink ist ungültig oder abgelaufen.', 'danger')
        return redirect(url_for('index'))

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (email, ))
    user = c.fetchone()
    if user:
        c.execute("UPDATE users SET status = 'bestätigt' WHERE email = ?",
                  (email, ))
        conn.commit()
        flash('Ihre E-Mail-Adresse wurde bestätigt. Vielen Dank!', 'success')
    else:
        flash('Die E-Mail-Adresse konnte nicht bestätigt werden.', 'danger')

    if user:

        c.execute("SELECT * FROM users WHERE email = ?", (email, ))
        data_user = c.fetchone()
        # Daten aus der Datenbank extrahieren
        user_id, name, email, von, bis, date, von1, bis1, telephone, wohnmobil, iban, status, *extra = data_user
        status = 'email bestätigt'
        c.execute(
            """INSERT INTO users (
                name, email, von, bis, date, von1, bis1, telephone, wohnmobil, iban, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (name, email, von, bis, date, von1, bis1, telephone, wohnmobil, iban, status))
        conn.commit()

        # Aktuelles Jahr für die E-Mail erstellen
        current_year = datetime.now().year

        # E-Mail-Daten setzen
        receiver_email = email
        subject = f'Buchungsanfrage vom {von1} bis zum {bis1}'
        message_body = (
            f'Hallo {name},\n\n'
            'Ihre Buchung wurde erfolgreich abgeschickt! \n'
            'Ihre Daten: \n'
            f'Name: {name}\n'
            f'Email: {email}\n'
            f'Telefon: {telephone}\n'
            f'Vom: {von1}\n'
            f'Bis: {bis1}\n\n'
            'Danke fuer Ihre Anfrage!\n'
            'Wir werden uns innerhalb von 48 Stunden bei Ihnen melden! \n\n'
            f'Ihr Team von Meine kleine Freiheit \n'
            f'(c) {current_year} Meine kleine Freiheit \n')

        # E-Mail senden
        send_email(receiver_email, subject, message_body)
        print('debug: ' + receiver_email + subject)
    conn.close()

    return redirect(url_for('index'))


@app.route('/test/header')
def header_test():
    return render_template('test/headertest.html')


@app.route('/test/log')
def log_display():
    # Log-Datei einlesen
    with open('admin_login.log', 'r') as file:
        logs = file.readlines()
    return render_template('test/log.html', logs=logs)


@app.route('/test/to-do')
def todo():
    return render_template('test/todo.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/home')
def home():
    return render_template('index.html')


@app.route('/buchen')
def buchen():
    wohnmobil_id = request.args.get('wohnmobil', default='0', type=str)
    conn = sqlite3.connect('preise.db')
    c = conn.cursor()
    c.execute('SELECT * FROM preise')
    preise = c.fetchall()
    conn.close()
    return render_template('buchen.html', wohnmobil_id=wohnmobil_id, preise=preise)


@app.route('/auth/bank', methods=('GET', 'POST'))
def auth_bank():
    return render_template('authbank.html')


@app.route('/auth/bank-submit', methods=('GET', 'POST'))
def auth_bank_submit():

    email = request.form['email']
    iban = request.form['iban']

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # Query to check if email exists
    c.execute("SELECT id FROM users WHERE email = ?", (email, ))
    result = c.fetchone()

    if result:
        # Update IBAN for the user with matching email
        c.execute("""UPDATE users SET iban = ? WHERE email = ?""",
                  (iban, email))
        conn.commit()
        conn.close()
        flash(
            f"Die IBAN wurde für die E-Mail '{email}' erfolgreich aktualisiert."
        )
        print(
            f"Die IBAN wurde für die E-Mail '{email}' erfolgreich aktualisiert."
        )
        return redirect(url_for('auth_bank'))
    else:
        conn.close()
        flash(f"Die E-Mail '{email}' existiert nicht in der Datenbank.")
        print(f"Die E-Mail '{email}' existiert nicht in der Datenbank.")
        return redirect(url_for('auth_bank'))


@app.route('/change_status', methods=['POST'])
def change_status():
    if 'admin' in session:
        user_id = request.form['user_id']
        new_status = request.form['status']

        # Connect to the database and update the user's status
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("UPDATE users SET status = ? WHERE id = ?",
                  (new_status, user_id))
        conn.commit()
        conn.close()

        return redirect(url_for('admin'))
    else:
        return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    session.pop('admin', None)  # Admin-Status aus der Session entfernen
    return redirect(url_for('admin'))


@app.route('/admin/session', methods=['GET', 'POST'])
def admin_session_check():
    if 'admin' in session:
        return 'Eingeloggt als Admin'
    else:
        return 'Nicht eingeloggt'


@app.route('/admin/downloadpreset', methods=['GET', 'POST'])
def admin_users():
    if 'admin' in session:
        return render_template('admin/downloadpreset.html')
    else:
        return redirect(url_for('admin'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Prüfe, ob der Benutzer bereits authentifiziert ist
    if 'admin' in session:
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY status")
        users = c.fetchall()
        conn.close()

        # Log-Datei einlesen
        with open('admin_login.log', 'r') as file:
            logs = file.readlines()

        # Definiere die Mitteleuropäische Zeitzone
        me_zone = pytz.timezone('Europe/Berlin')

        # Holen Sie sich die aktuelle Zeit in dieser Zeitzone
        me_time = datetime.now(me_zone)

        # Logge die Zeit
        logger.info('%s admin logged in',
                    me_time.strftime('%Y-%m-%d %H:%M:%S'))
        return render_template('admin/admin.html', users=users, logs=logs)

    if request.method == 'POST':
        password = request.form['password']
        if password == 'test':  # Einfacher Passwortcheck
            session['admin'] = True  # Setze Admin-Status in der Session
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users ORDER BY status")
            users = c.fetchall()
            conn.close()

            # Log-Datei einlesen
            with open('admin_login.log', 'r') as file:
                logs = file.readlines()

            # Definiere die Mitteleuropäische Zeitzone
            me_zone = pytz.timezone('Europe/Berlin')

            # Holen Sie sich die aktuelle Zeit in dieser Zeitzone
            me_time = datetime.now(me_zone)

            # Logge die Zeit
            logger.info('%s admin logged in',
                        me_time.strftime('%Y-%m-%d %H:%M:%S'))
            return render_template('admin/admin.html', users=users, logs=logs)
        else:
            me_zone = pytz.timezone('Europe/Berlin')

            # Holen Sie sich die aktuelle Zeit in dieser Zeitzone
            me_time = datetime.now(me_zone)
            # Logge die Zeit
            logger.info('%s admin failed to login',
                        me_time.strftime('%Y-%m-%d %H:%M:%S'))

            return render_template('admin/admin_login_fail.html')

    return render_template('/admin/admin_login.html')  # Zeige Login-Formular


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'test':  # Einfacher Passwortcheck
            session['admin'] = True  # Setze Admin-Status in der Session
    if 'admin' in session:
        return redirect(url_for('admin'))

    return render_template('admin/admin_login.html')


@app.route('/delete_user', methods=['POST'])
def delete_user():
    if 'admin' in session:
        user_id = request.form['user_id']  # ID aus dem Formular bekommen

        conn = sqlite3.connect('data.db')
        c = conn.cursor()

        # Benutzer aus der Datenbank löschen
        c.execute("DELETE FROM users WHERE id = ?", (user_id, ))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return redirect(url_for('admin'))  # Zurück zum Admin-Panel


@app.route('/download/admin_log', methods=['POST', 'GET'])
def download_file_admin_log():
    if 'admin' in session:
        path = "admin_login.log"
        return send_file(path, as_attachment=True)
    else:
        return redirect(url_for('admin'))


@app.route('/download/data_base', methods=['POST', 'GET'])
def download_file_data_base():
    if 'admin' in session:
        path = "data.db"
        return send_file(path, as_attachment=True)
    else:
        return redirect(url_for('admin'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
