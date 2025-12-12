"""Tests for the Click CLI module."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock

from emoji_bulk_migrator.cli import cli, validate_config, create_api_handler
from emoji_bulk_migrator.models import SlackConfig


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestCliBasics:
    """Basic CLI tests."""

    def test_help(self, runner):
        """Test that --help works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Sync custom emojis" in result.output

    def test_version(self, runner):
        """Test that --version works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.3.0" in result.output

    def test_no_command_shows_help(self, runner):
        """Test invoking with no command shows help."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestDownloadCommand:
    """Tests for the download command."""

    def test_download_help(self, runner):
        """Test download --help."""
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download emojis" in result.output
        assert "--source-workspace" in result.output
        assert "--source-token" in result.output

    def test_download_missing_workspace(self, runner):
        """Test download fails without workspace."""
        result = runner.invoke(cli, [
            "download",
            "--source-token", "xoxp-test"
        ])
        assert result.exit_code == 1
        assert "workspace is required" in result.output

    def test_download_missing_token(self, runner):
        """Test download fails without token."""
        result = runner.invoke(cli, [
            "download",
            "--source-workspace", "test"
        ])
        assert result.exit_code == 1
        assert "token is required" in result.output

    def test_download_from_env(self, runner):
        """Test download reads from environment variables."""
        with patch('emoji_bulk_migrator.cli.download_emojis') as mock_download:
            mock_download.return_value = Mock(processed=5, skipped=2, failed=0, errors=[])
            
            result = runner.invoke(cli, ["download"], env={
                "SOURCE_SLACK_WORKSPACE": "envworkspace",
                "SOURCE_SLACK_TOKEN": "env-token"
            })
            
            assert result.exit_code == 0
            assert "Download complete" in result.output
            mock_download.assert_called_once()

    def test_download_args_override_env(self, runner):
        """Test that CLI args override env vars."""
        with patch('emoji_bulk_migrator.cli.download_emojis') as mock_download:
            with patch('emoji_bulk_migrator.cli.create_api_handler') as mock_handler:
                mock_download.return_value = Mock(processed=0, skipped=0, failed=0, errors=[])
                mock_handler.return_value = Mock()
                
                result = runner.invoke(cli, [
                    "download",
                    "--source-workspace", "argworkspace",
                    "--source-token", "arg-token"
                ], env={
                    "SOURCE_SLACK_WORKSPACE": "envworkspace",
                    "SOURCE_SLACK_TOKEN": "env-token"
                })
                
                # Check that argworkspace was used (from CLI), not envworkspace
                assert "argworkspace" in result.output


class TestUploadCommand:
    """Tests for the upload command."""

    def test_upload_help(self, runner):
        """Test upload --help."""
        result = runner.invoke(cli, ["upload", "--help"])
        assert result.exit_code == 0
        assert "Upload emojis" in result.output
        assert "--dest-workspace" in result.output
        assert "--dest-token" in result.output

    def test_upload_missing_config(self, runner):
        """Test upload fails without config."""
        result = runner.invoke(cli, ["upload"])
        assert result.exit_code == 1
        assert "required" in result.output

    def test_upload_success(self, runner):
        """Test successful upload."""
        with patch('emoji_bulk_migrator.cli.upload_emojis') as mock_upload:
            mock_upload.return_value = Mock(processed=3, skipped=1, failed=0, errors=[])
            
            result = runner.invoke(cli, [
                "upload",
                "--dest-workspace", "destworkspace",
                "--dest-token", "dest-token"
            ])
            
            assert result.exit_code == 0
            assert "Upload complete" in result.output
            assert "Uploaded:   3" in result.output
            assert "Skipped:    1" in result.output


class TestSyncCommand:
    """Tests for the sync command."""

    def test_sync_help(self, runner):
        """Test sync --help."""
        result = runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Sync emojis" in result.output
        assert "--source-workspace" in result.output
        assert "--dest-workspace" in result.output

    def test_sync_missing_source(self, runner):
        """Test sync fails without source config."""
        result = runner.invoke(cli, [
            "sync",
            "--dest-workspace", "dest",
            "--dest-token", "token"
        ])
        assert result.exit_code == 1
        assert "Source" in result.output and "required" in result.output

    def test_sync_missing_dest(self, runner):
        """Test sync fails without dest config."""
        result = runner.invoke(cli, [
            "sync",
            "--source-workspace", "source",
            "--source-token", "token"
        ])
        assert result.exit_code == 1
        assert "Destination" in result.output and "required" in result.output

    def test_sync_success(self, runner):
        """Test successful sync."""
        with patch('emoji_bulk_migrator.cli.download_emojis') as mock_download:
            with patch('emoji_bulk_migrator.cli.upload_emojis') as mock_upload:
                mock_download.return_value = Mock(processed=5, skipped=0, failed=0, errors=[])
                mock_upload.return_value = Mock(processed=5, skipped=0, failed=0, errors=[])
                
                result = runner.invoke(cli, [
                    "sync",
                    "--source-workspace", "source",
                    "--source-token", "src-token",
                    "--dest-workspace", "dest",
                    "--dest-token", "dst-token"
                ])
                
                assert result.exit_code == 0
                assert "Sync Complete" in result.output


class TestListCommand:
    """Tests for the list command."""

    def test_list_help(self, runner):
        """Test list --help."""
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List emojis" in result.output

    def test_list_empty(self, runner, tmp_path):
        """Test list with empty directory."""
        result = runner.invoke(cli, [
            "--storage-path", str(tmp_path),
            "list"
        ])
        assert result.exit_code == 0
        assert "No emojis found" in result.output

    def test_list_with_files(self, runner, tmp_path):
        """Test list with files in directory."""
        # Create some test files
        (tmp_path / "emoji1.png").write_bytes(b"test")
        (tmp_path / "emoji2.gif").write_bytes(b"test")
        
        result = runner.invoke(cli, [
            "--storage-path", str(tmp_path),
            "list"
        ])
        
        assert result.exit_code == 0
        assert "Found 2 emojis" in result.output
        assert "emoji1.png" in result.output
        assert "emoji2.gif" in result.output


class TestCountCommand:
    """Tests for the count command."""

    def test_count_help(self, runner):
        """Test count --help."""
        result = runner.invoke(cli, ["count", "--help"])
        assert result.exit_code == 0
        assert "Count emojis" in result.output

    def test_count_success(self, runner):
        """Test successful count."""
        import asyncio
        from unittest.mock import AsyncMock
        
        with patch('emoji_bulk_migrator.cli.create_async_handler') as mock_handler:
            mock_api = Mock()
            # list_emojis is now async
            mock_api.list_emojis = AsyncMock(return_value=[
                Mock(extension=".png"),
                Mock(extension=".gif"),
                Mock(extension=".png"),
            ])
            mock_handler.return_value = mock_api
            
            result = runner.invoke(cli, [
                "count",
                "--source-workspace", "test",
                "--source-token", "token"
            ])
            
            assert result.exit_code == 0
            assert "Found 3 custom emojis" in result.output
            assert ".png: 2" in result.output
            assert ".gif: 1" in result.output


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config(self):
        """Test validation of valid config."""
        config = SlackConfig(workspace="test", token="xoxp-123")
        assert validate_config(config, "Source") is True

    def test_missing_workspace(self):
        """Test validation fails with missing workspace."""
        config = SlackConfig(workspace="", token="xoxp-123")
        assert validate_config(config, "Source") is False

    def test_missing_token(self):
        """Test validation fails with missing token."""
        config = SlackConfig(workspace="test", token="")
        assert validate_config(config, "Source") is False


class TestCreateApiHandler:
    """Tests for create_api_handler function."""

    def test_creates_web_api_handler(self):
        """Test creating web API handler."""
        config = SlackConfig(workspace="test", token="xoxp-123")
        
        with patch('emoji_bulk_migrator.cli.SlackWebApiHandler') as mock_class:
            create_api_handler(config, "web_api")
            mock_class.assert_called_once_with(config)

    def test_creates_http_handler(self):
        """Test creating HTTP handler."""
        config = SlackConfig(workspace="test", token="xoxp-123")
        
        with patch('emoji_bulk_migrator.cli.SlackHttpHandler') as mock_class:
            create_api_handler(config, "http")
            mock_class.assert_called_once_with(config)


class TestGlobalOptions:
    """Tests for global options."""

    def test_storage_path_option(self, runner, tmp_path):
        """Test --storage-path option."""
        result = runner.invoke(cli, [
            "--storage-path", str(tmp_path),
            "list"
        ])
        assert result.exit_code == 0

    def test_api_mode_option(self, runner):
        """Test --api-mode option."""
        with patch('emoji_bulk_migrator.cli.download_emojis') as mock_download:
            with patch('emoji_bulk_migrator.cli.SlackHttpHandler') as mock_http:
                mock_download.return_value = Mock(processed=0, skipped=0, failed=0, errors=[])
                mock_http.return_value = Mock()
                
                result = runner.invoke(cli, [
                    "--api-mode", "http",
                    "download",
                    "--source-workspace", "test",
                    "--source-token", "token"
                ])
                
                # HTTP handler should be used
                mock_http.assert_called_once()

    def test_verbose_option(self, runner, tmp_path):
        """Test -v/--verbose option."""
        result = runner.invoke(cli, [
            "-v",
            "--storage-path", str(tmp_path),
            "list"
        ])
        assert result.exit_code == 0

    def test_quiet_option(self, runner, tmp_path):
        """Test -q/--quiet option."""
        result = runner.invoke(cli, [
            "-q",
            "--storage-path", str(tmp_path),
            "list"
        ])
        assert result.exit_code == 0


class TestShortOptions:
    """Tests for short option aliases."""

    def test_short_source_options(self, runner):
        """Test short options for source config."""
        with patch('emoji_bulk_migrator.cli.download_emojis') as mock_download:
            mock_download.return_value = Mock(processed=0, skipped=0, failed=0, errors=[])
            
            result = runner.invoke(cli, [
                "download",
                "-sw", "myworkspace",
                "-st", "mytoken"
            ])
            
            assert result.exit_code == 0

    def test_short_dest_options(self, runner):
        """Test short options for dest config."""
        with patch('emoji_bulk_migrator.cli.upload_emojis') as mock_upload:
            mock_upload.return_value = Mock(processed=0, skipped=0, failed=0, errors=[])
            
            result = runner.invoke(cli, [
                "upload",
                "-dw", "myworkspace",
                "-dt", "mytoken"
            ])
            
            assert result.exit_code == 0
