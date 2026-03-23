"""CLI entry point for the Study Note Agent."""

import argparse
import socket

from dotenv import load_dotenv

# Load environment variables early before importing constants/services
load_dotenv()

import constants  # noqa: E402
from logging_config import setup_logging  # noqa: E402

setup_logging()


def main() -> None:
    # Prefer IPv4 to avoid MSAL/Gmail/Graph hanging on broken IPv6.
    _original_getaddrinfo = socket.getaddrinfo

    def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        responses = _original_getaddrinfo(host, port, family, type, proto, flags)
        return [r for r in responses if r[0] == socket.AF_INET]

    socket.getaddrinfo = _ipv4_getaddrinfo

    parser = argparse.ArgumentParser(description="AI Agent to turn Emails into OneNote")
    parser.add_argument(
        "--limit",
        type=int,
        default=constants.MAX_EMAILS_PER_RUN,
        help="Maximum number of emails to process in one run",
    )
    parser.add_argument(
        "--whatsapp",
        action="store_true",
        default=False,
        help="Enable WhatsApp notifications via CallMeBot (disabled by default)",
    )
    args = parser.parse_args()

    from agent import run  # noqa: E402

    run(limit=args.limit, enable_whatsapp=args.whatsapp)


if __name__ == "__main__":
    main()
