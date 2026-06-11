import json
from unittest.mock import patch

import main
from services.local_file_service import build_gmail_stem


def test_fetch_raw_with_limit_creates_text_metadata_and_marks_read(tmp_path):
    with patch("services.gmail_service.GmailService") as mock_gmail_cls:
        gmail = mock_gmail_cls.return_value
        gmail.fetch_emails.return_value = [
            {
                "id": "id1",
                "subject": "Subject One",
                "sender": "sender@example.com",
                "content": "body one",
            },
            {
                "id": "id2",
                "subject": "Subject Two",
                "sender": "sender@example.com",
                "content": "body two",
            },
        ]

        code = main.main(["fetch-raw", "--limit", "1", "--raw-dir", str(tmp_path)])

    assert code == 0
    raw_files = list(tmp_path.glob("*.txt"))
    assert len(raw_files) == 1
    assert raw_files[0].read_text(encoding="utf-8") == "body one\n"

    metadata = json.loads(raw_files[0].with_suffix(".json").read_text())
    assert metadata == {
        "sender": "sender@example.com",
        "source": "gmail",
        "source_id": "id1",
        "subject": "Subject One",
    }
    gmail.mark_as_read.assert_called_once_with("id1")


def test_fetch_raw_without_limit_saves_and_marks_all_fetched_emails(tmp_path):
    with patch("services.gmail_service.GmailService") as mock_gmail_cls:
        gmail = mock_gmail_cls.return_value
        gmail.mark_as_read.return_value = True
        gmail.fetch_emails.return_value = [
            {
                "id": "id1",
                "subject": "Subject One",
                "sender": "sender@example.com",
                "content": "body one",
            },
            {
                "id": "id2",
                "subject": "Subject Two",
                "sender": "sender@example.com",
                "content": "body two",
            },
        ]

        code = main.main(
            ["fetch-raw", "--raw-dir", str(tmp_path), "--mark-read-delay", "0"]
        )

    assert code == 0
    assert sorted(path.name for path in tmp_path.glob("*.txt")) == [
        "gmail_id1_Subject-One.txt",
        "gmail_id2_Subject-Two.txt",
    ]
    assert [call.args[0] for call in gmail.mark_as_read.call_args_list] == [
        "id1",
        "id2",
    ]


def test_fetch_raw_does_not_mark_when_existing_metadata_mismatches(tmp_path):
    email = {
        "id": "id1",
        "subject": "Subject One",
        "sender": "sender@example.com",
        "content": "body one",
    }
    existing_raw = tmp_path / f"{build_gmail_stem(email)}.txt"
    existing_raw.write_text("old body", encoding="utf-8")
    existing_raw.with_suffix(".json").write_text(
        json.dumps({"source": "gmail", "source_id": "other-id"}),
        encoding="utf-8",
    )

    with patch("services.gmail_service.GmailService") as mock_gmail_cls:
        gmail = mock_gmail_cls.return_value
        gmail.fetch_emails.return_value = [email]

        code = main.main(["fetch-raw", "--raw-dir", str(tmp_path)])

    assert code == 1
    assert existing_raw.read_text(encoding="utf-8") == "old body"
    gmail.mark_as_read.assert_not_called()


def test_raw_to_md_uses_sidecar_title(tmp_path):
    raw_dir = tmp_path / "rawtext"
    md_dir = tmp_path / "mdnotes"
    raw_dir.mkdir()
    raw_path = raw_dir / "gmail_id1_subject.txt"
    raw_path.write_text("raw body", encoding="utf-8")
    raw_path.with_suffix(".json").write_text(
        json.dumps({"subject": "Sidecar Subject"}),
        encoding="utf-8",
    )

    with patch("services.llm_service.LLMService") as mock_llm_cls:
        llm = mock_llm_cls.return_value
        llm.generate_notes.return_value = "generated"
        llm.proofread_notes.return_value = "proofread"

        code = main.main(
            ["raw-to-md", "--raw-dir", str(raw_dir), "--md-dir", str(md_dir)]
        )

    assert code == 0
    assert (md_dir / "gmail_id1_subject.md").read_text(encoding="utf-8") == (
        "proofread\n\n---\n*Tags: #ai-agent #local-notes*\n"
    )
    llm.generate_notes.assert_called_once_with("Sidecar Subject", "raw body")
    llm.proofread_notes.assert_called_once_with("raw body", "generated")


def test_raw_to_md_falls_back_to_filename_title(tmp_path):
    raw_dir = tmp_path / "rawtext"
    md_dir = tmp_path / "mdnotes"
    raw_dir.mkdir()
    raw_path = raw_dir / "plain_topic.txt"
    raw_path.write_text("raw body", encoding="utf-8")

    with patch("services.llm_service.LLMService") as mock_llm_cls:
        llm = mock_llm_cls.return_value
        llm.generate_notes.return_value = "generated"
        llm.proofread_notes.return_value = None

        code = main.main(
            ["raw-to-md", "--raw-dir", str(raw_dir), "--md-dir", str(md_dir)]
        )

    assert code == 0
    assert "generated" in (md_dir / "plain_topic.md").read_text(encoding="utf-8")
    llm.generate_notes.assert_called_once_with("plain_topic", "raw body")


def test_raw_to_md_skips_existing_unless_overwrite(tmp_path):
    raw_dir = tmp_path / "rawtext"
    md_dir = tmp_path / "mdnotes"
    raw_dir.mkdir()
    md_dir.mkdir()
    (raw_dir / "topic.txt").write_text("raw body", encoding="utf-8")
    md_path = md_dir / "topic.md"
    md_path.write_text("existing", encoding="utf-8")

    with patch("services.llm_service.LLMService") as mock_llm_cls:
        code = main.main(
            ["raw-to-md", "--raw-dir", str(raw_dir), "--md-dir", str(md_dir)]
        )

    assert code == 0
    assert md_path.read_text(encoding="utf-8") == "existing"
    mock_llm_cls.assert_not_called()

    with patch("services.llm_service.LLMService") as mock_llm_cls:
        llm = mock_llm_cls.return_value
        llm.generate_notes.return_value = "new notes"
        llm.proofread_notes.return_value = None

        code = main.main(
            [
                "raw-to-md",
                "--raw-dir",
                str(raw_dir),
                "--md-dir",
                str(md_dir),
                "--overwrite",
            ]
        )

    assert code == 0
    assert "new notes" in md_path.read_text(encoding="utf-8")


def test_raw_to_md_limit_processes_only_requested_number(tmp_path):
    raw_dir = tmp_path / "rawtext"
    md_dir = tmp_path / "mdnotes"
    raw_dir.mkdir()
    for name in ("one", "two", "three"):
        (raw_dir / f"{name}.txt").write_text(f"{name} body", encoding="utf-8")

    with patch("services.llm_service.LLMService") as mock_llm_cls:
        llm = mock_llm_cls.return_value
        llm.generate_notes.side_effect = ["one notes", "two notes"]
        llm.proofread_notes.side_effect = [None, None]

        code = main.main(
            [
                "raw-to-md",
                "--raw-dir",
                str(raw_dir),
                "--md-dir",
                str(md_dir),
                "--limit",
                "2",
            ]
        )

    assert code == 0
    assert sorted(path.name for path in md_dir.glob("*.md")) == ["one.md", "three.md"]
    assert llm.generate_notes.call_count == 2


def test_youtube_command_saves_transcript_to_rawtext(tmp_path):
    url = "https://www.youtube.com/watch?v=abc123"
    with patch("services.youtube_service.get_transcript") as mock_get_transcript:
        mock_get_transcript.return_value = "transcript text"

        code = main.main(["youtube", url, "--raw-dir", str(tmp_path)])

    assert code == 0
    raw_path = tmp_path / "youtube_abc123.txt"
    assert raw_path.read_text(encoding="utf-8") == "transcript text\n"
    metadata = json.loads(raw_path.with_suffix(".json").read_text())
    assert metadata["source"] == "youtube"
    assert metadata["source_id"] == "abc123"
    mock_get_transcript.assert_called_once_with(url, language="en")


def test_whatsapp_command_fails_when_disabled():
    with patch("services.whatsapp_service.WhatsAppService") as mock_whatsapp_cls:
        whatsapp = mock_whatsapp_cls.return_value
        whatsapp.enabled = False

        code = main.main(["whatsapp", "--message", "hello"])

    assert code == 1
    whatsapp.send_text.assert_not_called()


def test_whatsapp_command_sends_message():
    with patch("services.whatsapp_service.WhatsAppService") as mock_whatsapp_cls:
        whatsapp = mock_whatsapp_cls.return_value
        whatsapp.enabled = True
        whatsapp.send_text.return_value = True

        code = main.main(["whatsapp", "--message", "hello"])

    assert code == 0
    whatsapp.send_text.assert_called_once_with("hello")


def test_telegram_command_is_placeholder():
    assert main.main(["telegram"]) == 1


def test_full_workflow_dispatches_to_agent_run():
    with patch("agent.run") as mock_run:
        code = main.main(["full-workflow", "--limit", "3", "--whatsapp"])

    assert code == 0
    mock_run.assert_called_once_with(limit=3, enable_whatsapp=True)
