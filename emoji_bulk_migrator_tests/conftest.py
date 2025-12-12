"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import os


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_emoji_data():
    """Sample emoji image data (minimal PNG)."""
    # Minimal valid PNG (1x1 transparent pixel)
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


@pytest.fixture
def mock_slack_emoji_list():
    """Mock Slack emoji list API response."""
    return {
        "ok": True,
        "emoji": {
            "thumbsup": "https://emoji.slack-edge.com/T123/thumbsup/abc123.png",
            "party": "https://emoji.slack-edge.com/T123/party/def456.gif",
            "rocket": "https://emoji.slack-edge.com/T123/rocket/ghi789.png",
            "plus1": "alias:thumbsup",  # This is an alias
        }
    }


@pytest.fixture
def mock_slack_admin_list():
    """Mock Slack emoji.adminList API response."""
    return {
        "ok": True,
        "emoji": [
            {
                "name": "thumbsup",
                "url": "https://emoji.slack-edge.com/T123/thumbsup/abc123.png",
                "user_display_name": "User",
                "created": 1234567890,
            },
            {
                "name": "party",
                "url": "https://emoji.slack-edge.com/T123/party/def456.gif",
                "user_display_name": "User",
                "created": 1234567891,
            },
            {
                "name": "plus1",
                "url": "alias:thumbsup",
                "alias_for": "thumbsup",
                "user_display_name": "User",
                "created": 1234567892,
            },
        ],
        "paging": {
            "count": 100,
            "total": 3,
            "page": 1,
            "pages": 1,
        }
    }
