# constants.py
import json
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def _load_config(filepath=None):
    if filepath is None:
        filepath = _PROJECT_ROOT / "config" / "config.json"
    filepath = Path(filepath)
    default_config = {
        "target_emails": [],
        "max_emails_per_run": 5,
    }
    if filepath.exists():
        try:
            content = filepath.read_text()
            # Flexibly strip JSON comments (//) so you can temporarily disable emails!
            content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)
            # Strip trailing commas that become exposed when the last array item is commented out
            content = re.sub(r",\s*([\]}])", r"\1", content)
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    return default_config


_config = _load_config()

# List of email addresses to monitor for extraction
TARGET_EMAILS = _config.get("target_emails", [])

# Maximum number of emails to process in one execution
MAX_EMAILS_PER_RUN = _config.get("max_emails_per_run", 5)

# Concurrency settings
MAX_WORKERS_POOL = 5

# API timeouts (in seconds)
ONENOTE_REQUEST_TIMEOUT = 15
GEMINI_REQUEST_TIMEOUT = 30
GMAIL_REQUEST_TIMEOUT = 30
CALLMEBOT_REQUEST_TIMEOUT = 15

# CallMeBot WhatsApp free API message size guard (URL length / provider limits)
CALLMEBOT_MAX_MESSAGE_CHARS = 4000

# CallMeBot optional defaults from config.json; env CALLMEBOT_* overrides (see WhatsAppService)
CALLMEBOT_WHATSAPP_URL = _config.get("callmebot_whatsapp_url") or (
    "https://api.callmebot.com/whatsapp.php"
)
CALLMEBOT_PHONE_FALLBACK = (_config.get("callmebot_phone") or "").strip()
CALLMEBOT_API_KEY_FALLBACK = (_config.get("callmebot_api_key") or "").strip()

# Gmail messages.list pagination (see GmailService.fetch_emails)
GMAIL_LIST_MAX_RESULTS = 100
GMAIL_LIST_MAX_PAGES = 10

# LLM settings (loaded from config)
GEMINI_MODEL = _config.get("gemini_model", "gemini-2.5-flash")

# Deduplication storage
PROCESSED_EMAILS_FILE = _PROJECT_ROOT / "config" / "processed_emails.json"

PROMPT_GENERATE_NOTES = """
You are an expert technical summarizer and educator. 
Your job is to read an email and extract the valuable information into structured, revision-friendly notes.
Ignore pleasantries, disclaimers, signatures, and logistical noise.

Format your response in Markdown using exactly this structure:
# [Email Subject]

## Summary
[2-3 sentence high-level overview]

## Key Concepts
* [Concept 1]: [Brief explanation]
* [Concept 2]: [Brief explanation]

## Detailed Notes
[Organized bullet points containing the core information, examples, and technical details]

## Quick Revision
[3-4 rapid-fire Q&A style points or a TL;DR for quick memory recall]
"""

PROMPT_PROOFREAD_NOTES = """
You are an expert technical reviewer.
Your job is to read the original email content and the generated structured notes, 
and proofread the notes to ensure they are 100% accurate, capture all key details, 
and do not contain any hallucinations.

Fix any inaccuracies, grammatical errors, or missing critical details. 
Return ONLY the finalized, corrected Markdown notes in the exact same format.
"""
