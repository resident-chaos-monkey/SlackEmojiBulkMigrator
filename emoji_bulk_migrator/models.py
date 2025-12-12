"""Data models for the emoji sync application."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os


class ApiProtocol(Enum):
    """Supported API protocols for connecting to Slack."""
    WEB_API = "web_api"  # Official Slack Web API (requires admin)
    HTTP = "http"  # HTTP-based approach (works for non-admins)


@dataclass(frozen=True)
class Emoji:
    """Represents a Slack emoji.
    
    Attributes:
        name: The emoji name (without colons), e.g., 'thumbsup'
        url: The URL where the emoji image is hosted
        extension: The file extension, e.g., '.png', '.gif'
    """
    name: str
    url: str
    extension: str

    @property
    def filename(self) -> str:
        """Return the full filename including extension."""
        return f"{self.name}{self.extension}"

    @classmethod
    def from_url(cls, name: str, url: str) -> "Emoji":
        """Create an Emoji from a name and URL, extracting the extension."""
        # Handle URLs like https://emoji.slack-edge.com/.../emoji.png
        extension = "." + url.split(".")[-1].split("?")[0]  # Handle query params
        return cls(name=name, url=url, extension=extension)


@dataclass
class SlackConfig:
    """Configuration for connecting to a Slack workspace.
    
    Attributes:
        workspace: The Slack workspace name (e.g., 'mycompany')
        token: API token or session token
        cookie: Optional cookie for HTTP-based auth
    """
    workspace: str
    token: str
    cookie: Optional[str] = None

    @classmethod
    def from_env(cls, prefix: str = "") -> "SlackConfig":
        """Create config from environment variables.
        
        Args:
            prefix: Optional prefix for env vars (e.g., 'SOURCE_' or 'DEST_')
        
        Environment variables:
            {PREFIX}SLACK_WORKSPACE: The workspace name
            {PREFIX}SLACK_TOKEN: The API/session token
            {PREFIX}SLACK_COOKIE: Optional cookie for HTTP auth
        """
        workspace = os.environ.get(f"{prefix}SLACK_WORKSPACE", "")
        token = os.environ.get(f"{prefix}SLACK_TOKEN", "")
        cookie = os.environ.get(f"{prefix}SLACK_COOKIE")
        return cls(workspace=workspace, token=token, cookie=cookie)


@dataclass
class SyncResult:
    """Result of a sync operation.
    
    Attributes:
        processed: Number of emojis successfully processed
        skipped: Number of emojis skipped (already exist)
        failed: Number of emojis that failed to process
        errors: List of error messages for failed items
    """
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
