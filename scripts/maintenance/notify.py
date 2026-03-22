#!/usr/bin/env python3
"""Email notification via Gmail SMTP.

Env vars (set as GitHub secrets):
    SMTP_USER: Gmail address (jeff@deltascanner.com)
    SMTP_PASS: Google Workspace app password (16-char)
    NOTIFY_EMAIL: Recipient (millett.jeffrey@gmail.com)

SMTP config: smtp.gmail.com, port 587, STARTTLS
"""
import os
import smtplib
import sys
from email.mime.text import MIMEText


def send_notification(subject: str, body: str) -> bool:
    """Send email via Gmail SMTP with STARTTLS on port 587."""
    user = os.environ.get("SMTP_USER", "")
    pwd = os.environ.get("SMTP_PASS", "")
    to = os.environ.get("NOTIFY_EMAIL", "")

    if not all([user, pwd, to]):
        missing = []
        if not user: missing.append("SMTP_USER")
        if not pwd: missing.append("SMTP_PASS")
        if not to: missing.append("NOTIFY_EMAIL")
        print(f"WARNING: SMTP not configured. Missing: {', '.join(missing)}")
        print(f"\nSubject: {subject}\n{body}")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, pwd)
            server.send_message(msg)
        print(f"Notification sent to {to}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP auth failed: {e}")
        print(f"Check: SMTP_USER={user}, SMTP_PASS length={len(pwd)} chars")
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

    print(f"\n--- EMAIL FALLBACK (stdout) ---\nSubject: {subject}\n{body}\n--- END ---")
    return False


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        ok = send_notification(sys.argv[1], sys.argv[2])
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python notify.py '<subject>' '<body>'")
        sys.exit(1)
