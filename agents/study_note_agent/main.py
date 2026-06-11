"""CLI entry point for the Study Note Agent."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import socket
from typing import Sequence

from dotenv import load_dotenv

# Load environment variables early before importing constants/services.
load_dotenv()

import constants  # noqa: E402
from logging_config import setup_logging  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)


def _prefer_ipv4() -> None:
    """Prefer IPv4 to avoid MSAL/Gmail/Graph hanging on broken IPv6."""
    if getattr(socket, "_study_note_agent_ipv4_patch", False):
        return

    original_getaddrinfo = socket.getaddrinfo

    def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        responses = original_getaddrinfo(host, port, family, type, proto, flags)
        ipv4_responses = [r for r in responses if r[0] == socket.AF_INET]
        return ipv4_responses or responses

    socket.getaddrinfo = ipv4_getaddrinfo
    socket._study_note_agent_ipv4_patch = True


def _handle_fetch_raw(args: argparse.Namespace) -> int:
    from agent import build_gmail_search_query
    from services.gmail_service import GmailService
    from services.local_file_service import build_gmail_stem, write_raw_text

    query = args.query or build_gmail_search_query()
    gmail = GmailService()
    emails = gmail.fetch_emails(query=query)
    emails_to_save = emails[: args.limit]

    written = 0
    skipped = 0
    for email in emails_to_save:
        result = write_raw_text(
            build_gmail_stem(email),
            email["content"],
            {
                "source": "gmail",
                "source_id": email["id"],
                "subject": email["subject"],
                "sender": email["sender"],
            },
            raw_dir=args.raw_dir,
            overwrite=args.overwrite,
        )
        if result.skipped:
            skipped += 1
            logger.info("Skipped existing raw text: %s", result.path)
        else:
            written += 1
            logger.info("Saved raw email text: %s", result.path)

    logger.info(
        "Raw email capture complete: %d written, %d skipped, %d fetched.",
        written,
        skipped,
        len(emails),
    )
    return 0


def _handle_raw_to_md(args: argparse.Namespace) -> int:
    from services.llm_service import LLMService
    from services.local_file_service import (
        iter_raw_text_files,
        markdown_path_for_stem,
        read_raw_metadata,
        read_raw_text,
        title_for_raw,
        write_markdown,
    )

    raw_files = iter_raw_text_files(args.raw_dir)
    if not raw_files:
        logger.info("No raw text files found in %s.", args.raw_dir)
        return 0

    pending: list[Path] = []
    skipped = 0
    for raw_path in raw_files:
        md_path = markdown_path_for_stem(raw_path.stem, args.md_dir)
        if md_path.exists() and not args.overwrite:
            skipped += 1
            logger.info("Skipped existing markdown note: %s", md_path)
        else:
            pending.append(raw_path)

    if not pending:
        logger.info("No raw text files needed markdown generation.")
        return 0

    llm = LLMService()
    written = 0
    failed = 0

    for raw_path in pending:
        content = read_raw_text(raw_path)
        if not content.strip():
            failed += 1
            logger.warning("Skipping empty raw text file: %s", raw_path)
            continue

        metadata = read_raw_metadata(raw_path)
        title = title_for_raw(raw_path, metadata)
        generated_notes = llm.generate_notes(title, content)
        if not generated_notes:
            failed += 1
            logger.error("Failed to generate markdown notes for %s.", raw_path)
            continue

        proofread_notes = llm.proofread_notes(content, generated_notes)
        if not proofread_notes:
            logger.warning("Proofread failed for %s. Using generated notes.", raw_path)
            proofread_notes = generated_notes

        final_output = f"{proofread_notes}\n\n---\n*Tags: #ai-agent #local-notes*"
        result = write_markdown(
            raw_path.stem,
            final_output,
            md_dir=args.md_dir,
            overwrite=args.overwrite,
        )
        if result.skipped:
            skipped += 1
            logger.info("Skipped existing markdown note: %s", result.path)
        else:
            written += 1
            logger.info("Saved markdown note: %s", result.path)

    logger.info(
        "Markdown generation complete: %d written, %d skipped, %d failed.",
        written,
        skipped,
        failed,
    )
    return 1 if failed else 0


def _handle_whatsapp(args: argparse.Namespace) -> int:
    from services.whatsapp_service import WhatsAppService

    whatsapp = WhatsAppService()
    if not whatsapp.enabled:
        logger.error(
            "WhatsApp is not configured. Set CALLMEBOT_API_KEY and CALLMEBOT_PHONE."
        )
        return 1

    if not whatsapp.send_text(args.message):
        logger.error("WhatsApp message failed.")
        return 1

    logger.info("WhatsApp message sent.")
    return 0


def _handle_youtube(args: argparse.Namespace) -> int:
    from services.local_file_service import build_youtube_stem, write_raw_text
    from services.youtube_service import extract_video_id, get_transcript

    video_id = extract_video_id(args.url_or_video_id)
    transcript = get_transcript(args.url_or_video_id, language=args.language)
    result = write_raw_text(
        build_youtube_stem(video_id),
        transcript,
        {
            "source": "youtube",
            "source_id": video_id,
            "subject": f"YouTube transcript: {video_id}",
            "sender": "YouTube",
            "language": args.language,
            "input": args.url_or_video_id,
        },
        raw_dir=args.raw_dir,
        overwrite=args.overwrite,
    )

    if result.skipped:
        logger.info("Skipped existing YouTube transcript: %s", result.path)
    else:
        logger.info("Saved YouTube transcript: %s", result.path)
    return 0


def _handle_telegram(_args: argparse.Namespace) -> int:
    logger.error("Telegram service is not implemented yet.")
    return 1


def _handle_full_workflow(args: argparse.Namespace) -> int:
    from agent import run

    run(limit=args.limit, enable_whatsapp=args.whatsapp)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Study Note Agent command runner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_raw = subparsers.add_parser(
        "fetch-raw",
        help="Fetch Gmail messages and save raw text files locally.",
    )
    fetch_raw.add_argument(
        "--limit",
        type=int,
        default=constants.MAX_EMAILS_PER_RUN,
        help="Maximum number of emails to fetch and save.",
    )
    fetch_raw.add_argument(
        "--raw-dir",
        type=Path,
        default=constants.RAWTEXT_DIR,
        help="Directory where raw text files are saved.",
    )
    fetch_raw.add_argument(
        "--query",
        default="",
        help="Optional Gmail query override. Defaults to configured target emails.",
    )
    fetch_raw.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing raw text and metadata files.",
    )
    fetch_raw.set_defaults(func=_handle_fetch_raw)

    raw_to_md = subparsers.add_parser(
        "raw-to-md",
        help="Convert local raw text files into local markdown notes using the LLM.",
    )
    raw_to_md.add_argument(
        "--raw-dir",
        type=Path,
        default=constants.RAWTEXT_DIR,
        help="Directory containing raw text files.",
    )
    raw_to_md.add_argument(
        "--md-dir",
        type=Path,
        default=constants.MDNOTES_DIR,
        help="Directory where markdown notes are saved.",
    )
    raw_to_md.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing markdown files.",
    )
    raw_to_md.set_defaults(func=_handle_raw_to_md)

    whatsapp = subparsers.add_parser(
        "whatsapp",
        help="Send a WhatsApp message through the configured CallMeBot service.",
    )
    whatsapp.add_argument("--message", required=True, help="Message text to send.")
    whatsapp.set_defaults(func=_handle_whatsapp)

    youtube = subparsers.add_parser(
        "youtube",
        help="Fetch a YouTube transcript and save it as raw text.",
    )
    youtube.add_argument("url_or_video_id", help="YouTube URL or video ID.")
    youtube.add_argument(
        "--language",
        default="en",
        help="Transcript language code to request.",
    )
    youtube.add_argument(
        "--raw-dir",
        type=Path,
        default=constants.RAWTEXT_DIR,
        help="Directory where transcript raw text is saved.",
    )
    youtube.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing transcript file.",
    )
    youtube.set_defaults(func=_handle_youtube)

    telegram = subparsers.add_parser(
        "telegram",
        help="Placeholder for a future Telegram service command.",
    )
    telegram.set_defaults(func=_handle_telegram)

    full_workflow = subparsers.add_parser(
        "full-workflow",
        help="Run Gmail to LLM to OneNote workflow.",
    )
    full_workflow.add_argument(
        "--limit",
        type=int,
        default=constants.MAX_EMAILS_PER_RUN,
        help="Maximum number of emails to process in one run.",
    )
    full_workflow.add_argument(
        "--whatsapp",
        action="store_true",
        default=False,
        help="Enable WhatsApp notifications via CallMeBot.",
    )
    full_workflow.set_defaults(func=_handle_full_workflow)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _prefer_ipv4()
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
