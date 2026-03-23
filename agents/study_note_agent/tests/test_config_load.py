from pathlib import Path
from unittest.mock import patch

import constants


def test_load_config_reads_toml(tmp_path: Path) -> None:
    toml_path = tmp_path / "cfg.toml"
    toml_path.write_text(
        'target_emails = ["a@b.com"]\nmax_emails_per_run = 7\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "cfg.json"  # does not exist

    with (
        patch.object(constants, "CONFIG_TOML_PATH", toml_path),
        patch.object(constants, "CONFIG_JSON_PATH", json_path),
    ):
        data = constants._load_config()

    assert data["target_emails"] == ["a@b.com"]
    assert data["max_emails_per_run"] == 7


def test_load_config_json_overrides_toml(tmp_path: Path) -> None:
    toml_path = tmp_path / "cfg.toml"
    toml_path.write_text(
        'target_emails = ["toml@x.com"]\nmax_emails_per_run = 3\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "cfg.json"
    json_path.write_text(
        '{"target_emails": ["json@y.com"],\n// comment\n"max_emails_per_run": 9\n}',
        encoding="utf-8",
    )

    with (
        patch.object(constants, "CONFIG_TOML_PATH", toml_path),
        patch.object(constants, "CONFIG_JSON_PATH", json_path),
    ):
        data = constants._load_config()

    # JSON values override TOML
    assert data["target_emails"] == ["json@y.com"]
    assert data["max_emails_per_run"] == 9


def test_load_config_defaults_when_no_files(tmp_path: Path) -> None:
    toml_path = tmp_path / "missing.toml"
    json_path = tmp_path / "missing.json"

    with (
        patch.object(constants, "CONFIG_TOML_PATH", toml_path),
        patch.object(constants, "CONFIG_JSON_PATH", json_path),
    ):
        data = constants._load_config()

    assert data["target_emails"] == []
    assert data["max_emails_per_run"] == 5
