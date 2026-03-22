from pathlib import Path

import constants


def test_load_config_strips_comments_and_trailing_comma(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"target_emails": ["a@b.com"],\n// comment\n"max_emails_per_run": 7,\n}',
        encoding="utf-8",
    )
    data = constants._load_config(path)
    assert data["target_emails"] == ["a@b.com"]
    assert data["max_emails_per_run"] == 7
