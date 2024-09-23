import logging
import os
import smtplib
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

app = Flask(__name__)

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

password_email = os.environ['password']

s = URLSafeTimedSerializer(app.secret_key)



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
    sender_email = 'manfred-eckl@web.de'
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

    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")

    finally:
        server.quit()  # Verbindung zum Server schließen



# Beispielwerte für den Aufruf der Funktion





# Database setup
def init_db():
    if not os.path.exists('data.db'):
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


@app.route('/wohnmobile')
def wohnmobile():
    return render_template('/Wohnmobile.html')


@app.route('/bild')
def bild():
    return render_template('/test.html')


@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email_noformat = request.form['email']
    telephone = request.form['telephone']
    email = email_noformat.lower()
    date = request.form['kalenderInput']
    wohnmobil = request.form['wohnmobil']

    if wohnmobil == "0":
        flash('bitte wohnmobil angeben oder "egal" auswählen')
        return redirect(url_for('buchen'))
        
    if date == "":
        flash('Bitte geben Sie eine gültige Datum ein.')
        return redirect(url_for('buchen'))

    von1, bis1 = date.split(" to ")

    print("\033[1m" + "\033[31m" + date + "\033[0m" + "\033[0m")
    if date == '':
        return print('no date')

    if name == "bennet":
        flash("Hallo Bennet, schön, dass du da bist!")
    if name == "Bennet":
        flash("Hallo Bennet, schön, dass du da bist!")

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
            status
        
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ((name, email, date, von1, bis1, telephone, wohnmobil, status)))
    conn.commit()
    conn.close()

    token = generate_confirmation_token(email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = 'Bitte bestaetigen Sie Ihre E-Mail-Adresse'
    message_body = f'Hallo {name}, bitte bestaetigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken: {confirm_url}'
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
    c.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    if user:
        c.execute("UPDATE users SET status = 'bestätigt' WHERE email = ?", (email,))
        conn.commit()
        flash('Ihre E-Mail-Adresse wurde bestätigt. Vielen Dank!', 'success')
    else:
        flash('Die E-Mail-Adresse konnte nicht bestätigt werden.', 'danger')


    
    if user:

        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        data_user = c.fetchone()
        # Daten aus der Datenbank extrahieren
        user_id, name, email, von, bis, date, von1, bis1, telephone, iban, status = data_user

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
            f'(c) {current_year} Meine kleine Freiheit \n'
        )

        # E-Mail senden
        send_email(receiver_email, subject, message_body)
        print('debug: ' + receiver_email + subject )
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
    return render_template('buchen.html', wohnmobil_id=wohnmobil_id)


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


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'test':  # Simple password check
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
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
            # Definiere die Mitteleuropäische Zeitzone
            me_zone = pytz.timezone('Europe/Berlin')

            # Holen Sie sich die aktuelle Zeit in dieser Zeitzone
            me_time = datetime.now(me_zone)

            ip_addr = request.environ['REMOTE_ADDR']
            # Logge die Zeit
            logger.info('%s admin failed to login',
                        me_time.strftime('%Y-%m-%d %H:%M:%S'))

            return render_template('admin/admin_login_fail.html')
    return render_template('admin/admin_login.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
