"""Tests for Slack API handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from emoji_bulk_migrator.models import Emoji, SlackConfig
from emoji_bulk_migrator.slack_web_api import SlackWebApiHandler
from emoji_bulk_migrator.slack_http import SlackHttpHandler, detect_content_type


class TestSlackWebApiHandler:
    """Tests for SlackWebApiHandler."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return SlackConfig(workspace="testworkspace", token="xoxp-test-token")

    @pytest.fixture
    def handler(self, config):
        """Create handler with mocked client."""
        with patch('emoji_bulk_migrator.slack_web_api.WebClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            handler = SlackWebApiHandler(config)
            handler._client = mock_client
            yield handler

    def test_list_emojis_success(self, handler):
        """Test listing emojis successfully."""
        handler._client.emoji_list.return_value = {
            "ok": True,
            "emoji": {
                "thumbsup": "https://emoji.slack-edge.com/T123/thumbsup/abc.png",
                "party": "https://emoji.slack-edge.com/T123/party/def.gif",
            }
        }
        
        emojis = handler.list_emojis()
        
        assert len(emojis) == 2
        names = {e.name for e in emojis}
        assert "thumbsup" in names
        assert "party" in names

    def test_list_emojis_skips_aliases(self, handler):
        """Test that aliases are skipped."""
        handler._client.emoji_list.return_value = {
            "ok": True,
            "emoji": {
                "thumbsup": "https://emoji.slack-edge.com/T123/thumbsup/abc.png",
                "plus1": "alias:thumbsup",  # This is an alias
            }
        }
        
        emojis = handler.list_emojis()
        
        assert len(emojis) == 1
        assert emojis[0].name == "thumbsup"

    def test_download_emoji_success(self, handler):
        """Test downloading an emoji."""
        with patch('emoji_bulk_migrator.slack_web_api.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"image data"
            mock_get.return_value = mock_response
            
            result = handler.download_emoji("https://example.com/emoji.png")
            
            assert result == b"image data"
            mock_get.assert_called_once_with("https://example.com/emoji.png", timeout=30)

    def test_download_emoji_failure(self, handler):
        """Test download failure handling."""
        with patch('emoji_bulk_migrator.slack_web_api.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")
            
            with pytest.raises(requests.RequestException):
                handler.download_emoji("https://example.com/emoji.png")


class TestSlackHttpHandler:
    """Tests for SlackHttpHandler."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return SlackConfig(
            workspace="testworkspace",
            token="xoxp-test-token",
            cookie="d=test-cookie"
        )

    @pytest.fixture
    def handler(self, config):
        """Create handler."""
        return SlackHttpHandler(config)

    def test_init_creates_session(self, handler):
        """Test that init creates a session with headers."""
        assert handler._session is not None
        assert "Authorization" in handler._session.headers or "Cookie" in handler._session.headers

    def test_list_emojis_success(self, handler):
        """Test listing emojis via HTTP."""
        with patch.object(handler._session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "ok": True,
                "emoji": [
                    {"name": "emoji1", "url": "https://example.com/1.png"},
                    {"name": "emoji2", "url": "https://example.com/2.gif"},
                ],
                "paging": {"pages": 1}
            }
            mock_post.return_value = mock_response
            
            emojis = handler.list_emojis()
            
            assert len(emojis) == 2

    def test_list_emojis_pagination(self, handler):
        """Test pagination handling."""
        with patch.object(handler._session, 'post') as mock_post:
            # First page
            page1 = Mock()
            page1.json.return_value = {
                "ok": True,
                "emoji": [{"name": "emoji1", "url": "https://example.com/1.png"}],
                "paging": {"pages": 2}
            }
            # Second page
            page2 = Mock()
            page2.json.return_value = {
                "ok": True,
                "emoji": [{"name": "emoji2", "url": "https://example.com/2.png"}],
                "paging": {"pages": 2}
            }
            mock_post.side_effect = [page1, page2]
            
            emojis = handler.list_emojis()
            
            assert len(emojis) == 2
            assert mock_post.call_count == 2

    def test_list_emojis_skips_aliases(self, handler):
        """Test that aliases are skipped."""
        with patch.object(handler._session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "ok": True,
                "emoji": [
                    {"name": "emoji1", "url": "https://example.com/1.png"},
                    {"name": "alias1", "url": "alias:emoji1", "alias_for": "emoji1"},
                ],
                "paging": {"pages": 1}
            }
            mock_post.return_value = mock_response
            
            emojis = handler.list_emojis()
            
            assert len(emojis) == 1
            assert emojis[0].name == "emoji1"

    def test_download_emoji_success(self, handler):
        """Test downloading an emoji."""
        with patch('emoji_bulk_migrator.slack_http.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"image data"
            mock_get.return_value = mock_response
            
            result = handler.download_emoji("https://example.com/emoji.png")
            
            assert result == b"image data"


class TestDetectContentType:
    """Tests for detect_content_type function."""

    def test_png(self):
        assert detect_content_type("image.png") == "image/png"

    def test_gif(self):
        assert detect_content_type("image.gif") == "image/gif"

    def test_jpg(self):
        assert detect_content_type("image.jpg") == "image/jpeg"

    def test_jpeg(self):
        assert detect_content_type("image.jpeg") == "image/jpeg"

    def test_webp(self):
        assert detect_content_type("image.webp") == "image/webp"

    def test_unknown_defaults_to_png(self):
        assert detect_content_type("image.bmp") == "image/png"

    def test_no_extension(self):
        assert detect_content_type("noextension") == "image/png"

    def test_uppercase_extension(self):
        assert detect_content_type("image.PNG") == "image/png"
