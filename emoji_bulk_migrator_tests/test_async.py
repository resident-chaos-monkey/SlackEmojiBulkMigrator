"""Tests for async handlers and operations."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import ClientResponseError

from emoji_bulk_migrator.models import Emoji, SlackConfig
from emoji_bulk_migrator.async_slack import AsyncSlackHandler


@pytest.fixture
def config():
    """Create test config."""
    return SlackConfig(
        workspace="testworkspace",
        token="xoxp-test-token",
        cookie="test-cookie"
    )


@pytest.fixture
def handler(config):
    """Create async handler with default concurrency."""
    return AsyncSlackHandler(config, max_concurrent=5)


@pytest.fixture
def sequential_handler(config):
    """Create async handler with sequential execution."""
    return AsyncSlackHandler(config, max_concurrent=1)


class TestAsyncSlackHandler:
    """Tests for AsyncSlackHandler."""

    def test_init_defaults(self, config):
        """Test default initialization."""
        handler = AsyncSlackHandler(config)
        assert handler._max_concurrent == 10
        assert handler._retry_attempts == 3

    def test_init_custom_concurrency(self, config):
        """Test custom concurrency setting."""
        handler = AsyncSlackHandler(config, max_concurrent=5)
        assert handler._max_concurrent == 5

    def test_init_sequential(self, config):
        """Test sequential mode (concurrency=1)."""
        handler = AsyncSlackHandler(config, max_concurrent=1)
        assert handler._max_concurrent == 1

    def test_get_headers(self, handler):
        """Test header generation."""
        headers = handler._get_headers()
        assert "Cookie" in headers
        assert "Authorization" in headers
        assert headers["Cookie"] == "test-cookie"
        assert "Bearer" in headers["Authorization"]


class TestAsyncDownload:
    """Tests for async download operations."""

    @pytest.mark.asyncio
    async def test_download_emoji_success(self, handler):
        """Test successful emoji download."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"image data")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            result = await handler.download_emoji("https://example.com/emoji.png")
            
            assert result == b"image data"

    @pytest.mark.asyncio
    async def test_download_many_concurrent(self, handler):
        """Test downloading multiple emojis concurrently."""
        urls = [f"https://example.com/emoji{i}.png" for i in range(5)]
        
        async def mock_download(url):
            return b"data"
        
        with patch.object(handler, 'download_emoji', side_effect=mock_download):
            results = await handler.download_many(urls)
            
            assert len(results) == 5
            for url, content in results:
                assert content == b"data"

    @pytest.mark.asyncio
    async def test_download_many_with_failures(self, handler):
        """Test that failures are captured but don't stop other downloads."""
        urls = ["https://example.com/good.png", "https://example.com/bad.png"]
        
        async def mock_download(url):
            if "bad" in url:
                raise Exception("Download failed")
            return b"data"
        
        with patch.object(handler, 'download_emoji', side_effect=mock_download):
            results = await handler.download_many(urls)
            
            assert len(results) == 2
            # First should succeed
            assert results[0][1] == b"data"
            # Second should be an exception
            assert isinstance(results[1][1], Exception)


class TestAsyncUpload:
    """Tests for async upload operations."""

    @pytest.mark.asyncio
    async def test_upload_many(self, handler):
        """Test uploading multiple emojis."""
        items = [
            ("emoji1", b"data1", "image/png"),
            ("emoji2", b"data2", "image/gif"),
        ]
        
        async def mock_upload(name, data, ctype):
            pass  # Success
        
        with patch.object(handler, 'upload_emoji', side_effect=mock_upload):
            results = await handler.upload_many(items)
            
            assert len(results) == 2
            # Both should succeed (error is None)
            assert results[0] == ("emoji1", None)
            assert results[1] == ("emoji2", None)

    @pytest.mark.asyncio
    async def test_upload_many_with_failures(self, handler):
        """Test that upload failures are captured."""
        items = [
            ("good", b"data", "image/png"),
            ("bad", b"data", "image/png"),
        ]
        
        async def mock_upload(name, data, ctype):
            if name == "bad":
                raise Exception("Upload failed")
        
        with patch.object(handler, 'upload_emoji', side_effect=mock_upload):
            results = await handler.upload_many(items)
            
            assert results[0] == ("good", None)
            assert results[1][0] == "bad"
            assert isinstance(results[1][1], Exception)


class TestConcurrencyControl:
    """Tests for concurrency limiting."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, config):
        """Test that semaphore limits concurrent requests."""
        handler = AsyncSlackHandler(config, max_concurrent=2)
        
        concurrent_count = 0
        max_concurrent_seen = 0
        
        async def mock_download(url):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate network delay
            concurrent_count -= 1
            return b"data"
        
        with patch.object(handler, '_download_with_retry', side_effect=mock_download):
            urls = [f"https://example.com/{i}.png" for i in range(10)]
            await handler.download_many(urls)
        
        # Should never exceed max_concurrent
        assert max_concurrent_seen <= 2

    @pytest.mark.asyncio
    async def test_sequential_mode(self, sequential_handler):
        """Test that concurrency=1 runs sequentially."""
        execution_order = []
        
        async def mock_download(url):
            execution_order.append(f"start_{url}")
            await asyncio.sleep(0.01)
            execution_order.append(f"end_{url}")
            return b"data"
        
        with patch.object(sequential_handler, '_download_with_retry', side_effect=mock_download):
            urls = ["a", "b", "c"]
            await sequential_handler.download_many(urls)
        
        # With concurrency=1, operations should complete one at a time
        # start_a, end_a, start_b, end_b, start_c, end_c
        for i in range(0, len(execution_order) - 1, 2):
            # Each start should be followed by its end before next start
            assert execution_order[i].startswith("start_")
            assert execution_order[i + 1].startswith("end_")


class TestProgressCallback:
    """Tests for progress callbacks."""

    @pytest.mark.asyncio
    async def test_download_progress_callback(self, handler):
        """Test that progress callback is called during download."""
        progress_calls = []
        
        async def progress_callback(completed, total):
            progress_calls.append((completed, total))
        
        async def mock_download(url):
            return b"data"
        
        with patch.object(handler, 'download_emoji', side_effect=mock_download):
            urls = ["a", "b", "c"]
            await handler.download_many(urls, progress_callback)
        
        # Should be called once per download
        assert len(progress_calls) == 3
        # Final call should show 3/3
        assert (3, 3) in progress_calls

    @pytest.mark.asyncio
    async def test_upload_progress_callback(self, handler):
        """Test that progress callback is called during upload."""
        progress_calls = []
        
        async def progress_callback(completed, total):
            progress_calls.append((completed, total))
        
        async def mock_upload(name, data, ctype):
            pass
        
        with patch.object(handler, 'upload_emoji', side_effect=mock_upload):
            items = [("a", b"", "image/png"), ("b", b"", "image/png")]
            await handler.upload_many(items, progress_callback)
        
        assert len(progress_calls) == 2
