from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gmail_auto_v2.analyzer import EmailAnalysis, analysis_to_dict
from gmail_auto_v2.gmail_client import EmailMessage


def append_result(
    output_file: Path,
    email: EmailMessage,
    analysis: EmailAnalysis,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "email": asdict(email) | {"body": email.body[:1000]},
        "analysis": analysis_to_dict(analysis),
    }

    with output_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

