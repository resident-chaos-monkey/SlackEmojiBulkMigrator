"""Local file storage handler implementation."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalStorageHandler:
    """Handler for local file storage operations.
    
    Implements the StorageHandler protocol for storing emoji files
    on the local filesystem.
    """

    def __init__(self, path: str | Path):
        """Initialize the storage handler.
        
        Args:
            path: Directory path for storing emoji files.
        """
        self._path = Path(path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create the storage directory if it doesn't exist."""
        if not self._path.exists():
            self._path.mkdir(parents=True)
            logger.info(f"Created storage directory: {self._path}")

    @property
    def path(self) -> Path:
        """Return the storage path."""
        return self._path

    def list_files(self) -> list[str]:
        """List all files in the storage directory.
        
        Returns:
            List of filenames (not full paths).
        """
        if not self._path.exists():
            return []
        
        files = [
            f.name for f in self._path.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]
        return files

    def read_file(self, filename: str) -> bytes:
        """Read a file from storage.
        
        Args:
            filename: The filename to read.
            
        Returns:
            The raw file bytes.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        filepath = self._path / filename
        with open(filepath, 'rb') as f:
            return f.read()

    def write_file(self, filename: str, content: bytes) -> None:
        """Write a file to storage.
        
        Args:
            filename: The filename to write.
            content: The raw file bytes.
        """
        self._ensure_directory()
        filepath = self._path / filename
        with open(filepath, 'wb') as f:
            f.write(content)
        logger.debug(f"Wrote file: {filepath}")

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in storage.
        
        Args:
            filename: The filename to check.
            
        Returns:
            True if the file exists, False otherwise.
        """
        filepath = self._path / filename
        return filepath.is_file()

    def delete_file(self, filename: str) -> bool:
        """Delete a file from storage.
        
        Args:
            filename: The filename to delete.
            
        Returns:
            True if the file was deleted, False if it didn't exist.
        """
        filepath = self._path / filename
        if filepath.is_file():
            filepath.unlink()
            logger.debug(f"Deleted file: {filepath}")
            return True
        return False
