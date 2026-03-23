"""Centralized configuration and constants for the Study Note Agent."""

import os
from pathlib import Path
import tomllib

# ──────────────────────────────────────────────
# Project Paths
# ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent

CONFIG_TOML_PATH = _PROJECT_ROOT / "config" / "config.toml"
CONFIG_JSON_PATH = _PROJECT_ROOT / "config" / "config.json"
CREDENTIALS_PATH = _PROJECT_ROOT / "config" / "credentials.json"
TOKEN_PATH = _PROJECT_ROOT / "config" / "token.json"
ONENOTE_TOKEN_PATH = _PROJECT_ROOT / "config" / "onenote_token.json"
PROCESSED_EMAILS_DB = _PROJECT_ROOT / "config" / "processed_emails.sqlite"
SKILLS_DIR = _PROJECT_ROOT / "skills"
DEFAULT_SKILL = "default.md"


# ──────────────────────────────────────────────
# Config Loader (TOML base + private JSON override)
# ──────────────────────────────────────────────
def _load_config():
    default_config = {
        "target_emails": [],
        "max_emails_per_run": 5,
        "gemini_model": "",
        "scope": [],
        "graph_end_point": "",
        "microsoft_online": "",
        "callmebot_whatsapp_url": "",
        "callmebot_api_key": "",
        "callmebot_phone": "",
    }
    user_config = {}

    # 1. Load public toml config from Github
    if CONFIG_TOML_PATH.exists():
        try:
            with CONFIG_TOML_PATH.open("rb") as f:
                user_config.update(tomllib.load(f))
        except tomllib.TOMLDecodeError:
            pass

    # 2. Override with private json config if exists locally
    if CONFIG_JSON_PATH.exists():
        import json
        import re

        try:
            content = CONFIG_JSON_PATH.read_text()
            content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)
            content = re.sub(r",\s*([\]}])", r"\1", content)
            user_config.update(json.loads(content))
        except json.JSONDecodeError:
            pass

    return {**default_config, **user_config}


_config = _load_config()


# ──────────────────────────────────────────────
# Environment / Secret Keys
# ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "").strip()


# ──────────────────────────────────────────────
# Gmail Settings
# ──────────────────────────────────────────────
TARGET_EMAILS = _config.get("target_emails", [])

SCOPE = _config.get("scope", [])
if isinstance(SCOPE, str):
    SCOPE = [SCOPE] if SCOPE else []

GMAIL_REQUEST_TIMEOUT = 30
GMAIL_LIST_MAX_RESULTS = 100
GMAIL_LIST_MAX_PAGES = 10

MAX_EMAILS_PER_RUN = _config.get("max_emails_per_run", 5)


# ──────────────────────────────────────────────
# Microsoft OneNote / Graph API Settings
# ──────────────────────────────────────────────
ONENOTE_SCOPES = ["Notes.Create", "Notes.ReadWrite", "User.Read"]

GRAPH_ENDPOINT = _config.get("graph_end_point", "")
MICROSOFTONLINE = _config.get("microsoft_online", "")

ONENOTE_REQUEST_TIMEOUT = 15


# ──────────────────────────────────────────────
# Gemini LLM Settings
# ──────────────────────────────────────────────
GEMINI_MODEL = _config.get("gemini_model", "")
GEMINI_REQUEST_TIMEOUT = 30


# ──────────────────────────────────────────────
# CallMeBot WhatsApp Notification Settings
# ──────────────────────────────────────────────
CALLMEBOT_WHATSAPP_URL = _config.get("callmebot_whatsapp_url", "")
CALLMEBOT_PHONE_FALLBACK = str(_config.get("callmebot_phone", "")).strip()
CALLMEBOT_API_KEY_FALLBACK = str(_config.get("callmebot_api_key", "")).strip()
CALLMEBOT_REQUEST_TIMEOUT = 15
CALLMEBOT_MAX_MESSAGE_CHARS = 4000


# ──────────────────────────────────────────────
# Concurrency
# ──────────────────────────────────────────────
MAX_WORKERS_POOL = 5


# ──────────────────────────────────────────────
# LLM Prompts
# ──────────────────────────────────────────────
PROMPT_GENERATE_NOTES = """\
You are an expert technical summarizer and educator. \
Your job is to read an email and extract the valuable information \
into structured, revision-friendly notes.
Ignore pleasantries, disclaimers, signatures, and logistical noise.

Format your response in Markdown using exactly this structure:
# [Email Subject]

## Summary
[2-3 sentence high-level overview]

## Key Concepts
* [Concept 1]: [Brief explanation]
* [Concept 2]: [Brief explanation]

## Detailed Notes
[Organized bullet points containing the core information, \
examples, and technical details]

## Quick Revision
[3-4 rapid-fire Q&A style points or a TL;DR for quick memory recall]
"""

PROMPT_PROOFREAD_NOTES = """\
You are an expert technical reviewer.
Your job is to read the original email content and the generated \
structured notes, and proofread the notes to ensure they are 100% \
accurate, capture all key details, and do not contain any hallucinations.

Fix any inaccuracies, grammatical errors, or missing critical details. \
Return ONLY the finalized, corrected Markdown notes in the exact same format.
"""
