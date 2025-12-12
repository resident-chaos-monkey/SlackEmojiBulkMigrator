"""Async Slack handler implementation using aiohttp.

Provides concurrent emoji downloads/uploads with configurable throttling.
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from emoji_bulk_migrator.models import Emoji, SlackConfig

logger = logging.getLogger(__name__)

# API endpoints
EMOJI_LIST_ENDPOINT = "/api/emoji.adminList"
EMOJI_ADD_ENDPOINT = "/api/emoji.add"


class AsyncSlackHandler:
    """Async handler for Slack operations with configurable concurrency.
    
    Uses aiohttp for concurrent HTTP requests with semaphore-based
    throttling to respect Slack's rate limits.
    """

    def __init__(
        self,
        config: SlackConfig,
        max_concurrent: int = 10,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize the async handler.
        
        Args:
            config: Slack configuration with workspace, token, and cookie.
            max_concurrent: Maximum concurrent requests (1 = sequential).
            retry_attempts: Number of retry attempts on failure.
            retry_delay: Base delay between retries (exponential backoff).
        """
        self._config = config
        self._max_concurrent = max_concurrent
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._base_url = f"https://{config.workspace}.slack.com"
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore for the current event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    def _get_headers(self) -> dict:
        """Get headers for requests."""
        headers = {}
        if self._config.cookie:
            headers["Cookie"] = self._config.cookie
        if self._config.token:
            headers["Authorization"] = f"Bearer {self._config.token}"
        return headers

    async def list_emojis(self) -> list[Emoji]:
        """Fetch the list of custom emojis from the workspace.
        
        Returns:
            List of Emoji objects, excluding aliases.
        """
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            return await self._fetch_emoji_list(session)

    async def _fetch_emoji_list(self, session: aiohttp.ClientSession) -> list[Emoji]:
        """Fetch paginated emoji list."""
        page = 1
        total_pages = None
        emojis = []
        
        while total_pages is None or page <= total_pages:
            data = {
                "token": self._config.token,
                "page": page,
                "count": 100,
            }
            
            url = f"{self._base_url}{EMOJI_LIST_ENDPOINT}"
            
            async with session.post(url, data=data) as response:
                response.raise_for_status()
                result = await response.json()
            
            if not result.get("ok"):
                error = result.get("error", "unknown")
                raise Exception(f"Failed to list emojis: {error}")
            
            for entry in result.get("emoji", []):
                emoji_url = entry.get("url", "")
                name = entry.get("name", "")
                
                if emoji_url.startswith("alias:"):
                    continue
                
                emojis.append(Emoji.from_url(name, emoji_url))
            
            if total_pages is None:
                paging = result.get("paging", {})
                total_pages = paging.get("pages", 1)
            
            logger.debug(f"Fetched emoji page {page}/{total_pages}")
            page += 1
        
        return emojis

    async def download_emoji(self, url: str) -> bytes:
        """Download a single emoji with semaphore throttling.
        
        Args:
            url: The URL of the emoji image.
            
        Returns:
            The raw image bytes.
        """
        semaphore = self._get_semaphore()
        
        async with semaphore:
            return await self._download_with_retry(url)

    async def _download_with_retry(self, url: str) -> bytes:
        """Download with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self._retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 429:
                            # Rate limited - wait and retry
                            retry_after = int(response.headers.get("Retry-After", 5))
                            logger.warning(f"Rate limited, waiting {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        response.raise_for_status()
                        return await response.read()
                        
            except Exception as e:
                last_error = e
                if attempt < self._retry_attempts - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.debug(f"Retry {attempt + 1}/{self._retry_attempts} after {delay}s: {e}")
                    await asyncio.sleep(delay)
        
        raise last_error or Exception(f"Failed to download {url}")

    async def download_many(
        self,
        urls: list[str],
        progress_callback: Optional[callable] = None,
    ) -> list[tuple[str, bytes | Exception]]:
        """Download multiple emojis concurrently.
        
        Args:
            urls: List of URLs to download.
            progress_callback: Optional async callback(completed, total).
            
        Returns:
            List of (url, content_or_exception) tuples.
        """
        results = []
        completed = 0
        total = len(urls)
        
        async def download_one(url: str) -> tuple[str, bytes | Exception]:
            nonlocal completed
            try:
                content = await self.download_emoji(url)
                result = (url, content)
            except Exception as e:
                result = (url, e)
            
            completed += 1
            if progress_callback:
                await progress_callback(completed, total)
            
            return result
        
        # Create tasks for all downloads
        tasks = [download_one(url) for url in urls]
        
        # Run with controlled concurrency (semaphore handles throttling)
        results = await asyncio.gather(*tasks)
        
        return results

    async def upload_emoji(
        self,
        name: str,
        image_data: bytes,
        content_type: str = "image/png",
    ) -> None:
        """Upload a single emoji with semaphore throttling.
        
        Args:
            name: The emoji name.
            image_data: The raw image bytes.
            content_type: The MIME type of the image.
        """
        semaphore = self._get_semaphore()
        
        async with semaphore:
            await self._upload_with_retry(name, image_data, content_type)

    async def _upload_with_retry(
        self,
        name: str,
        image_data: bytes,
        content_type: str,
    ) -> None:
        """Upload with exponential backoff retry."""
        url = f"{self._base_url}{EMOJI_ADD_ENDPOINT}"
        
        ext_map = {
            "image/png": "png",
            "image/gif": "gif",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }
        ext = ext_map.get(content_type, "png")
        
        last_error = None
        
        for attempt in range(self._retry_attempts):
            try:
                form_data = aiohttp.FormData()
                form_data.add_field("mode", "data")
                form_data.add_field("name", name)
                form_data.add_field("token", self._config.token)
                form_data.add_field(
                    "image",
                    image_data,
                    filename=f"{name}.{ext}",
                    content_type=content_type,
                )
                
                async with aiohttp.ClientSession(headers=self._get_headers()) as session:
                    async with session.post(url, data=form_data) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 5))
                            logger.warning(f"Rate limited uploading {name}, waiting {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        response.raise_for_status()
                        result = await response.json()
                        
                        if not result.get("ok"):
                            error = result.get("error", "unknown")
                            raise Exception(f"Upload failed: {error}")
                        
                        return
                        
            except Exception as e:
                last_error = e
                if attempt < self._retry_attempts - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.debug(f"Retry upload {attempt + 1}/{self._retry_attempts}: {e}")
                    await asyncio.sleep(delay)
        
        raise last_error or Exception(f"Failed to upload {name}")

    async def upload_many(
        self,
        items: list[tuple[str, bytes, str]],
        progress_callback: Optional[callable] = None,
    ) -> list[tuple[str, Exception | None]]:
        """Upload multiple emojis concurrently.
        
        Args:
            items: List of (name, image_data, content_type) tuples.
            progress_callback: Optional async callback(completed, total).
            
        Returns:
            List of (name, error_or_none) tuples.
        """
        results = []
        completed = 0
        total = len(items)
        
        async def upload_one(name: str, data: bytes, ctype: str) -> tuple[str, Exception | None]:
            nonlocal completed
            try:
                await self.upload_emoji(name, data, ctype)
                result = (name, None)
            except Exception as e:
                result = (name, e)
            
            completed += 1
            if progress_callback:
                await progress_callback(completed, total)
            
            return result
        
        tasks = [upload_one(name, data, ctype) for name, data, ctype in items]
        results = await asyncio.gather(*tasks)
        
        return results
