#!/usr/bin/env python3
"""Email notification via Gmail SMTP.
Env: SMTP_USER, SMTP_PASS (Google app password), NOTIFY_EMAIL
"""
import os, smtplib, sys
from email.mime.text import MIMEText

def send_notification(subject, body):
    user, pwd, to = os.environ.get("SMTP_USER",""), os.environ.get("SMTP_PASS",""), os.environ.get("NOTIFY_EMAIL","")
    if not all([user, pwd, to]):
        print(f"SMTP not configured.\nSubject: {subject}\n{body}"); return
    msg = MIMEText(body); msg["Subject"] = subject; msg["From"] = user; msg["To"] = to
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pwd); s.send_message(msg)
        print(f"Sent to {to}")
    except Exception as e:
        print(f"SMTP failed: {e}\nSubject: {subject}\n{body}")

if __name__ == "__main__":
    if len(sys.argv) >= 3: send_notification(sys.argv[1], sys.argv[2])
    else: print("Usage: notify.py '<subject>' '<body>'")
