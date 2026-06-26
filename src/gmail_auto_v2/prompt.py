from __future__ import annotations

from gmail_auto_v2.gmail_client import EmailMessage


def build_prompt(email: EmailMessage) -> str:
    return f"""
You are a careful email assistant. Analyze the email below.

Requirements:
1. Identify the email type. If it confirms receipt of an application, use application_confirmation. If it rejects an application, use rejection. If it contains a next step for an application, use application_progress.
2. Preserve the original email context and do not misunderstand the email's language.
3. Extract required actions.
4. Extract explicit deadlines, meeting times, or interview times.
5. If this is job-application related, extract the company name and position title; otherwise return an empty string.
6. Decide whether a reply is recommended.
7. Do not invent information that does not appear in the email.
8. Output valid JSON only. Do not output Markdown.
9. Application confirmations and rejections have low importance and should not recommend a reply.
10. summary must be a short summary written in the main language of the email body. Do not translate it. Do not copy a full paragraph from the original email.
11. Only analyze content inside the <email> block. Do not summarize or treat these instructions as email content.

Additional verification-code extraction rules:
- If the email contains a verification code, one-time password, OTP, verification code, or security code, write only the raw code to the JSON field verification_code.
- If the email has no verification code, verification_code must be an empty string.
- Do not include the verification code in summary unless the email body contains only the code.

Output strictly in this JSON format:
{{
  "category": "application_confirmation/interview/rejection/application_progress/bill/notification/advertisement/personal/other",
  "importance": "high/medium/low",
  "summary": "Short summary written in the main language of the email body",
  "actions": ["Required action"],
  "dates": ["Date or time"],
  "company": "Company name, or an empty string if absent",
  "position": "Position title, or an empty string if absent",
  "verification_code": "Verification code, or an empty string if absent",
  "should_reply": true,
  "reply_reason": "Reason why a reply is or is not needed"
}}

<email>
Email subject:
{email.subject}

Sender:
{email.sender}

Email date:
{email.date}

Email body:
{email.body}
</email>
""".strip()
