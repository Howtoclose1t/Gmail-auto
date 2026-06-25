from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_PROCESSED_IDS = 2000


def load_history_id(state_file: Path) -> str | None:
    data = load_state(state_file)
    history_id = data.get("history_id")
    return str(history_id) if history_id else None


def load_processed_ids(state_file: Path) -> set[str]:
    data = load_state(state_file)
    processed_ids = data.get("processed_message_ids", [])
    if not isinstance(processed_ids, list):
        return set()
    return {str(message_id) for message_id in processed_ids}


def save_history_id(state_file: Path, history_id: str) -> None:
    save_state(state_file, history_id=history_id, processed_message_ids=[])


def save_state(
    state_file: Path,
    history_id: str,
    processed_message_ids: list[str] | set[str],
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    processed_ids = [str(message_id) for message_id in processed_message_ids]
    data: dict[str, Any] = {
        "history_id": str(history_id),
        "processed_message_ids": processed_ids[-MAX_PROCESSED_IDS:],
    }
    state_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}

    data = json.loads(state_file.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}

