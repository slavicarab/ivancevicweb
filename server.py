from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
import os
import smtplib
import ssl
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


def smtp_configured() -> bool:
    return all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_RECIPIENT])


load_dotenv()

HOST = '127.0.0.1'
PORT = 8001

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', SMTP_USERNAME)
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', 'slavicarabrenovic@yahoo.com')


def send_email_notification(subject: str, body: str) -> None:
    if not smtp_configured():
        raise RuntimeError('SMTP is not configured. Please set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_RECIPIENT.')

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = EMAIL_SENDER
    message['To'] = EMAIL_RECIPIENT
    message.set_content(body)

    log(f"Sending email to {EMAIL_RECIPIENT} via {SMTP_HOST}:{SMTP_PORT}")

    if certifi is not None:
        cafile = certifi.where()
        log(f'Using certifi CA bundle: {cafile}')
        context = ssl.create_default_context(cafile=cafile)
    else:
        log('Certifi not installed; using system default certificate store')
        context = ssl.create_default_context()

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
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

        first_name = str(data.get('firstName', '')).strip()
        last_name = str(data.get('lastName', '')).strip()
        email = str(data.get('email', '')).strip()
        message = str(data.get('message', '')).strip()
        antispam_answer = str(data.get('antispamAnswer', '')).strip()
        honeypot = str(data.get('honeypot', '')).strip()

        if not all([first_name, last_name, email, message, antispam_answer]):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'All fields are required'}).encode('utf-8'))
            return

        if honeypot:
            log(f"Rejected spam request from {self.client_address[0]}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Spam detected'}).encode('utf-8'))
            return

        if antispam_answer != '5':
            log(f"Incorrect anti-spam answer from {self.client_address[0]}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Anti-spam answer is incorrect'}).encode('utf-8'))
            return

        log(f"Received contact from {first_name} {last_name} <{email}>")
        with open('messages.txt', 'a', encoding='utf-8') as file:
            file.write(f'Name: {first_name} {last_name}\nEmail: {email}\nMessage: {message}\n---\n')

        email_subject = f'New portfolio message from {first_name} {last_name}'
        email_body = (
            f'You have a new message from your portfolio contact form.\n\n'
            f'Name: {first_name} {last_name}\n'
            f'Email: {email}\n\n'
            f'Message:\n{message}\n'
        )

        email_status = 'Message received successfully.'
        try:
            send_email_notification(email_subject, email_body)
        except Exception as error:
            email_status = f'Message saved, but email notification failed: {error}'

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
        log(f'SMTP configured for recipient {EMAIL_RECIPIENT} via {SMTP_HOST}:{SMTP_PORT}')
    else:
        log('WARNING: SMTP is not fully configured. Email notifications will fail until .env is set correctly.')

    server.serve_forever()
