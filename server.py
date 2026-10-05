from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage

try:
    import certifi
except ImportError:
    certifi = None


def load_dotenv(path='.env'):
    if not os.path.exists(path):
        return

    with open(path, 'r', encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and value and key not in os.environ:
                os.environ[key] = value


def log(message: str) -> None:
    print(f"[contact-backend] {message}", flush=True)


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def smtp_configured() -> bool:
    return all([SMTP_HOST, SMTP_PORT, EMAIL_SENDER, EMAIL_RECIPIENT])


def smtp_auth_configured() -> bool:
    return bool(SMTP_USERNAME and SMTP_PASSWORD)


load_dotenv()

HOST = '127.0.0.1'
PORT = 8001

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', SMTP_USERNAME or os.environ.get('EMAIL_RECIPIENT', ''))
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', '')
SMTP_STARTTLS = env_flag('SMTP_STARTTLS', default=bool(SMTP_USERNAME or SMTP_PASSWORD))

RATE_LIMIT_SECONDS = 30
LAST_SUBMISSIONS = {}
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def send_email_notification(subject: str, body: str) -> None:
    if not smtp_configured():
        raise RuntimeError('SMTP is not configured. Please set SMTP_HOST, EMAIL_SENDER, and EMAIL_RECIPIENT.')

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = EMAIL_SENDER
    message['To'] = EMAIL_RECIPIENT
    message.set_content(body)

    log(f"Sending email to {EMAIL_RECIPIENT} via {SMTP_HOST}:{SMTP_PORT}")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_STARTTLS:
            if certifi is not None:
                cafile = certifi.where()
                log(f'Using certifi CA bundle: {cafile}')
                context = ssl.create_default_context(cafile=cafile)
            else:
                log('Certifi not installed; using system default certificate store')
                context = ssl.create_default_context()
            server.starttls(context=context)

        if smtp_auth_configured():
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        else:
            log('SMTP authentication disabled; sending through local/trusted SMTP relay.')

        server.send_message(message)

    log('Email sent successfully.')

class ContactHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            requested_path = 'index.html'
        else:
            requested_path = self.path.lstrip('/')

        if requested_path.startswith('contact'):
            self.send_response(405)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'GET is not supported for this endpoint'}).encode('utf-8'))
            return

        safe_path = os.path.normpath(requested_path)
        if safe_path in ('.', ''):
            safe_path = 'index.html'
        if safe_path.startswith('..') or os.path.isabs(safe_path):
            self.send_response(403)
            self.end_headers()
            return

        full_path = os.path.join(os.getcwd(), safe_path)
        if not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            return

        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        with open(full_path, 'rb') as file:
            content = file.read()

        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path != '/contact':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Invalid JSON payload'}).encode('utf-8'))
            return

        client_ip = self.client_address[0]
        now = time.time()
        last_submission = LAST_SUBMISSIONS.get(client_ip, 0)
        if now - last_submission < RATE_LIMIT_SECONDS:
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Please wait before submitting again.'}).encode('utf-8'))
            return

        name = str(data.get('name', '')).strip()
        company = str(data.get('company', '')).strip()
        email = str(data.get('email', '')).strip()
        phone = str(data.get('phone', '')).strip()
        topic = str(data.get('topic', '')).strip()
        budget = str(data.get('budget', '')).strip()
        message = str(data.get('message', '')).strip()
        privacy = bool(data.get('privacy', False))
        honeypot = str(data.get('website', '')).strip()

        if honeypot:
            log(f"Rejected spam request from {client_ip}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Spam detected'}).encode('utf-8'))
            return

        if not all([name, email, message, privacy]):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Required fields are missing'}).encode('utf-8'))
            return

        if not EMAIL_PATTERN.match(email):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Invalid email address'}).encode('utf-8'))
            return

        if any(len(value) > limit for value, limit in [
            (name, 120),
            (company, 160),
            (email, 180),
            (phone, 80),
            (topic, 120),
            (budget, 80),
            (message, 5000),
        ]):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Submitted fields are too long'}).encode('utf-8'))
            return

        LAST_SUBMISSIONS[client_ip] = now

        log(f"Received contact from {name} <{email}>")
        with open('messages.txt', 'a', encoding='utf-8') as file:
            file.write(
                f'Name: {name}\n'
                f'Company: {company or "-"}\n'
                f'Email: {email}\n'
                f'Phone: {phone or "-"}\n'
                f'Topic: {topic or "-"}\n'
                f'Budget: {budget or "-"}\n'
                f'Privacy consent: yes\n'
                f'Message: {message}\n'
                f'---\n'
            )

        email_subject = f'Neue Anfrage von {name}'
        email_body = (
            f'Neue Anfrage über ivancevicweb.com\n\n'
            f'Name: {name}\n'
            f'Firma: {company or "-"}\n'
            f'E-Mail: {email}\n'
            f'Telefon: {phone or "-"}\n'
            f'Thema: {topic or "-"}\n'
            f'Budgetrahmen: {budget or "-"}\n'
            f'Datenschutz bestätigt: ja\n\n'
            f'Nachricht:\n{message}\n'
        )

        email_status = 'Message received successfully.'
        if smtp_configured():
            try:
                send_email_notification(email_subject, email_body)
            except Exception as error:
                log(f'Email notification failed: {error}')
                email_status = 'Message saved, but email notification failed.'
        else:
            log('SMTP not configured; message was saved locally only.')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': email_status}).encode('utf-8'))

    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), ContactHandler)
    log(f'Server running on http://{HOST}:{PORT}')

    if smtp_configured():
        auth_mode = 'authenticated SMTP' if smtp_auth_configured() else 'local/trusted SMTP without login'
        tls_mode = 'STARTTLS enabled' if SMTP_STARTTLS else 'STARTTLS disabled'
        log(f'SMTP configured for recipient {EMAIL_RECIPIENT} via {SMTP_HOST}:{SMTP_PORT} ({auth_mode}, {tls_mode})')
    else:
        log('WARNING: SMTP is not fully configured. Set SMTP_HOST, EMAIL_SENDER, and EMAIL_RECIPIENT to enable email notifications.')

    server.serve_forever()
