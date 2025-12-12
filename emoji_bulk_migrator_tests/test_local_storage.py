"""Tests for local storage handler."""

import os
import pytest
import tempfile
from pathlib import Path

from emoji_bulk_migrator.local_storage import LocalStorageHandler


class TestLocalStorageHandler:
    """Tests for the LocalStorageHandler class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage handler with temp directory."""
        return LocalStorageHandler(temp_dir)

    def test_init_creates_directory(self, temp_dir):
        """Test that init creates the storage directory."""
        path = os.path.join(temp_dir, "new_subdir")
        assert not os.path.exists(path)
        
        storage = LocalStorageHandler(path)
        
        assert os.path.exists(path)
        assert os.path.isdir(path)

    def test_path_property(self, storage, temp_dir):
        """Test the path property returns the correct path."""
        assert storage.path == Path(temp_dir)

    def test_list_files_empty(self, storage):
        """Test listing files in empty directory."""
        files = storage.list_files()
        
        assert files == []

    def test_list_files_with_files(self, storage, temp_dir):
        """Test listing files when files exist."""
        # Create some test files
        Path(temp_dir, "emoji1.png").write_bytes(b"test1")
        Path(temp_dir, "emoji2.gif").write_bytes(b"test2")
        
        files = storage.list_files()
        
        assert len(files) == 2
        assert "emoji1.png" in files
        assert "emoji2.gif" in files

    def test_list_files_excludes_hidden(self, storage, temp_dir):
        """Test that hidden files are excluded."""
        Path(temp_dir, ".hidden").write_bytes(b"hidden")
        Path(temp_dir, "visible.png").write_bytes(b"visible")
        
        files = storage.list_files()
        
        assert len(files) == 1
        assert "visible.png" in files
        assert ".hidden" not in files

    def test_list_files_excludes_directories(self, storage, temp_dir):
        """Test that directories are excluded."""
        Path(temp_dir, "subdir").mkdir()
        Path(temp_dir, "file.png").write_bytes(b"file")
        
        files = storage.list_files()
        
        assert files == ["file.png"]

    def test_write_file(self, storage, temp_dir):
        """Test writing a file."""
        content = b"test content"
        
        storage.write_file("test.png", content)
        
        filepath = Path(temp_dir, "test.png")
        assert filepath.exists()
        assert filepath.read_bytes() == content

    def test_read_file(self, storage, temp_dir):
        """Test reading a file."""
        content = b"test content"
        Path(temp_dir, "test.png").write_bytes(content)
        
        result = storage.read_file("test.png")
        
        assert result == content

    def test_read_file_not_found(self, storage):
        """Test reading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            storage.read_file("nonexistent.png")

    def test_file_exists_true(self, storage, temp_dir):
        """Test file_exists returns True for existing file."""
        Path(temp_dir, "exists.png").write_bytes(b"content")
        
        assert storage.file_exists("exists.png") is True

    def test_file_exists_false(self, storage):
        """Test file_exists returns False for non-existent file."""
        assert storage.file_exists("nonexistent.png") is False

    def test_file_exists_false_for_directory(self, storage, temp_dir):
        """Test file_exists returns False for directories."""
        Path(temp_dir, "subdir").mkdir()
        
        assert storage.file_exists("subdir") is False

    def test_delete_file(self, storage, temp_dir):
        """Test deleting a file."""
        Path(temp_dir, "todelete.png").write_bytes(b"content")
        
        result = storage.delete_file("todelete.png")
        
        assert result is True
        assert not Path(temp_dir, "todelete.png").exists()

    def test_delete_file_nonexistent(self, storage):
        """Test deleting a non-existent file."""
        result = storage.delete_file("nonexistent.png")
        
        assert result is False

    def test_write_then_read(self, storage):
        """Test write followed by read returns same content."""
        content = b"\x89PNG\r\n\x1a\n" + b"fake png data"
        
        storage.write_file("image.png", content)
        result = storage.read_file("image.png")
        
        assert result == content

    def test_write_overwrites_existing(self, storage):
        """Test that writing overwrites existing content."""
        storage.write_file("file.txt", b"original")
        storage.write_file("file.txt", b"updated")
        
        result = storage.read_file("file.txt")
        
        assert result == b"updated"
