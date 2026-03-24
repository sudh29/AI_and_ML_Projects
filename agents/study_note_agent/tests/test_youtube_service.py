"""Tests for services.youtube.YouTubeService."""

from unittest.mock import MagicMock, patch

import pytest

from services.youtube import YouTubeService


# ------------------------------------------------------------------
# Video ID extraction
# ------------------------------------------------------------------
class TestExtractVideoId:
    @pytest.mark.parametrize(
        "url, expected_id",
        [
            ("https://www.youtube.com/watch?v=abc123", "abc123"),
            ("https://www.youtube.com/watch?v=abc123&list=PL", "abc123"),
            ("https://youtu.be/xyz789", "xyz789"),
            ("https://youtu.be/xyz789?t=42", "xyz789"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),  # bare ID
        ],
    )
    def test_extract_video_id(self, url, expected_id):
        assert YouTubeService._extract_video_id(url) == expected_id


# ------------------------------------------------------------------
# get_transcript
# ------------------------------------------------------------------
class TestGetTranscript:
    @patch("services.youtube.YouTubeTranscriptApi")
    @patch("services.youtube.TextFormatter")
    def test_returns_formatted_text(self, mock_formatter_cls, mock_api):
        mock_api.get_transcript.return_value = [{"text": "hello"}]
        mock_formatter = mock_formatter_cls.return_value
        mock_formatter.format_transcript.return_value = "hello"

        svc = YouTubeService()
        result = svc.get_transcript("https://www.youtube.com/watch?v=abc123")

        mock_api.get_transcript.assert_called_once_with("abc123", languages=["en"])
        assert result == "hello"


# ------------------------------------------------------------------
# process_video
# ------------------------------------------------------------------
class TestProcessVideo:
    def _make_services(self, *, notes_ok=True, gen_notes="# Notes", proofread="# OK"):
        llm = MagicMock()
        llm.generate_notes.return_value = gen_notes
        llm.proofread_notes.return_value = proofread
        notes = MagicMock()
        notes.save_note.return_value = notes_ok
        return llm, notes

    @patch.object(YouTubeService, "get_transcript", return_value="transcript text")
    def test_full_pipeline_success(self, _mock_transcript):
        llm, notes = self._make_services()
        svc = YouTubeService()

        result = svc.process_video("https://www.youtube.com/watch?v=vid1", llm, notes)

        assert result is True
        llm.generate_notes.assert_called_once()
        llm.proofread_notes.assert_called_once()
        notes.save_note.assert_called_once()

    @patch.object(
        YouTubeService,
        "get_transcript",
        side_effect=Exception("Transcripts disabled"),
    )
    def test_transcript_failure_returns_false(self, _mock_transcript):
        llm, notes = self._make_services()
        svc = YouTubeService()

        result = svc.process_video("https://www.youtube.com/watch?v=vid1", llm, notes)

        assert result is False
        llm.generate_notes.assert_not_called()

    @patch.object(YouTubeService, "get_transcript", return_value="transcript text")
    def test_note_save_failure_returns_false(self, _mock_transcript):
        llm, notes = self._make_services(notes_ok=False)
        svc = YouTubeService()

        result = svc.process_video("https://www.youtube.com/watch?v=vid1", llm, notes)

        assert result is False

    @patch.object(YouTubeService, "get_transcript", return_value="transcript text")
    def test_whatsapp_called_on_success(self, _mock_transcript):
        llm, notes = self._make_services()
        whatsapp = MagicMock()
        whatsapp.notify_note_saved.return_value = True
        svc = YouTubeService()

        result = svc.process_video(
            "https://www.youtube.com/watch?v=vid1", llm, notes, whatsapp=whatsapp
        )

        assert result is True
        whatsapp.notify_note_saved.assert_called_once()
