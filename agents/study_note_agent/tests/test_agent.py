"""Tests for agent.py workflow coordination."""

import pytest
from unittest.mock import MagicMock, patch
from agent import CircuitBreaker, run
import constants

class TestCircuitBreaker:
    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.is_open is False
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        cb.record_failure()
        assert cb.is_open is False

class TestAgentRun:
    @patch("agent.GmailService")
    @patch("agent.LLMService")
    @patch("agent.NotesService")
    @patch("agent.load_processed_emails")
    @patch("agent.save_processed_emails")
    def test_run_skips_processed_emails(self, mock_save, mock_load, mock_notes, mock_llm, mock_gmail):
        mock_load.return_value = {"id1"}
        mock_gmail_inst = mock_gmail.return_value
        mock_gmail_inst.fetch_emails.return_value = [
            {"id": "id1", "subject": "Old", "content": "..."}
        ]
        
        run(limit=5)
        
        # Should not call LLM if no new emails
        mock_llm.return_value.generate_notes.assert_not_called()

    @patch("agent.GmailService")
    @patch("agent.LLMService")
    @patch("agent.NotesService")
    @patch("agent.load_processed_emails")
    @patch("agent.save_processed_emails")
    @patch("agent.concurrent.futures.ThreadPoolExecutor")
    def test_run_processes_new_emails(self, mock_executor, mock_save, mock_load, mock_notes, mock_llm, mock_gmail):
        mock_load.return_value = set()
        mock_gmail_inst = mock_gmail.return_value
        mock_gmail_inst.fetch_emails.return_value = [
            {"id": "id2", "subject": "New", "content": "..."}
        ]
        
        # Mock executor to just call result in as_completed
        mock_future = MagicMock()
        mock_future.result.return_value = "id2"
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        with patch("agent.concurrent.futures.as_completed", return_value=[mock_future]):
            run(limit=5)
            
        mock_gmail_inst.mark_as_read.assert_called_with("id2")
        mock_save.assert_called()
