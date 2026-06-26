from __future__ import annotations

import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

ROOT_DIR = Path.cwd()
CREDENTIALS_FILE = ROOT_DIR / "credentials.json"
TOKEN_FILE = ROOT_DIR / "token_v2.json"
DEFAULT_OUTPUT_FILE = ROOT_DIR / "data" / "v2_analysis.jsonl"
DEFAULT_STATE_FILE = ROOT_DIR / "data" / "v2_push_state.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = "qwen3:4b"  # "qwen3:8b"
OLLAMA_KEEP_ALIVE_FOREVER = True
OLLAMA_KEEP_ALIVE = -1 if OLLAMA_KEEP_ALIVE_FOREVER else "30m"
GMAIL_PUBSUB_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC", "")
GMAIL_PUBSUB_SUBSCRIPTION = os.getenv("GMAIL_PUBSUB_SUBSCRIPTION", "")

DEFAULT_QUERY = "is:unread in:inbox"
DEFAULT_MAX_EMAILS = 10
MAX_BODY_LENGTH = 8000

