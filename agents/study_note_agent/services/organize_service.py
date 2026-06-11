"""Service for organizing raw text and markdown files by sender."""

import json
import logging
import shutil
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_sender_name(sender_email: str) -> str:
    """Extract sender's name from email string.
    
    Examples:
        'Neo Kim <systemdesignone@substack.com>' -> 'Neo Kim'
        'Sandeep Swadia <newsletter@example.com>' -> 'Sandeep Swadia'
        'unknown@example.com' -> 'unknown@example.com'
    """
    if '<' in sender_email:
        return sender_email.split('<')[0].strip()
    return sender_email.strip()


def organize_rawtext_files(raw_dir: Path) -> dict[str, int]:
    """Organize raw text files into sender-based subdirectories.
    
    Args:
        raw_dir: Path to the rawtext directory
        
    Returns:
        Dictionary with statistics: {'senders_created': int, 'files_moved': int}
    """
    if not raw_dir.exists():
        logger.warning("Raw text directory does not exist: %s", raw_dir)
        return {"senders_created": 0, "files_moved": 0}

    # Dictionary to store sender -> files mapping
    sender_files = defaultdict(list)
    stats = {"senders_created": 0, "files_moved": 0}

    # First pass: skip already organized files and collect new ones
    for json_file in raw_dir.glob("*.json"):
        # Skip if this file is already inside a sender subdirectory
        if json_file.parent != raw_dir:
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                sender = data.get("sender", "Unknown")
                sender_name = extract_sender_name(sender)

                base_name = json_file.stem
                txt_file = raw_dir / f"{base_name}.txt"

                sender_files[sender_name].append({
                    "json": json_file,
                    "txt": txt_file if txt_file.exists() else None,
                })
        except Exception as e:
            logger.error("Error reading %s: %s", json_file, e)
            continue

    # Second pass: create directories and move files
    for sender_name, files in sender_files.items():
        sender_dir = raw_dir / sender_name
        sender_dir.mkdir(exist_ok=True)

        if not (raw_dir / sender_name).exists():
            stats["senders_created"] += 1
        else:
            # Only log if we're creating a new directory
            if (sender_dir.parent / f"{sender_name}.json").exists():
                stats["senders_created"] += 1

        for file_pair in files:
            json_file = file_pair["json"]
            txt_file = file_pair["txt"]

            try:
                # Move JSON file
                new_json_path = sender_dir / json_file.name
                if not new_json_path.exists():
                    shutil.move(str(json_file), str(new_json_path))
                    stats["files_moved"] += 1
                    logger.info("Moved: %s -> %s/", json_file.name, sender_name)

                # Move TXT file if it exists
                if txt_file and txt_file.exists():
                    new_txt_path = sender_dir / txt_file.name
                    if not new_txt_path.exists():
                        shutil.move(str(txt_file), str(new_txt_path))
                        stats["files_moved"] += 1
            except Exception as e:
                logger.error("Error moving %s: %s", json_file.name, e)

    return stats


def organize_mdnotes_files(md_dir: Path, raw_dir: Path) -> dict[str, int]:
    """Organize markdown files into sender-based subdirectories.
    
    Matches each markdown file with its corresponding JSON file in rawtext
    to determine the sender.
    
    Args:
        md_dir: Path to the mdnotes directory
        raw_dir: Path to the rawtext directory (for sender lookup)
        
    Returns:
        Dictionary with statistics: {'senders_created': int, 'files_moved': int}
    """
    if not md_dir.exists():
        logger.warning("Markdown notes directory does not exist: %s", md_dir)
        return {"senders_created": 0, "files_moved": 0}

    stats = {"senders_created": 0, "files_moved": 0}
    sender_dirs_created = set()

    # Process all .md files in root of md_dir (skip already organized ones)
    for md_file in md_dir.glob("*.md"):
        base_name = md_file.stem

        # Find corresponding JSON file in rawtext to get sender
        json_file = None
        
        # Check in raw_dir subdirectories first (organized structure)
        for json_candidate in raw_dir.glob(f"**/{base_name}.json"):
            json_file = json_candidate
            break
        
        # If not found in subdirectories, check root (unorganized)
        if not json_file:
            json_candidate = raw_dir / f"{base_name}.json"
            if json_candidate.exists():
                json_file = json_candidate

        if json_file:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sender = data.get("sender", "Unknown")
                    sender_name = extract_sender_name(sender)

                    # Create sender directory
                    sender_dir = md_dir / sender_name
                    if sender_dir.mkdir(exist_ok=True) is None:
                        if sender_name not in sender_dirs_created:
                            stats["senders_created"] += 1
                            sender_dirs_created.add(sender_name)
                            logger.info("Created sender directory: %s", sender_name)

                    # Move the markdown file
                    new_path = sender_dir / md_file.name
                    if not new_path.exists():
                        shutil.move(str(md_file), str(new_path))
                        stats["files_moved"] += 1
                        logger.info("Moved: %s -> %s/", md_file.name, sender_name)
            except Exception as e:
                logger.error("Error processing %s: %s", md_file.name, e)
        else:
            logger.warning("Could not find JSON metadata for: %s", md_file.name)

    return stats
