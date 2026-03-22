import base64

from services.gmail_service import GmailService


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_extract_body_prefers_html_over_plain() -> None:
    g = GmailService.__new__(GmailService)
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain only")}},
            {
                "mimeType": "text/html",
                "body": {"data": _b64("<html><body><p>html bit</p></body></html>")},
            },
        ],
    }
    body = g._extract_body(payload)
    assert "html bit" in body


def test_extract_body_nested_multipart() -> None:
    g = GmailService.__new__(GmailService)
    inner = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>nested</p>")}},
        ],
    }
    payload = {"mimeType": "multipart/mixed", "parts": [inner]}
    assert "nested" in g._extract_body(payload)
