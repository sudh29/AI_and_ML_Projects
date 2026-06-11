"""Local raw-text and markdown file helpers for CLI workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Mapping

import constants


@dataclass(frozen=True)
class WriteResult:
    path: Path
    skipped: bool
    metadata_path: Path | None = None


_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(value: str | None, *, fallback: str = "untitled", max_length: int = 80) -> str:
    """Convert arbitrary text to a stable, filesystem-friendly slug."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("-", (value or "").strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-._")
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_length].rstrip("-._") or fallback


def build_gmail_stem(email: Mapping[str, Any]) -> str:
    email_id = slugify(str(email.get("id", "")), fallback="unknown-id", max_length=48)
    subject = slugify(
        str(email.get("subject", "")), fallback="no-subject", max_length=80
    )
    return f"gmail_{email_id}_{subject}"


def build_youtube_stem(video_id: str) -> str:
    return f"youtube_{slugify(video_id, fallback='unknown-video', max_length=48)}"


def metadata_path_for_raw(raw_path: Path) -> Path:
    return raw_path.with_suffix(".json")


def markdown_path_for_stem(
    stem: str, md_dir: str | Path | None = None
) -> Path:
    target_dir = Path(md_dir) if md_dir is not None else constants.MDNOTES_DIR
    return target_dir / f"{stem}.md"


def iter_raw_text_files(raw_dir: str | Path | None = None) -> list[Path]:
    source_dir = Path(raw_dir) if raw_dir is not None else constants.RAWTEXT_DIR
    if not source_dir.exists():
        return []
    # Search recursively in all subdirectories (organized by sender)
    return sorted(source_dir.glob("**/*.txt"))


def read_raw_text(raw_path: str | Path) -> str:
    return Path(raw_path).read_text(encoding="utf-8")


def read_raw_metadata(raw_path: str | Path) -> dict[str, Any]:
    metadata_path = metadata_path_for_raw(Path(raw_path))
    if not metadata_path.exists():
        return {}
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def raw_file_matches_source(raw_path: str | Path, source_id: str) -> bool:
    metadata = read_raw_metadata(raw_path)
    return metadata.get("source_id") == source_id


def title_for_raw(raw_path: str | Path, metadata: Mapping[str, Any] | None = None) -> str:
    metadata = metadata or read_raw_metadata(raw_path)
    title = metadata.get("subject") or metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return Path(raw_path).stem


def write_raw_text(
    stem: str,
    content: str,
    metadata: Mapping[str, Any],
    *,
    raw_dir: str | Path | None = None,
    overwrite: bool = False,
) -> WriteResult:
    target_dir = Path(raw_dir) if raw_dir is not None else constants.RAWTEXT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_path = target_dir / f"{stem}.txt"
    metadata_path = metadata_path_for_raw(raw_path)
    if raw_path.exists() and not overwrite:
        return WriteResult(raw_path, skipped=True, metadata_path=metadata_path)

    raw_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(dict(metadata), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return WriteResult(raw_path, skipped=False, metadata_path=metadata_path)


def is_markdown_already_created(raw_path: str | Path) -> bool:
    """Check if markdown has already been created for this raw file.
    
    Checks the metadata JSON file to see if markdown_created flag is set.
    """
    metadata = read_raw_metadata(raw_path)
    return metadata.get("markdown_created", False) is True


def has_markdown_conversion_failed(raw_path: str | Path) -> bool:
    """Check if markdown conversion has been attempted and failed for this raw file.
    
    Checks the metadata JSON file to see if conversion_failed flag is set.
    """
    metadata = read_raw_metadata(raw_path)
    return metadata.get("conversion_failed", False) is True


def mark_conversion_failed(raw_path: str | Path, error_message: str = "") -> None:
    """Mark the raw file as having a failed conversion attempt.
    
    Adds conversion_failed flag and error info to the metadata to prevent retries.
    """
    raw_path = Path(raw_path)
    metadata_path = metadata_path_for_raw(raw_path)
    
    if not metadata_path.exists():
        return
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    
    # Update metadata with conversion failure info
    metadata["conversion_failed"] = True
    metadata["conversion_failed_timestamp"] = datetime.now().isoformat()
    if error_message:
        metadata["conversion_error"] = error_message[:200]  # Limit error message length
    
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
            f.write("\n")
    except OSError:
        pass


def update_metadata_with_markdown(
    raw_path: str | Path, md_path: str | Path
) -> None:
    """Update the raw file's JSON metadata to record that markdown was created.
    
    Adds markdown_created flag and markdown_path to the metadata.
    """
    raw_path = Path(raw_path)
    metadata_path = metadata_path_for_raw(raw_path)
    
    if not metadata_path.exists():
        return
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    
    # Update metadata with markdown creation info
    metadata["markdown_created"] = True
    metadata["markdown_path"] = str(Path(md_path).relative_to(Path(md_path).parent.parent))
    
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
            f.write("\n")
    except OSError:
        pass


def write_markdown(
    stem: str,
    content: str,
    *,
    md_dir: str | Path | None = None,
    overwrite: bool = False,
) -> WriteResult:
    target_path = markdown_path_for_stem(stem, md_dir)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and not overwrite:
        return WriteResult(target_path, skipped=True)

    target_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return WriteResult(target_path, skipped=False)
