"""Tests for data models."""

import os
import pytest
from emoji_bulk_migrator.models import Emoji, SlackConfig, SyncResult, ApiProtocol


class TestEmoji:
    """Tests for the Emoji dataclass."""

    def test_emoji_creation(self):
        """Test basic emoji creation."""
        emoji = Emoji(name="thumbsup", url="https://example.com/thumbsup.png", extension=".png")
        
        assert emoji.name == "thumbsup"
        assert emoji.url == "https://example.com/thumbsup.png"
        assert emoji.extension == ".png"

    def test_emoji_filename_property(self):
        """Test the filename property."""
        emoji = Emoji(name="party", url="https://example.com/party.gif", extension=".gif")
        
        assert emoji.filename == "party.gif"

    def test_emoji_from_url(self):
        """Test creating emoji from URL."""
        emoji = Emoji.from_url(
            name="rocket",
            url="https://emoji.slack-edge.com/T123/rocket/abc123.png"
        )
        
        assert emoji.name == "rocket"
        assert emoji.extension == ".png"

    def test_emoji_from_url_with_query_params(self):
        """Test creating emoji from URL with query parameters."""
        emoji = Emoji.from_url(
            name="star",
            url="https://cdn.example.com/star.gif?v=123"
        )
        
        assert emoji.extension == ".gif"

    def test_emoji_is_frozen(self):
        """Test that emoji is immutable."""
        emoji = Emoji(name="test", url="https://example.com/test.png", extension=".png")
        
        with pytest.raises(AttributeError):
            emoji.name = "changed"


class TestSlackConfig:
    """Tests for the SlackConfig dataclass."""

    def test_config_creation(self):
        """Test basic config creation."""
        config = SlackConfig(workspace="mycompany", token="xoxp-123")
        
        assert config.workspace == "mycompany"
        assert config.token == "xoxp-123"
        assert config.cookie is None

    def test_config_with_cookie(self):
        """Test config with optional cookie."""
        config = SlackConfig(workspace="mycompany", token="xoxp-123", cookie="d=abc123")
        
        assert config.cookie == "d=abc123"

    def test_config_from_env(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("SLACK_WORKSPACE", "testworkspace")
        monkeypatch.setenv("SLACK_TOKEN", "xoxp-test-token")
        monkeypatch.setenv("SLACK_COOKIE", "test-cookie")
        
        config = SlackConfig.from_env()
        
        assert config.workspace == "testworkspace"
        assert config.token == "xoxp-test-token"
        assert config.cookie == "test-cookie"

    def test_config_from_env_with_prefix(self, monkeypatch):
        """Test creating config with prefix."""
        monkeypatch.setenv("SOURCE_SLACK_WORKSPACE", "sourceworkspace")
        monkeypatch.setenv("SOURCE_SLACK_TOKEN", "source-token")
        
        config = SlackConfig.from_env("SOURCE_")
        
        assert config.workspace == "sourceworkspace"
        assert config.token == "source-token"

    def test_config_from_env_missing_values(self, monkeypatch):
        """Test that missing env vars result in empty strings."""
        # Clear any existing env vars
        monkeypatch.delenv("SLACK_WORKSPACE", raising=False)
        monkeypatch.delenv("SLACK_TOKEN", raising=False)
        
        config = SlackConfig.from_env()
        
        assert config.workspace == ""
        assert config.token == ""


class TestSyncResult:
    """Tests for the SyncResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = SyncResult()
        
        assert result.processed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    def test_custom_values(self):
        """Test with custom values."""
        result = SyncResult(processed=5, skipped=3, failed=1, errors=["error1"])
        
        assert result.processed == 5
        assert result.skipped == 3
        assert result.failed == 1
        assert result.errors == ["error1"]


class TestApiProtocol:
    """Tests for the ApiProtocol enum."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert ApiProtocol.WEB_API.value == "web_api"
        assert ApiProtocol.HTTP.value == "http"
