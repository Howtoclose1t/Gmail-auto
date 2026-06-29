from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from gmail_auto_v2.config import CREDENTIALS_FILE, MAX_BODY_LENGTH, SCOPES, TOKEN_FILE
from gmail_auto_v2.parser import extract_body, get_header


@dataclass(frozen=True)
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    snippet: str
    body: str
    label_ids: tuple[str, ...] = ()


def authenticate_gmail(
    credentials_file: Path = CREDENTIALS_FILE,
    token_file: Path = TOKEN_FILE,
) -> Any:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing Gmail API dependencies. Run: pip install -r requirements.txt") from exc

    credentials: Credentials | None = None

    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not credentials_file.exists():
            raise FileNotFoundError(
                "credentials.json was not found. Create a Desktop OAuth client in "
                "Google Cloud Console and place the downloaded file in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        credentials = flow.run_local_server(port=0)

    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials)


def fetch_messages(service: Any, query: str, max_results: int) -> list[EmailMessage]:
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = response.get("messages", [])
    return [_fetch_message(service, item["id"]) for item in messages]


def watch_mailbox(
    service: Any,
    topic_name: str,
    label_ids: list[str] | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "topicName": topic_name,
        "labelIds": label_ids or ["INBOX"],
        "labelFilterBehavior": "INCLUDE",
    }
    return service.users().watch(userId="me", body=request).execute()


def get_profile_email(service: Any) -> str:
    profile = service.users().getProfile(userId="me").execute()
    return str(profile.get("emailAddress") or "").lower()


def fetch_new_messages_from_history(
    service: Any,
    start_history_id: str,
    label_id: str = "INBOX",
) -> list[EmailMessage]:
    message_ids: list[str] = []
    page_token: str | None = None

    while True:
        request = (
            service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
                labelId=label_id,
                pageToken=page_token,
            )
        )
        response = request.execute()

        for history in response.get("history", []):
            for item in history.get("messagesAdded", []):
                message_id = (item.get("message") or {}).get("id")
                if message_id and message_id not in message_ids:
                    message_ids.append(message_id)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    emails: list[EmailMessage] = []
    for message_id in message_ids:
        try:
            emails.append(_fetch_message(service, message_id))
        except Exception as exc:
            if _is_not_found_error(exc):
                print(f"Skipped unreadable Gmail message: {message_id}")
                continue
            raise

    return emails


def archive_message(service: Any, message_id: str) -> dict[str, Any]:
    return modify_message(service, message_id, remove_label_ids=["INBOX"])


def unarchive_message(service: Any, message_id: str) -> dict[str, Any]:
    return modify_message(service, message_id, add_label_ids=["INBOX"])


def star_message(service: Any, message_id: str) -> dict[str, Any]:
    return modify_message(service, message_id, add_label_ids=["STARRED"])


def unstar_message(service: Any, message_id: str) -> dict[str, Any]:
    return modify_message(service, message_id, remove_label_ids=["STARRED"])


def trash_message(service: Any, message_id: str) -> dict[str, Any]:
    return service.users().messages().trash(userId="me", id=message_id).execute()


def untrash_message(service: Any, message_id: str) -> dict[str, Any]:
    return service.users().messages().untrash(userId="me", id=message_id).execute()


def modify_message(
    service: Any,
    message_id: str,
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    body = {
        "addLabelIds": add_label_ids or [],
        "removeLabelIds": remove_label_ids or [],
    }
    return (
        service.users()
        .messages()
        .modify(userId="me", id=message_id, body=body)
        .execute()
    )


def _fetch_message(service: Any, message_id: str) -> EmailMessage:
    message: dict[str, Any] = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    body = extract_body(payload) or message.get("snippet", "")

    return EmailMessage(
        id=message_id,
        thread_id=message.get("threadId", ""),
        subject=get_header(headers, "Subject"),
        sender=get_header(headers, "From"),
        date=_message_date(message),
        snippet=message.get("snippet", ""),
        body=body[:MAX_BODY_LENGTH],
        label_ids=tuple(message.get("labelIds", [])),
    )


def _message_date(message: dict[str, Any]) -> str:
    internal_date = str(message.get("internalDate") or "").strip()
    if not internal_date:
        return ""

    try:
        timestamp = int(internal_date) / 1000
    except ValueError:
        return ""

    local_datetime = datetime.fromtimestamp(timestamp).astimezone()
    return f"{local_datetime:%Y-%m-%d %H:%M:%S} ({_utc_offset_label(local_datetime)})"


def _utc_offset_label(value: datetime) -> str:
    offset = value.utcoffset()
    if offset is None:
        return "UTC"

    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _is_not_found_error(exc: Exception) -> bool:
    status = getattr(getattr(exc, "resp", None), "status", None)
    return int(status or 0) == 404
