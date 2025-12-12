"""Slack HTTP handler implementation.

This handler uses direct HTTP requests to interact with Slack.
Works for non-admin users who have browser session cookies.
"""

import logging
from time import sleep
from typing import Optional

import requests

from emoji_bulk_migrator.models import Emoji, SlackConfig

logger = logging.getLogger(__name__)

# API endpoints
EMOJI_LIST_ENDPOINT = "/api/emoji.adminList"
EMOJI_ADD_ENDPOINT = "/api/emoji.add"


class SlackHttpHandler:
    """Handler for Slack HTTP-based operations.
    
    Uses direct HTTP requests with session cookies. This approach
    works for users who don't have admin API access but can access
    the emoji customization page in their browser.
    """

    def __init__(self, config: SlackConfig):
        """Initialize the handler.
        
        Args:
            config: Slack configuration with workspace, token, and cookie.
        """
        self._config = config
        self._base_url = f"https://{config.workspace}.slack.com"
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a configured requests session."""
        session = requests.Session()
        
        headers = {}
        if self._config.cookie:
            headers["Cookie"] = self._config.cookie
        if self._config.token:
            headers["Authorization"] = f"Bearer {self._config.token}"
        
        session.headers.update(headers)
        return session

    @classmethod
    def from_env(cls, prefix: str = "") -> "SlackHttpHandler":
        """Create handler from environment variables.
        
        Args:
            prefix: Optional prefix for env vars (e.g., 'SOURCE_').
        """
        config = SlackConfig.from_env(prefix)
        return cls(config)

    def list_emojis(self) -> list[Emoji]:
        """Fetch the list of custom emojis from the workspace.
        
        Uses the emoji.adminList endpoint with pagination.
        
        Returns:
            List of Emoji objects, excluding aliases.
        """
        page = 1
        total_pages = None
        emojis = []
        
        while total_pages is None or page <= total_pages:
            data = {
                "token": self._config.token,
                "page": page,
                "count": 100,  # Items per page
            }
            
            url = f"{self._base_url}{EMOJI_LIST_ENDPOINT}"
            response = self._session.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("ok"):
                error = result.get("error", "unknown")
                raise Exception(f"Failed to list emojis: {error}")
            
            # Process emoji entries
            for entry in result.get("emoji", []):
                emoji_url = entry.get("url", "")
                name = entry.get("name", "")
                
                # Skip aliases
                if emoji_url.startswith("alias:"):
                    alias_for = entry.get("alias_for", "unknown")
                    logger.debug(f"Skipping alias: {name} -> {alias_for}")
                    continue
                
                emojis.append(Emoji.from_url(name, emoji_url))
            
            # Update pagination
            if total_pages is None:
                paging = result.get("paging", {})
                total_pages = paging.get("pages", 1)
            
            logger.debug(f"Loaded page {page}/{total_pages}")
            page += 1
        
        return emojis

    def download_emoji(self, url: str) -> bytes:
        """Download an emoji image from the given URL.
        
        Args:
            url: The URL of the emoji image.
            
        Returns:
            The raw image bytes.
        """
        # Emoji images are on CDN, no auth needed
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def upload_emoji(
        self,
        name: str,
        image_data: bytes,
        content_type: str = "image/png",
        max_retries: int = 3
    ) -> None:
        """Upload an emoji to the workspace.
        
        Args:
            name: The emoji name (without colons).
            image_data: The raw image bytes.
            content_type: The MIME type of the image.
            max_retries: Maximum retries on rate limiting.
        """
        url = f"{self._base_url}{EMOJI_ADD_ENDPOINT}"
        
        # Determine file extension from content type
        ext_map = {
            "image/png": "png",
            "image/gif": "gif",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }
        ext = ext_map.get(content_type, "png")
        
        data = {
            "mode": "data",
            "name": name,
            "token": self._config.token,
        }
        
        files = {
            "image": (f"{name}.{ext}", image_data, content_type)
        }
        
        for attempt in range(max_retries):
            response = self._session.post(url, data=data, files=files)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(f"Rate limited, waiting {retry_after}s...")
                sleep(retry_after)
                continue
            
            response.raise_for_status()
            
            result = response.json()
            if not result.get("ok"):
                error = result.get("error", "unknown")
                raise Exception(f"Emoji upload failed: {error}")
            
            logger.debug(f"Uploaded emoji: {name}")
            return
        
        raise Exception(f"Failed to upload {name} after {max_retries} retries")


def detect_content_type(filename: str) -> str:
    """Detect content type from filename extension.
    
    Args:
        filename: The filename with extension.
        
    Returns:
        MIME type string.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    type_map = {
        "png": "image/png",
        "gif": "image/gif",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    
    return type_map.get(ext, "image/png")
