"""Tests for the CLI module."""

import pytest
from emoji_bulk_migrator.cli import (
    create_parser,
    parse_args,
    setup_logging,
    get_source_config,
    get_dest_config,
    validate_config,
)
from emoji_bulk_migrator.models import SlackConfig


class TestCreateParser:
    """Tests for parser creation."""

    def test_parser_created(self):
        """Test that parser is created without errors."""
        parser = create_parser()
        assert parser is not None

    def test_help_works(self):
        """Test that help flag works."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0


class TestParseArgs:
    """Tests for argument parsing."""

    def test_download_command(self):
        """Test parsing download command."""
        args = parse_args([
            "download",
            "--source-workspace", "myworkspace",
            "--source-token", "xoxp-123"
        ])
        
        assert args.command == "download"
        assert args.source_workspace == "myworkspace"
        assert args.source_token == "xoxp-123"

    def test_upload_command(self):
        """Test parsing upload command."""
        args = parse_args([
            "upload",
            "--dest-workspace", "destworkspace",
            "--dest-token", "xoxp-456"
        ])
        
        assert args.command == "upload"
        assert args.dest_workspace == "destworkspace"
        assert args.dest_token == "xoxp-456"

    def test_sync_command(self):
        """Test parsing sync command."""
        args = parse_args([
            "sync",
            "--source-workspace", "source",
            "--source-token", "xoxp-src",
            "--dest-workspace", "dest",
            "--dest-token", "xoxp-dst"
        ])
        
        assert args.command == "sync"
        assert args.source_workspace == "source"
        assert args.dest_workspace == "dest"

    def test_list_command(self):
        """Test parsing list command."""
        args = parse_args(["list"])
        
        assert args.command == "list"

    def test_global_options(self):
        """Test global options."""
        args = parse_args([
            "--verbose",
            "--storage-path", "/custom/path",
            "--api-mode", "http",
            "list"
        ])
        
        assert args.verbose is True
        assert args.storage_path == "/custom/path"
        assert args.api_mode == "http"

    def test_default_values(self):
        """Test default values."""
        args = parse_args(["list"])
        
        assert args.verbose is False
        assert args.quiet is False
        assert args.storage_path == "./emojis"
        assert args.api_mode == "web_api"

    def test_no_command(self):
        """Test parsing with no command."""
        args = parse_args([])
        
        assert args.command is None


class TestGetSourceConfig:
    """Tests for get_source_config."""

    def test_from_args(self):
        """Test config from command line args."""
        args = parse_args([
            "download",
            "--source-workspace", "myworkspace",
            "--source-token", "xoxp-123",
            "--source-cookie", "d=abc"
        ])
        
        config = get_source_config(args)
        
        assert config.workspace == "myworkspace"
        assert config.token == "xoxp-123"
        assert config.cookie == "d=abc"

    def test_from_env(self, monkeypatch):
        """Test config from environment."""
        monkeypatch.setenv("SOURCE_SLACK_WORKSPACE", "envworkspace")
        monkeypatch.setenv("SOURCE_SLACK_TOKEN", "env-token")
        
        args = parse_args(["download"])
        config = get_source_config(args)
        
        assert config.workspace == "envworkspace"
        assert config.token == "env-token"

    def test_args_override_env(self, monkeypatch):
        """Test that args override environment."""
        monkeypatch.setenv("SOURCE_SLACK_WORKSPACE", "envworkspace")
        monkeypatch.setenv("SOURCE_SLACK_TOKEN", "env-token")
        
        args = parse_args([
            "download",
            "--source-workspace", "argworkspace",
            "--source-token", "arg-token"
        ])
        config = get_source_config(args)
        
        assert config.workspace == "argworkspace"
        assert config.token == "arg-token"


class TestGetDestConfig:
    """Tests for get_dest_config."""

    def test_from_args(self):
        """Test config from command line args."""
        args = parse_args([
            "upload",
            "--dest-workspace", "destworkspace",
            "--dest-token", "xoxp-456"
        ])
        
        config = get_dest_config(args)
        
        assert config.workspace == "destworkspace"
        assert config.token == "xoxp-456"


class TestValidateConfig:
    """Tests for validate_config."""

    def test_valid_config(self, caplog):
        """Test validation of valid config."""
        config = SlackConfig(workspace="test", token="xoxp-123")
        
        result = validate_config(config, "Source")
        
        assert result is True

    def test_missing_workspace(self, caplog):
        """Test validation fails with missing workspace."""
        config = SlackConfig(workspace="", token="xoxp-123")
        
        result = validate_config(config, "Source")
        
        assert result is False

    def test_missing_token(self, caplog):
        """Test validation fails with missing token."""
        config = SlackConfig(workspace="test", token="")
        
        result = validate_config(config, "Source")
        
        assert result is False

    def test_missing_both(self, caplog):
        """Test validation fails with both missing."""
        config = SlackConfig(workspace="", token="")
        
        result = validate_config(config, "Source")
        
        assert result is False
