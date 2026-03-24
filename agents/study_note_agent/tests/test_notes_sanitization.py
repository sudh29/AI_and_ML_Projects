"""Tests for services.notes_service sanitization."""

import pytest
from unittest.mock import MagicMock, patch
from services.notes_service import NotesService

class TestNotesSanitization:
    @patch("services.notes_service.constants.MS_CLIENT_ID", "fake_client_id")
    @patch("services.notes_service.PublicClientApplication")
    @patch("services.notes_service.SerializableTokenCache")
    def test_save_note_sanitizes_html(self, mock_cache, mock_app):
        # Mock MSAL and requests
        svc = NotesService(token_path="/tmp/fake_token.json")
        svc._get_access_token = MagicMock(return_value="fake_token")
        
        with patch("services.notes_service.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {}
            
            malicious_md = "# Title\n\n<script>alert('xss')</script>\n\n[Link](javascript:alert(1))"
            svc.save_note("Test", malicious_md)
            
            # Check the data sent to Microsoft
            args, kwargs = mock_post.call_args
            sent_html = kwargs["data"].decode("utf-8")
            
            # script should be stripped or escaped
            assert "<script>" not in sent_html
            # javascript link should be stripped or neutralized by bleach
            assert "javascript:alert(1)" not in sent_html
            assert "<h1>Title</h1>" in sent_html
