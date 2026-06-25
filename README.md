# Gmail Auto v2

Gmail Auto v2 is a local Gmail assistant that reads recent inbox messages, asks a local Ollama model to classify and summarize them, and can show desktop notifications with quick actions for archive, star, and unstar.

The app is designed to keep email content on your machine. It uses the Gmail API for mailbox access and a local Ollama endpoint for analysis.

## Features

- Fetch recent Gmail messages with a configurable Gmail search query.
- Classify messages into categories such as application confirmation, interview, rejection, application progress, bill, notification, advertisement, personal, and other.
- Generate concise summaries, action items, dates, company names, position titles, and reply recommendations.
- Extract verification codes only when the message clearly contains an OTP, security code, or verification code.
- Save analysis results as JSONL.
- Receive Gmail push notifications through Google Cloud Pub/Sub and analyze new inbox messages incrementally.
- Show a PyQt desktop popup with archive, star, unstar, and copy-code buttons.

## Privacy Notes

Do not commit any local OAuth or runtime files. The included `.gitignore` excludes the expected private files:

- `credentials.json`
- `token.json`
- `token_v2.json`
- `.env`
- `data/`

You still need to create your own `credentials.json` locally from a Google Cloud Desktop OAuth client before running the app.

## Requirements

- Python 3.10 or newer
- Ollama running locally
- A downloaded Ollama model, for example `qwen3:8b`
- Gmail API enabled in a Google Cloud project
- Optional: Google Cloud Pub/Sub for push notifications

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Install the package in editable mode if you want the `gmail-auto-v2` command:

```powershell
pip install -e .
```

Pull and run an Ollama model:

```powershell
ollama pull qwen3:8b
ollama serve
```

To use another local model:

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
```

## Google Setup

1. Enable the Gmail API in Google Cloud Console.
2. Create an OAuth Client ID with application type `Desktop app`.
3. Download the OAuth file and save it as `credentials.json` in the project root.
4. For desktop notification actions such as archive/star/unstar, the app uses the Gmail `gmail.modify` scope.

On first run, Google will open an authorization page. After approval, the app creates `token_v2.json` locally. This file is private and should not be committed.

## One-Time Analysis

```powershell
python -m gmail_auto_v2 --max 10
```

Common options:

```powershell
python -m gmail_auto_v2 --max 20
python -m gmail_auto_v2 --query "is:unread in:inbox newer_than:7d"
python -m gmail_auto_v2 --output data/today.jsonl
```

After editable installation, you can also use:

```powershell
gmail-auto-v2 --max 10
```

## Gmail Push Notifications

Gmail push notifications require Google Cloud Pub/Sub. Gmail does not push full email content directly. The flow is:

1. Gmail sends a mailbox-change notification to a Pub/Sub topic.
2. This app receives the Pub/Sub message and reads the new `historyId`.
3. The app calls the Gmail History API from the last saved `historyId`.
4. New inbox messages are fetched and analyzed locally.

Create a Pub/Sub topic and subscription in your Google Cloud project, then grant `gmail-api-push@system.gserviceaccount.com` the Pub/Sub Publisher role on the topic.

Example resource names:

```text
projects/YOUR_PROJECT_ID/topics/gmail-updates
projects/YOUR_PROJECT_ID/subscriptions/gmail-updates-sub
```

Register or renew the Gmail watch:

```powershell
python -m gmail_auto_v2 --setup-push --topic projects/YOUR_PROJECT_ID/topics/gmail-updates
```

Start receiving notifications:

```powershell
python -m gmail_auto_v2 --receive-push --subscription projects/YOUR_PROJECT_ID/subscriptions/gmail-updates-sub
```

You can also use environment variables:

```powershell
$env:GMAIL_PUBSUB_TOPIC="projects/YOUR_PROJECT_ID/topics/gmail-updates"
$env:GMAIL_PUBSUB_SUBSCRIPTION="projects/YOUR_PROJECT_ID/subscriptions/gmail-updates-sub"
```

Gmail watches expire and should be renewed at least every 7 days. A daily scheduled renewal is recommended.

## Configuration

Useful environment variables:

- `OLLAMA_URL`: Ollama chat endpoint. Default: `http://localhost:11434/api/chat`.
- `OLLAMA_MODEL`: Ollama model name. Default is defined in `gmail_auto_v2.config`.
- `GMAIL_PUBSUB_TOPIC`: default topic for `--setup-push`.
- `GMAIL_PUBSUB_SUBSCRIPTION`: default subscription for `--receive-push`.

Runtime output defaults to:

- Analysis results: `data/v2_analysis.jsonl`
- Push state: `data/v2_push_state.json`

## Project Structure

```text
src/gmail_auto_v2/
  __main__.py              CLI module entry point
  cli.py                   Command-line workflow and push processing
  config.py                Default paths and environment variables
  gmail_client.py          Gmail OAuth, message fetching, and mailbox actions
  parser.py                Email body parsing helpers
  analyzer.py              Ollama prompt and response normalization
  notification_popup.py    PyQt desktop popup
  notifier.py              Notification launcher and sound
  push_state.py            Gmail historyId and processed-id state
  storage.py               JSONL result writing
```
