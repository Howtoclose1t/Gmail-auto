from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from gmail_auto_v2.config import OLLAMA_KEEP_ALIVE, OLLAMA_MODEL, OLLAMA_URL
from gmail_auto_v2.gmail_client import EmailMessage
from gmail_auto_v2.prompt import build_prompt


@dataclass(frozen=True)
class EmailAnalysis:
    category: str
    importance: str
    summary: str
    actions: list[str]
    dates: list[str]
    company: str
    position: str
    verification_code: str
    should_reply: bool
    reply_reason: str


def analyze_email(
    email: EmailMessage,
    ollama_url: str = OLLAMA_URL,
    model: str = OLLAMA_MODEL,
    keep_alive: str | int = OLLAMA_KEEP_ALIVE,
) -> EmailAnalysis:
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing requests dependency. Run: pip install -r requirements.txt") from exc

    response = requests.post(
        ollama_url,
        json={
            "model": model,
            "messages": [{"role": "user", "content": build_prompt(email)}],
            "stream": False,
            "format": "json",
            "keep_alive": keep_alive,
            "options": {"temperature": 0.1},
        },
        timeout=180,
    )
    response.raise_for_status()

    payload = response.json()
    content = (payload.get("message") or {}).get("content", "")
    return normalize_analysis(parse_json_content(content), email)


def parse_json_content(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "category": "parse_failed",
        "importance": "unknown",
        "summary": content.strip(),
        "actions": [],
        "dates": [],
        "company": "",
        "position": "",
        "verification_code": "",
        "should_reply": False,
        "reply_reason": "Model did not return valid JSON.",
    }


def normalize_analysis(
    data: dict[str, Any],
    email: EmailMessage | None = None,
) -> EmailAnalysis:
    summary = str(
        data.get("summary")
        or data.get("summary_original")
        or data.get("summary_zh")
        or ""
    )
    return EmailAnalysis(
        category=str(data.get("category") or "other"),
        importance=str(data.get("importance") or "unknown"),
        summary=summary,
        actions=_string_list(data.get("actions")),
        dates=_string_list(data.get("dates")),
        company=str(data.get("company") or ""),
        position=str(data.get("position") or ""),
        verification_code=_verified_code(str(data.get("verification_code") or ""), email),
        should_reply=bool(data.get("should_reply")),
        reply_reason=str(data.get("reply_reason") or ""),
    )


def analysis_to_dict(analysis: EmailAnalysis) -> dict[str, Any]:
    return asdict(analysis)


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


_VERIFICATION_CONTEXT_RE = re.compile(
    r"验证码|校验码|动态码|一次性密码|安全代码|"
    r"verification\s*code|security\s*code|one[-\s]?time\s*(?:password|code)|"
    r"\botp\b|passcode|authentication\s*code",
    flags=re.IGNORECASE,
)


def _verified_code(candidate: str, email: EmailMessage | None) -> str:
    code = candidate.strip()
    if not code:
        return ""

    compact_code = re.sub(r"[\s-]+", "", code)
    if not _looks_like_verification_code(compact_code):
        return ""

    if email is None:
        return code

    haystack = "\n".join([email.subject or "", email.body or ""])
    compact_haystack = re.sub(r"[\s-]+", "", haystack)
    if compact_code not in compact_haystack:
        return ""

    if _has_verification_context_near_code(haystack, code):
        return code

    # Some real OTP emails put the code alone in the body and the context in the subject.
    if _VERIFICATION_CONTEXT_RE.search(haystack) and _body_is_mostly_code(email.body or "", code):
        return code

    return ""


def _looks_like_verification_code(code: str) -> bool:
    if not 4 <= len(code) <= 12:
        return False
    if not re.fullmatch(r"[A-Za-z0-9]+", code):
        return False
    if code.isalpha() and len(code) > 8:
        return False
    return bool(re.search(r"\d", code))


def _has_verification_context_near_code(text: str, code: str) -> bool:
    normalized_code = re.escape(re.sub(r"[\s-]+", "", code))
    flexible_code = r"[\s-]*".join(normalized_code)
    for match in re.finditer(flexible_code, text, flags=re.IGNORECASE):
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 120)
        if _VERIFICATION_CONTEXT_RE.search(text[start:end]):
            return True
    return False


def _body_is_mostly_code(body: str, code: str) -> bool:
    body_text = re.sub(r"\s+", " ", body).strip()
    if not body_text:
        return False
    body_without_code = re.sub(re.escape(code), "", body_text, flags=re.IGNORECASE)
    body_without_code = re.sub(r"[\s:：。；;,.，]+", "", body_without_code)
    return len(body_without_code) <= 20
