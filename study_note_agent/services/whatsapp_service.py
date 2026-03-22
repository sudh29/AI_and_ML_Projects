"""Notify via CallMeBot WhatsApp HTTP API after notes are saved.

Setup: https://www.callmebot.com/blog/free-api-whatsapp-messages/

Enable with either environment variables or ``config.json`` (env wins):
``CALLMEBOT_API_KEY``, ``CALLMEBOT_PHONE`` (E.164, e.g. +34123456789), optional
``callmebot_whatsapp_url``. If phone and api key are both missing after merge,
notifications are skipped (no error).
"""

from __future__ import annotations

import logging
import os
import threading

import constants
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Tutorial / placeholder values from docs — treat as unset so real keys can come from config fallback
_PLACEHOLDER_API_KEYS = frozenset(
    {
        "your_api_key_from_the_bot",
        "your_api_key_here",
        "changeme",
        "xxx",
        "<apikey>",
    }
)

_PLACEHOLDER_PHONES = frozenset(
    {
        "your_phone_here",
        "changeme",
    }
)


def _callmebot_response_indicates_failure(body: str) -> bool:
    """Detect error-style payloads when HTTP status is still 200."""
    raw = (body or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    if lower.startswith("error"):
        return True
    # Broad but API replies are short; avoids missing failures that omit the word "error"
    markers = (
        "error",
        "invalid api",
        "invalid key",
        "wrong api",
        "unauthorized",
        "not allowed",
        "blocked",
        "quota",
    )
    return any(m in lower for m in markers)


def _effective_api_key(env_value: str, fallback: str) -> str:
    for candidate in ((env_value or "").strip(), (fallback or "").strip()):
        if not candidate:
            continue
        if candidate.strip().lower() in _PLACEHOLDER_API_KEYS:
            continue
        return candidate
    return ""


def _effective_phone(env_value: str, fallback: str) -> str:
    for candidate in ((env_value or "").strip(), (fallback or "").strip()):
        if not candidate:
            continue
        if candidate.strip().lower() in _PLACEHOLDER_PHONES:
            continue
        return candidate
    return ""


class WhatsAppService:
    """Send WhatsApp text messages through CallMeBot's personal-use API."""

    def __init__(self) -> None:
        self._api_key = _effective_api_key(
            os.getenv("CALLMEBOT_API_KEY") or "",
            constants.CALLMEBOT_API_KEY_FALLBACK,
        )
        self._phone = _effective_phone(
            os.getenv("CALLMEBOT_PHONE") or "",
            constants.CALLMEBOT_PHONE_FALLBACK,
        )
        self._enabled = bool(self._api_key and self._phone)
        self._lock = threading.Lock()

        if not self._enabled:
            logger.debug(
                "CallMeBot WhatsApp notifications disabled "
                "(set CALLMEBOT_API_KEY and CALLMEBOT_PHONE, or callmebot_* in config.json)."
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _truncate(self, text: str) -> str:
        if len(text) <= constants.CALLMEBOT_MAX_MESSAGE_CHARS:
            return text
        return text[: constants.CALLMEBOT_MAX_MESSAGE_CHARS - 1] + "…"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    def _get(self, params: dict[str, str]) -> requests.Response:
        response = requests.get(
            constants.CALLMEBOT_WHATSAPP_URL,
            params=params,
            timeout=constants.CALLMEBOT_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response

    def send_text(self, text: str) -> bool:
        """Send arbitrary text. Returns True if skipped (disabled), sent, or accepted."""
        body = self._truncate(text)
        if not self._enabled:
            return True

        params = {
            "phone": self._phone,
            "text": body,
            "apikey": self._api_key,
        }
        try:
            with self._lock:
                response = self._get(params)
            raw = (response.text or "").strip()
            if _callmebot_response_indicates_failure(raw):
                logger.error("CallMeBot returned an error in body: %s", raw[:500])
                return False
            logger.debug("CallMeBot WhatsApp response: %s", raw[:200])
            return True
        except requests.RequestException as e:
            logger.error("CallMeBot WhatsApp request failed: %s", e)
            return False

    def notify_note_saved(self, subject: str, preview: str | None = None) -> bool:
        """Notify that study notes were saved to OneNote."""
        lines = [
            "*Study Note Agent* — notes saved to OneNote",
            f"*Subject:* {subject}",
        ]
        if preview:
            lines.append("")
            lines.append(self._truncate(preview))
        return self.send_text("\n".join(lines))
