import json
import os
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.text import MIMEText

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "messages.json")
LOCK = threading.Lock()

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path == "index.html":
        return send_from_directory(BASE_DIR, "index.html")
    return send_from_directory(BASE_DIR, path)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "sitebuyld"})


@app.post("/api/contact")
def contact():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    message = str(data.get("message", "")).strip()
    bilingual = bool(data.get("bilingual"))

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "missing_fields"}), 400
    if "@" not in email or "." not in email:
        return jsonify({"ok": False, "error": "invalid_email"}), 400
    if len(message) < 10:
        return jsonify({"ok": False, "error": "message_too_short"}), 400

    record = {
        "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": name[:200],
        "email": email[:300],
        "message": message[:5000],
        "bilingual": bilingual,
    }

    with LOCK:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                messages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messages = []
        messages.append(record)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

    notify_email(record)
    return jsonify({"ok": True, "id": record["id"]})


def notify_email(record):
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    secret = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("CONTACT_TO", "example@sitebuyld.com")
    if not (host and user and secret):
        return

    body = (
        f"{record['name']} <{record['email']}>\n"
        f"Bilingual: {record['bilingual']}\n\n"
        f"{record['message']}"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[sitebuyld] New request from {record['name']}"
    msg["From"] = user
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            s.login(user, secret)
            s.send_message(msg)
    except Exception:
        pass


app.register_error_handler(404, lambda _e: send_from_directory(BASE_DIR, "index.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)