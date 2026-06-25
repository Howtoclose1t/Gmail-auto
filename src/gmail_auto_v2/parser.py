from __future__ import annotations

import base64
import html
import re
from email.header import decode_header
from typing import Any


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""

    output: list[str] = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            output.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            output.append(part)

    return "".join(output).strip()


def decode_base64url(data: str | None) -> str:
    if not data:
        return ""

    padding = "=" * (-len(data) % 4)
    try:
        decoded = base64.urlsafe_b64decode(data + padding)
    except Exception:
        return ""

    return decoded.decode("utf-8", errors="replace")


def clean_html(html_text: str) -> str:
    text = re.sub(
        r"<(script|style).*?>.*?</\1>",
        " ",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def get_header(headers: list[dict[str, str]], header_name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return decode_mime_header(header.get("value"))
    return ""


def extract_body(payload: dict[str, Any]) -> str:
    plain_text_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime_type = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")

        if data:
            decoded = decode_base64url(data)
            if mime_type == "text/plain":
                plain_text_parts.append(decoded)
            elif mime_type == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)

    if plain_text_parts:
        body = "\n".join(plain_text_parts)
    elif html_parts:
        body = clean_html("\n".join(html_parts))
    else:
        body = ""

    body = re.sub(r"\r\n?", "\n", body)
    body = re.sub(r"\n{4,}", "\n\n\n", body)
    return body.strip()

