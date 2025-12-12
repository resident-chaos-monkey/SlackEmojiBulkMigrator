"""Protocol definitions for handler interfaces.

These protocols define the contracts that handlers must implement,
enabling dependency injection and easy testing.
"""

from typing import Protocol, runtime_checkable

from emoji_bulk_migrator.models import Emoji


@runtime_checkable
class SlackApiHandler(Protocol):
    """Protocol for Slack API handlers.
    
    Implementations can use different methods to interact with Slack:
    - Official Web API (requires admin privileges for some operations)
    - HTTP-based approach (works for non-admins with browser session)
    """

    def list_emojis(self) -> list[Emoji]:
        """Fetch the list of custom emojis from the workspace.
        
        Returns:
            List of Emoji objects, excluding aliases.
        """
        ...

    def download_emoji(self, url: str) -> bytes:
        """Download an emoji image from the given URL.
        
        Args:
            url: The URL of the emoji image.
            
        Returns:
            The raw image bytes.
        """
        ...

    def upload_emoji(self, name: str, image_data: bytes) -> None:
        """Upload an emoji to the workspace.
        
        Args:
            name: The emoji name (without colons or extension).
            image_data: The raw image bytes.
            
        Raises:
            Exception: If the upload fails.
        """
        ...


@runtime_checkable
class StorageHandler(Protocol):
    """Protocol for local storage handlers.
    
    Handles reading and writing emoji files to local storage,
    which serves as an intermediary for syncing between workspaces.
    """

    def list_files(self) -> list[str]:
        """List all emoji files in storage.
        
        Returns:
            List of filenames (with extensions).
        """
        ...

    def read_file(self, filename: str) -> bytes:
        """Read an emoji file from storage.
        
        Args:
            filename: The filename to read.
            
        Returns:
            The raw file bytes.
        """
        ...

    def write_file(self, filename: str, content: bytes) -> None:
        """Write an emoji file to storage.
        
        Args:
            filename: The filename to write.
            content: The raw file bytes.
        """
        ...

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in storage.
        
        Args:
            filename: The filename to check.
            
        Returns:
            True if the file exists, False otherwise.
        """
        ...
