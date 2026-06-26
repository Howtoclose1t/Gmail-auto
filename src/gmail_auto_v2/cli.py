from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import threading
from pathlib import Path
from typing import Any

from gmail_auto_v2.analyzer import analyze_email
from gmail_auto_v2.config import (
    DEFAULT_MAX_EMAILS,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_QUERY,
    DEFAULT_STATE_FILE,
    GMAIL_PUBSUB_SUBSCRIPTION,
    GMAIL_PUBSUB_TOPIC,
)
from gmail_auto_v2.gmail_client import (
    EmailMessage,
    authenticate_gmail,
    fetch_messages,
    fetch_new_messages_from_history,
    get_profile_email,
    watch_mailbox,
)
from gmail_auto_v2.notifier import send_desktop_notification
from gmail_auto_v2.push_state import (
    load_history_id,
    load_processed_ids,
    save_history_id,
    save_state,
)
from gmail_auto_v2.storage import append_result


def main() -> None:
    args = parse_args()

    if args.setup_push:
        setup_push(args)
        return

    if args.receive_push:
        receive_push(args)
        return

    run_once(args)


def run_once(args: argparse.Namespace) -> None:
    try:
        service = authenticate_gmail()
        emails = fetch_messages(service, query=args.query, max_results=args.max)
    except Exception as exc:
        raise SystemExit(f"Failed to read Gmail messages: {exc}") from exc

    if not emails:
        print("No emails matched the current query.")
        return

    analyze_and_store(
        emails,
        Path(args.output),
        desktop_notify=not args.no_desktop_notify,
    )
    print(f"\nAnalysis results saved to {Path(args.output).resolve()}")


def setup_push(args: argparse.Namespace) -> None:
    topic = args.topic or GMAIL_PUBSUB_TOPIC
    if not topic:
        raise SystemExit(
            "Missing Pub/Sub topic. Pass --topic projects/PROJECT_ID/topics/TOPIC_NAME "
            "or set GMAIL_PUBSUB_TOPIC."
        )

    try:
        service = authenticate_gmail()
        response = watch_mailbox(service, topic_name=topic)
    except Exception as exc:
        raise SystemExit(f"Failed to set up Gmail push subscription: {exc}") from exc

    history_id = str(response["historyId"])
    save_history_id(Path(args.state), history_id)
    print("Gmail push subscription has been enabled.")
    print(f"Current historyId: {history_id}")
    print(f"Expiration timestamp: {response.get('expiration', 'unknown')}")
    print("Run --setup-push again at least every 7 days; daily renewal is recommended.")


def receive_push(args: argparse.Namespace) -> None:
    subscription = args.subscription or GMAIL_PUBSUB_SUBSCRIPTION
    if not subscription:
        raise SystemExit(
            "Missing Pub/Sub subscription. Pass "
            "--subscription projects/PROJECT_ID/subscriptions/SUBSCRIPTION_NAME "
            "or set GMAIL_PUBSUB_SUBSCRIPTION."
        )

    try:
        from google.cloud import pubsub_v1
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing Pub/Sub dependency. Run: pip install -r requirements.txt") from exc

    gmail_service = authenticate_gmail()
    current_email = get_profile_email(gmail_service)
    subscriber = pubsub_v1.SubscriberClient()
    scheduler = pubsub_v1.subscriber.scheduler.ThreadScheduler(
        concurrent.futures.ThreadPoolExecutor(max_workers=1)
    )
    flow_control = pubsub_v1.types.FlowControl(max_messages=1)
    processing_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    output_file = Path(args.output)
    state_file = Path(args.state)
    callback_lock = threading.Lock()

    def callback(message: Any) -> None:
        try:
            notification = decode_pubsub_notification(message.data)
        except Exception as exc:
            message.nack()
            print(f"Failed to process push notification; it will be retried later: {exc}")
            return

        message.ack()
        processing_executor.submit(handle_notification, notification)

    def handle_notification(notification: dict[str, str]) -> None:
        try:
            with callback_lock:
                process_notification(
                    gmail_service,
                    notification,
                    output_file=output_file,
                    state_file=state_file,
                    desktop_notify=not args.no_desktop_notify,
                    current_email=current_email,
                )
        except Exception as exc:
            print(f"Failed to process Gmail notification; state was not advanced and the next notification will catch up: {exc}")

    future = subscriber.subscribe(
        subscription,
        callback=callback,
        scheduler=scheduler,
        flow_control=flow_control,
    )
    print(f"Receiving Gmail push notifications from: {subscription}")
    print("New email notifications will automatically fetch and analyze changes. Press Ctrl+C to exit.")

    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()
        processing_executor.shutdown(wait=False, cancel_futures=True)
        print("\nStopped receiving push notifications.")


def decode_pubsub_notification(data: bytes) -> dict[str, str]:
    try:
        payload = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        padded_data = data + b"=" * (-len(data) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_data).decode("utf-8"))

    return {str(key): str(value) for key, value in payload.items()}


def process_notification(
    service: Any,
    notification: dict[str, str],
    output_file: Path,
    state_file: Path,
    desktop_notify: bool,
    current_email: str = "",
) -> None:
    new_history_id = notification.get("historyId")
    if not new_history_id:
        print("Received a notification without historyId; skipping.")
        return

    notification_email = str(notification.get("emailAddress") or "").lower()
    if current_email and notification_email and notification_email != current_email:
        print(f"Received a Gmail notification for another mailbox; skipping: {notification_email}")
        return

    previous_history_id = load_history_id(state_file)
    if not previous_history_id:
        save_history_id(state_file, new_history_id)
        print(f"Initialized historyId: {new_history_id}. New emails will be analyzed from the next notification.")
        return

    if _history_id_lte(new_history_id, previous_history_id):
        print(f"Received an old Gmail notification; skipping. historyId: {new_history_id}")
        return

    processed_ids = load_processed_ids(state_file)
    emails = fetch_new_messages_from_history(
        service,
        start_history_id=previous_history_id,
    )
    new_emails = [email for email in emails if email.id not in processed_ids]

    if not new_emails:
        save_state(state_file, new_history_id, processed_ids)
        print(f"Received mailbox change notification, but no new inbox emails were found. historyId: {new_history_id}")
        return

    skipped_count = len(emails) - len(new_emails)
    if skipped_count:
        print(f"Skipped {skipped_count} duplicate emails.")

    print(f"Received {len(new_emails)} new emails; starting analysis.")
    analyzed_ids = analyze_and_store(
        new_emails,
        output_file,
        desktop_notify=desktop_notify,
    )
    save_state(state_file, new_history_id, processed_ids | set(analyzed_ids))


def analyze_and_store(
    emails: list[EmailMessage],
    output_file: Path,
    desktop_notify: bool,
) -> list[str]:
    print(f"Found {len(emails)} emails; starting analysis.\n")

    analyzed_ids: list[str] = []
    for index, email in enumerate(emails, start=1):
        print(f"Calling Ollama to analyze: {email.subject or 'No subject'}")
        try:
            analysis = analyze_email(email)
        except Exception as exc:
            raise RuntimeError(
                "AI analysis failed. Make sure Ollama is running and the model has been downloaded.\n"
                f"Error: {exc}"
            ) from exc

        append_result(output_file, email, analysis)
        analyzed_ids.append(email.id)
        print_result(index, email, analysis)
        if desktop_notify:
            send_desktop_notification(email, analysis)

    return analyzed_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gmail Auto v2: read Gmail, classify with local Ollama, and show Qt buttons for archive/delete/star toggle."
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_EMAILS,
        help=f"Maximum number of emails to read. Default: {DEFAULT_MAX_EMAILS}.",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Gmail search query. Default: {DEFAULT_QUERY}",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_FILE),
        help=f"JSONL output file. Default: {DEFAULT_OUTPUT_FILE}",
    )
    parser.add_argument(
        "--setup-push",
        action="store_true",
        help="Register Gmail Pub/Sub push notifications.",
    )
    parser.add_argument(
        "--receive-push",
        action="store_true",
        help="Receive Pub/Sub notifications and analyze new emails when notifications arrive.",
    )
    parser.add_argument(
        "--topic",
        default="",
        help="Pub/Sub topic, for example projects/my-project/topics/gmail-updates.",
    )
    parser.add_argument(
        "--subscription",
        default="",
        help="Pub/Sub subscription, for example projects/my-project/subscriptions/gmail-updates-sub.",
    )
    parser.add_argument(
        "--state",
        default=str(DEFAULT_STATE_FILE),
        help=f"Push state file. Default: {DEFAULT_STATE_FILE}",
    )
    parser.add_argument(
        "--no-desktop-notify",
        action="store_true",
        help="Disable desktop notifications.",
    )
    return parser.parse_args()


def print_result(index: int, email: EmailMessage, analysis: object) -> None:
    print("=" * 80)
    print(f"Email {index}")
    print(f"Subject: {email.subject or 'No subject'}")
    print(f"Sender: {email.sender or 'unknown'}")
    print(f"Date: {email.date or 'unknown'}")
    print(f"Category: {getattr(analysis, 'category', 'unknown')}")
    print(f"Importance: {getattr(analysis, 'importance', 'unknown')}")
    print(f"Summary: {getattr(analysis, 'summary', '')}")

    company = getattr(analysis, "company", "")
    position = getattr(analysis, "position", "")
    if company or position:
        print(f"Company/position: {company or 'unknown'} / {position or 'unknown'}")

    verification_code = getattr(analysis, "verification_code", "")
    if verification_code:
        print(f"Verification code: {verification_code}")

    actions = getattr(analysis, "actions", []) or []
    if actions:
        print("Action items:")
        for action in actions:
            print(f"  - {action}")
    else:
        print("Action items: none")

    dates = getattr(analysis, "dates", []) or []
    if dates:
        print("Dates and times:")
        for date in dates:
            print(f"  - {date}")

    should_reply = getattr(analysis, "should_reply", False)
    print(f"Reply recommended: {'yes' if should_reply else 'no'}")
    print(f"Reason: {getattr(analysis, 'reply_reason', '')}")
    print()


def _history_id_lte(left: str, right: str) -> bool:
    try:
        return int(left) <= int(right)
    except ValueError:
        return left <= right
