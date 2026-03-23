"""Tests for CallMeBot WhatsApp helper and WhatsAppService."""

from unittest.mock import MagicMock, patch

import pytest

from services import whatsapp_service as ws


def test_effective_api_key_prefers_env() -> None:
    assert ws._effective_api_key("secret", "fallback") == "secret"


def test_effective_api_key_skips_placeholder_uses_fallback() -> None:
    assert ws._effective_api_key("your_api_key_from_the_bot", "real") == "real"


def test_effective_api_key_all_placeholders() -> None:
    assert ws._effective_api_key("your_api_key_here", "changeme") == ""


def test_effective_phone_prefers_env() -> None:
    assert ws._effective_phone("+15551234567", "+34999") == "+15551234567"


def test_callmebot_failure_detection() -> None:
    assert ws._callmebot_response_indicates_failure("ERROR: invalid phone")
    assert ws._callmebot_response_indicates_failure("wrong api key")
    assert not ws._callmebot_response_indicates_failure("Message queued")
    assert not ws._callmebot_response_indicates_failure("")


@patch("services.whatsapp_service.requests.get")
def test_send_text_calls_api_when_enabled(
    mock_get: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CALLMEBOT_API_KEY", "testkey")
    monkeypatch.setenv("CALLMEBOT_PHONE", "+1555000111222")
    mock_resp = MagicMock()
    mock_resp.text = "Message queued"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    svc = ws.WhatsAppService()
    assert svc.enabled
    assert svc.send_text("hello world") is True
    mock_get.assert_called_once()
    call_kw = mock_get.call_args
    assert "api.callmebot.com" in call_kw[0][0] or "whatsapp" in call_kw[0][0]


def test_send_text_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALLMEBOT_API_KEY", raising=False)
    monkeypatch.delenv("CALLMEBOT_PHONE", raising=False)
    with (
        patch.object(ws.constants, "CALLMEBOT_API_KEY_FALLBACK", ""),
        patch.object(ws.constants, "CALLMEBOT_PHONE_FALLBACK", ""),
    ):
        svc = ws.WhatsAppService()
        assert not svc.enabled
        with patch("services.whatsapp_service.requests.get") as mock_get:
            assert svc.send_text("x") is True
            mock_get.assert_not_called()
