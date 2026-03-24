"""Tests for services.youtube_service."""

from unittest.mock import patch

from services.youtube_service import get_transcript


class TestGetTranscript:
    @patch("services.youtube_service.YouTubeTranscriptApi")
    @patch("services.youtube_service.TextFormatter")
    def test_get_transcript_extracts_id_correctly(self, mock_formatter_cls, mock_api):
        mock_api.get_transcript.return_value = [{"text": "hello"}]
        mock_formatter = mock_formatter_cls.return_value
        mock_formatter.format_transcript.return_value = "hello"

        # standard url
        assert get_transcript("https://www.youtube.com/watch?v=abc123") == "hello"
        mock_api.get_transcript.assert_called_with("abc123", languages=["en"])

        # short url
        assert get_transcript("https://youtu.be/xyz789") == "hello"
        mock_api.get_transcript.assert_called_with("xyz789", languages=["en"])

        # standard url with extra params
        assert (
            get_transcript("https://www.youtube.com/watch?t=10&v=def456&list=PLx")
            == "hello"
        )
        mock_api.get_transcript.assert_called_with("def456", languages=["en"])

        # bare id
        assert get_transcript("dQw4w9WgXcQ") == "hello"
        mock_api.get_transcript.assert_called_with("dQw4w9WgXcQ", languages=["en"])
