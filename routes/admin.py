import logging
import os
import smtplib
import sqlite3
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
from flask import Blueprint

app = Flask(__name__)
admin_route = Blueprint('admin', __name__)


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

password_email = os.environ['password']

s = URLSafeTimedSerializer(app.secret_key)


@admin_route.route('/logout')
def logout():
    session.pop('admin', None)  # Admin-Status aus der Session entfernen
    return redirect(url_for('admin.admin'))


@admin_route.route('/admin/session', methods=['GET', 'POST'])
def admin_session_check():
    if 'admin' in session:
        return 'Eingeloggt als Admin'
    else:
        return 'Nicht eingeloggt'


@admin_route.route('/admin/downloadpreset', methods=['GET', 'POST'])
def admin_users():
    if 'admin' in session:
        return render_template('admin/downloadpreset.html')
    else:
        return redirect(url_for('admin.admin'))


@admin_route.route('/admin', methods=['GET', 'POST'])
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


@admin_route.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'test':  # Einfacher Passwortcheck
            session['admin'] = True  # Setze Admin-Status in der Session
    if 'admin' in session:
        return redirect(url_for('admin.admin'))

    return render_template('admin/admin_login.html')


@admin_route.route('/delete_user', methods=['POST'])
def delete_user():
    if 'admin' in session:
        user_id = request.form['user_id']  # ID aus dem Formular bekommen

        conn = sqlite3.connect('data.db')
        c = conn.cursor()

        # Benutzer aus der Datenbank löschen
        c.execute("DELETE FROM users WHERE id = ?", (user_id, ))
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin'))
    return redirect(url_for('admin.admin'))  # Zurück zum Admin-Panel


@admin_route.route('/download/admin_log', methods=['POST', 'GET'])
def download_file_admin_log():
    if 'admin' in session:
        path = "admin_login.log"
        return send_file(path, as_attachment=True)
    else:
        return redirect(url_for('admin.admin'))


@admin_route.route('/download/data_base', methods=['POST', 'GET'])
def download_file_data_base():
    if 'admin' in session:
        path = "data.db"
        return send_file(path, as_attachment=True)
    else:
        return redirect(url_for('admin.admin'))