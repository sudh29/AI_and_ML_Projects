"""CLI entry point for the Study Note Agent."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import socket
import time
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


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return parsed


def _handle_fetch_raw(args: argparse.Namespace) -> int:
    from agent import build_gmail_search_query
    from services.gmail_service import GmailService
    from services.local_file_service import (
        build_gmail_stem,
        raw_file_matches_source,
        write_raw_text,
    )
    from services.organize_service import organize_rawtext_files

    query = args.query or build_gmail_search_query()
    logger.info("Fetching unread Gmail messages with query: %s", query)
    gmail = GmailService()
    emails = gmail.fetch_emails(query=query)
    
    if not emails:
        logger.warning("No unread emails found matching the query.")
        return 0
    
    logger.info("Found %d unread email(s) to process.", len(emails))
    
    emails_to_save = emails if args.limit is None else emails[: args.limit]
    if args.limit is not None and len(emails_to_save) < len(emails):
        logger.info("Limiting to %d email(s) due to --limit flag.", args.limit)

    written = 0
    skipped = 0
    unsafe_to_mark = 0
    saved_email_ids: list[str] = []
    
    for index, email in enumerate(emails_to_save, 1):
        email_id = email["id"]
        subject = email["subject"]
        sender = email["sender"]
        
        logger.info(
            "[%d/%d] Processing email: Subject='%s' | From='%s'",
            index,
            len(emails_to_save),
            subject,
            sender,
        )
        
        result = write_raw_text(
            build_gmail_stem(email),
            email["content"],
            {
                "source": "gmail",
                "source_id": email_id,
                "subject": subject,
                "sender": sender,
            },
            raw_dir=args.raw_dir,
            overwrite=args.overwrite,
        )
        if result.skipped:
            skipped += 1
            logger.info("  ✓ Skipped existing raw text: %s", result.path)
        else:
            written += 1
            logger.info("  ✓ Saved raw email text: %s", result.path)

        if result.path.exists() and raw_file_matches_source(result.path, email_id):
            saved_email_ids.append(email_id)
        else:
            unsafe_to_mark += 1
            logger.error(
                "  ✗ Not marking email %s as read because local metadata could not be "
                "verified for %s.",
                email_id,
                result.path,
            )

    marked_read = 0
    mark_read_failed = 0
    if args.mark_read:
        logger.info("Marking %d email(s) as read in Gmail...", len(saved_email_ids))
        for index, email_id in enumerate(saved_email_ids, 1):
            if index > 1 and args.mark_read_delay > 0:
                time.sleep(args.mark_read_delay)

            if gmail.mark_as_read(email_id):
                marked_read += 1
                logger.info("  [%d/%d] ✓ Marked as read: %s", index, len(saved_email_ids), email_id)
            else:
                mark_read_failed += 1
                logger.error("  [%d/%d] ✗ Failed to mark as read: %s", index, len(saved_email_ids), email_id)
    else:
        logger.info("Mark-as-read disabled by --no-mark-read.")

    # Log summary before organization
    logger.info(
        "Raw email capture complete: %d written, %d skipped, %d fetched, "
        "%d marked read, %d mark-read failed, %d unsafe to mark.",
        written,
        skipped,
        len(emails),
        marked_read,
        mark_read_failed,
        unsafe_to_mark,
    )

    # Organize rawtext files by sender
    logger.info("Organizing rawtext files by sender...")
    org_stats = organize_rawtext_files(args.raw_dir)
    logger.info(
        "Rawtext organization complete: %d senders created, %d files moved.",
        org_stats["senders_created"],
        org_stats["files_moved"],
    )

    return 1 if mark_read_failed or unsafe_to_mark else 0


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
    from services.organize_service import organize_mdnotes_files
    from services.conversion_tracker import ConversionTracker

    # Initialize conversion tracker
    tracker = ConversionTracker(constants.CONVERSION_TRACKER_FILE)

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

    if args.limit is not None:
        pending = pending[: args.limit]
        logger.info("Limiting markdown generation to %d raw text file(s).", args.limit)

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
            # Track the conversion
            tracker.mark_converted(raw_path.stem, result.path)

    logger.info(
        "Markdown generation complete: %d written, %d skipped, %d failed.",
        written,
        skipped,
        failed,
    )

    # Organize markdown files by sender
    logger.info("Organizing markdown notes by sender...")
    org_stats = organize_mdnotes_files(args.md_dir, args.raw_dir)
    logger.info(
        "Markdown organization complete: %d senders created, %d files moved.",
        org_stats["senders_created"],
        org_stats["files_moved"],
    )

    # Log conversion statistics
    conv_stats = tracker.get_conversion_stats()
    logger.info(
        "Conversion tracking updated: %d total conversions, last updated: %s",
        conv_stats["total_conversions"],
        conv_stats["last_updated"],
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
        type=_positive_int,
        default=None,
        help="Maximum number of emails to fetch and save. Defaults to all fetched unread emails.",
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
    fetch_raw.add_argument(
        "--no-mark-read",
        action="store_false",
        dest="mark_read",
        help="Save raw text without marking Gmail messages as read.",
    )
    fetch_raw.add_argument(
        "--mark-read-delay",
        type=_non_negative_float,
        default=0.25,
        help="Seconds to wait between Gmail mark-as-read calls.",
    )
    fetch_raw.set_defaults(mark_read=True)
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
    raw_to_md.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Maximum number of raw text files to convert. Defaults to all eligible files.",
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
