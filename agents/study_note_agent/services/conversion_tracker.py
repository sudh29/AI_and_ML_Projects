"""Service for tracking which raw text files have been converted to markdown."""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversionTracker:
    """Tracks which raw text files have been converted to markdown notes."""

    def __init__(self, tracker_file: Path):
        """Initialize the conversion tracker.
        
        Args:
            tracker_file: Path to the JSON file where conversions are tracked
        """
        self.tracker_file = Path(tracker_file)
        self._data = self._load_tracker()

    def _load_tracker(self) -> dict:
        """Load tracking data from file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load conversion tracker: %s. Starting fresh.", e)
        return {"conversions": [], "last_updated": None}

    def _save_tracker(self) -> None:
        """Save tracking data to file."""
        try:
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save conversion tracker: %s", e)

    def mark_converted(self, raw_stem: str, md_path: Path) -> None:
        """Mark a raw file as converted to markdown.
        
        Args:
            raw_stem: The stem of the raw file (without extension)
            md_path: The path to the generated markdown file
        """
        conversion_record = {
            "raw_stem": raw_stem,
            "md_path": str(md_path.relative_to(md_path.parent.parent)),
            "timestamp": datetime.now().isoformat(),
        }

        # Check if already tracked
        for conv in self._data["conversions"]:
            if conv["raw_stem"] == raw_stem:
                logger.debug("Conversion already tracked: %s", raw_stem)
                return

        self._data["conversions"].append(conversion_record)
        self._data["last_updated"] = datetime.now().isoformat()
        self._save_tracker()
        logger.info("Tracked conversion: %s -> %s", raw_stem, md_path.name)

    def get_conversions(self) -> list[dict]:
        """Get all tracked conversions.
        
        Returns:
            List of conversion records
        """
        return self._data.get("conversions", [])

    def get_conversion_count(self) -> int:
        """Get total number of tracked conversions."""
        return len(self._data.get("conversions", []))

    def is_converted(self, raw_stem: str) -> bool:
        """Check if a raw file has been converted.
        
        Args:
            raw_stem: The stem of the raw file
            
        Returns:
            True if the file has been converted, False otherwise
        """
        for conv in self._data.get("conversions", []):
            if conv["raw_stem"] == raw_stem:
                return True
        return False

    def get_conversion_stats(self) -> dict:
        """Get statistics about conversions.
        
        Returns:
            Dictionary with conversion stats
        """
        conversions = self.get_conversions()
        return {
            "total_conversions": len(conversions),
            "last_conversion": conversions[-1]["timestamp"] if conversions else None,
            "last_updated": self._data.get("last_updated"),
        }
