"""Typed structures for mail payloads passed between services."""

from typing import TypedDict


class FetchedEmail(TypedDict):
    """Single message returned by GmailService.fetch_emails."""

    id: str
    subject: str
    sender: str
    content: str
