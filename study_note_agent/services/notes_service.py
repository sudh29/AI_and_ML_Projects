import atexit
import logging
import os
import socket

import markdown
import requests
from msal import PublicClientApplication, SerializableTokenCache
from tenacity import retry, stop_after_attempt, wait_exponential

# Force IPv4 to prevent MSAL/requests from indefinitely hanging on broken IPv6 networks
old_getaddrinfo = socket.getaddrinfo


def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    responses = old_getaddrinfo(host, port, family, type, proto, flags)
    return [r for r in responses if r[0] == socket.AF_INET]


socket.getaddrinfo = new_getaddrinfo

SCOPES = ["Notes.Create", "Notes.ReadWrite", "User.Read"]
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0/me/onenote/pages"


class NotesService:
    def __init__(self, token_path="config/onenote_token.json"):
        self.logger = logging.getLogger(__name__)
        self.token_path = token_path
        self.user_email = "Unknown Microsoft Account"

        self.client_id = os.getenv("MS_CLIENT_ID")
        self.authority = "https://login.microsoftonline.com/common"

        if not self.client_id:
            raise ValueError(
                "MS_CLIENT_ID environment variable is missing. You need an Azure AD app registration."
            )

        self.cache = SerializableTokenCache()
        if os.path.exists(self.token_path):
            with open(self.token_path, "r") as f:
                self.cache.deserialize(f.read())

        def save_cache():
            if self.cache.has_state_changed:
                with open(self.token_path, "w") as f:
                    f.write(self.cache.serialize())

        atexit.register(save_cache)

        self.app = PublicClientApplication(
            self.client_id, authority=self.authority, token_cache=self.cache
        )

        self.access_token = self._get_access_token()

    def _get_access_token(self):
        result = None
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])

        if not result:
            self.logger.info(
                "No cached OneNote token found. Opening browser for Microsoft login..."
            )
            result = self.app.acquire_token_interactive(scopes=SCOPES)

        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(
                f"Failed to authenticate with Microsoft: {result.get('error_description', result)}"
            )

    def save_note(self, title: str, markdown_content: str, email_id: str = "") -> bool:
        """Saves generated notes to Microsoft OneNote via Graph API."""

        html_content = markdown.markdown(markdown_content)

        # OneNote requires a strict HTML wrapper
        onenote_html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>{title}</title>
          </head>
          <body>
            {html_content}
          </body>
        </html>
        """

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/xhtml+xml",
        }

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        )
        def _post():
            response = requests.post(
                GRAPH_ENDPOINT, headers=headers, data=onenote_html.encode("utf-8")
            )
            response.raise_for_status()
            return response

        try:
            _post()
            self.logger.info(f"Successfully saved '{title}' to OneNote.")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to save '{title}' to OneNote after retries: {str(e)}"
            )
            return False
