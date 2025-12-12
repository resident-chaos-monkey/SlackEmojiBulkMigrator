"""Slack Web API handler implementation.

This handler uses the official Slack SDK to interact with Slack.
Note: Some operations (like admin.emoji.add) require admin privileges.
"""

import logging
from typing import Optional

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from emoji_bulk_migrator.models import Emoji, SlackConfig

logger = logging.getLogger(__name__)


class SlackWebApiHandler:
    """Handler for Slack Web API operations.
    
    Uses the official slack-sdk package. Best for users with admin
    access to their Slack workspace.
    """

    def __init__(self, config: SlackConfig):
        """Initialize the handler.
        
        Args:
            config: Slack configuration with workspace and token.
        """
        self._config = config
        self._client = WebClient(token=config.token)

    @classmethod
    def from_env(cls, prefix: str = "") -> "SlackWebApiHandler":
        """Create handler from environment variables.
        
        Args:
            prefix: Optional prefix for env vars (e.g., 'SOURCE_').
        """
        config = SlackConfig.from_env(prefix)
        return cls(config)

    def list_emojis(self) -> list[Emoji]:
        """Fetch the list of custom emojis from the workspace.
        
        Uses the emoji.list API endpoint.
        
        Returns:
            List of Emoji objects, excluding aliases.
        """
        try:
            response = self._client.emoji_list()
            emoji_dict = response.get("emoji", {})
            
            emojis = []
            for name, url in emoji_dict.items():
                # Skip aliases (they start with 'alias:')
                if url.startswith('alias:'):
                    logger.debug(f"Skipping alias: {name}")
                    continue
                
                emojis.append(Emoji.from_url(name, url))
            
            return emojis
            
        except SlackApiError as e:
            logger.error(f"Failed to list emojis: {e.response['error']}")
            raise

    def download_emoji(self, url: str) -> bytes:
        """Download an emoji image from the given URL.
        
        Args:
            url: The URL of the emoji image (from Slack CDN).
            
        Returns:
            The raw image bytes.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"Failed to download emoji from {url}: {e}")
            raise

    def upload_emoji(self, name: str, image_data: bytes) -> None:
        """Upload an emoji to the workspace.
        
        Note: This requires the admin.emoji:write scope and admin privileges.
        
        Args:
            name: The emoji name (without colons).
            image_data: The raw image bytes.
        """
        try:
            # admin.emoji.add requires the image as a file upload
            # We need to use the files approach
            response = self._client.admin_emoji_add(
                name=name,
                url=None,  # We're uploading directly
            )
            
            if not response.get("ok"):
                raise SlackApiError(
                    message=f"Upload failed: {response.get('error', 'unknown')}",
                    response=response
                )
                
        except SlackApiError as e:
            logger.error(f"Failed to upload emoji {name}: {e.response.get('error', str(e))}")
            raise


class SlackWebApiUploader:
    """Alternative uploader using multipart form upload.
    
    This approach works for adding emojis when you have the proper
    admin scopes but admin_emoji_add isn't working properly.
    """

    def __init__(self, config: SlackConfig):
        """Initialize the uploader.
        
        Args:
            config: Slack configuration with workspace and token.
        """
        self._config = config
        self._base_url = f"https://{config.workspace}.slack.com"
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.token}"
        })
        if config.cookie:
            self._session.headers.update({
                "Cookie": config.cookie
            })

    def upload_emoji(self, name: str, image_data: bytes, content_type: str = "image/png") -> None:
        """Upload an emoji using the /api/emoji.add endpoint.
        
        Args:
            name: The emoji name.
            image_data: The raw image bytes.
            content_type: The image MIME type.
        """
        url = f"{self._base_url}/api/emoji.add"
        
        # Determine file extension from content type
        ext_map = {
            "image/png": "png",
            "image/gif": "gif",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }
        ext = ext_map.get(content_type, "png")
        
        files = {
            "image": (f"{name}.{ext}", image_data, content_type)
        }
        data = {
            "mode": "data",
            "name": name,
            "token": self._config.token
        }
        
        response = self._session.post(url, data=data, files=files)
        response.raise_for_status()
        
        result = response.json()
        if not result.get("ok"):
            error = result.get("error", "unknown error")
            raise Exception(f"Emoji upload failed: {error}")
        
        logger.info(f"Successfully uploaded emoji: {name}")
