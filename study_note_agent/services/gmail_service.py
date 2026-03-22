import os
import logging
import base64
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

logger = logging.getLogger(__name__)


class GmailService:
    def __init__(
        self, credentials_path="config/credentials.json", token_path="config/token.json"
    ):
        self.creds = None
        self.token_path = token_path

        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(self.creds.to_json())

        self.service = build(
            "gmail", "v1", credentials=self.creds, cache_discovery=False
        )

    def fetch_emails(self, query: str = "is:unread") -> List[Dict]:
        """Fetches emails matching the Gmail search query."""
        try:
            results = (
                self.service.users().messages().list(userId="me", q=query).execute()
            )
        except Exception as e:
            logger.error(f"Error fetching email list: {e}")
            return []

        messages = results.get("messages", [])

        email_data = []
        for msg in messages:
            try:
                msg_id = msg["id"]
                message = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )

                headers = message["payload"].get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "No Subject",
                )
                sender = next(
                    (h["value"] for h in headers if h["name"].lower() == "from"),
                    "Unknown Sender",
                )

                body = self._extract_body(message["payload"])
                clean_text = self._clean_html(body)

                email_data.append(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "sender": sender,
                        "content": clean_text,
                    }
                )
            except Exception as e:
                logger.error(f"Error processing email {msg.get('id', 'Unknown')}: {e}")
                continue

        return email_data

    def _extract_body(self, payload: dict) -> str:
        """Recursively extracts the best available body text from the payload parts."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                elif part["mimeType"] == "text/html" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                elif part["mimeType"].startswith("multipart/"):
                    body = self._extract_body(part)
                    if body:
                        return body
        elif "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        return ""

    def mark_as_read(self, msg_id: str) -> bool:
        """Removes the UNREAD label from the specified email."""
        try:
            self.service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking email {msg_id} as read: {e}")
            return False

    def _clean_html(self, html_content: str) -> str:
        """Converts HTML structurally into Markdown to preserve semantics for the LLM."""
        import markdownify

        # markdownify smartly drops script/style tags and perfectly retains hyperlinks,
        # bold, table layouts, and list elements natively in Markdown output.
        clean_markdown = markdownify.markdownify(html_content, heading_style="ATX")
        return clean_markdown.strip()
