from __future__ import annotations

import json
import subprocess
import sys
import winsound

from gmail_auto_v2.analyzer import EmailAnalysis
from gmail_auto_v2.gmail_client import EmailMessage

NOTIFICATION_WIDTH = 920
NOTIFICATION_HEIGHT = 660


def send_desktop_notification(email: EmailMessage, analysis: EmailAnalysis) -> bool:
    try:
        play_notification_sound()
        payload = {
            "message_id": email.id,
            "thread_id": email.thread_id,
            "subject": email.subject,
            "sender": email.sender,
            "date": email.date,
            "starred": "STARRED" in email.label_ids,
            "category": analysis.category,
            "company": analysis.company.strip() or "Unknown company",
            "position": analysis.position.strip() or "Unknown position",
            "company_position": _company_position(analysis),
            "summary": analysis.summary,
            "verification_code": analysis.verification_code,
            "width": NOTIFICATION_WIDTH,
            "height": NOTIFICATION_HEIGHT,
        }
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gmail_auto_v2.notification_popup",
                json.dumps(payload, ensure_ascii=False),
            ],
            close_fds=True,
        )
        return True
    except Exception as exc:
        print(f"Failed to send desktop notification: {exc}")
        return False


def play_notification_sound() -> None:
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except RuntimeError:
        pass


def _company_position(analysis: EmailAnalysis) -> str:
    company = analysis.company.strip() or "Unknown company"
    position = analysis.position.strip() or "Unknown position"
    return f"{company} / {position}"
