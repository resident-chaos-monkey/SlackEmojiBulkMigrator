"""Tests for sync logic functions."""

import pytest
from emoji_bulk_migrator.models import Emoji, SyncResult
from emoji_bulk_migrator.sync import (
    sanitize_filename,
    compute_emojis_to_download,
    compute_emojis_to_upload,
)


class TestSanitizeFilename:
    """Tests for the sanitize_filename function."""

    def test_no_special_chars(self):
        """Test filename with no special characters."""
        assert sanitize_filename("emoji.png") == "emoji.png"

    def test_with_colon(self):
        """Test filename with colon."""
        assert sanitize_filename("emoji:name.png") == "emoji_name.png"

    def test_with_pipe(self):
        """Test filename with pipe (included in invalid chars)."""
        assert sanitize_filename("emoji|name.png") == "emoji_name.png"

    def test_with_semicolon(self):
        """Test filename with semicolon."""
        assert sanitize_filename("emoji;name.png") == "emoji_name.png"

    def test_multiple_special_chars(self):
        """Test filename with multiple special characters."""
        assert sanitize_filename("a:b;c:d.gif") == "a_b_c_d.gif"


class TestComputeEmojisToDownload:
    """Tests for compute_emojis_to_download function."""

    def test_empty_remote_list(self):
        """Test with no remote emojis."""
        remote = []
        local = ["existing.png"]
        
        result = compute_emojis_to_download(remote, local)
        
        assert result == []

    def test_empty_local_list(self):
        """Test with no local files - should download all."""
        remote = [
            Emoji(name="emoji1", url="http://example.com/1.png", extension=".png"),
            Emoji(name="emoji2", url="http://example.com/2.gif", extension=".gif"),
        ]
        local = []
        
        result = compute_emojis_to_download(remote, local)
        
        assert len(result) == 2
        assert result[0].name == "emoji1"
        assert result[1].name == "emoji2"

    def test_some_existing_local_files(self):
        """Test with some files already downloaded."""
        remote = [
            Emoji(name="emoji1", url="http://example.com/1.png", extension=".png"),
            Emoji(name="emoji2", url="http://example.com/2.gif", extension=".gif"),
            Emoji(name="emoji3", url="http://example.com/3.png", extension=".png"),
        ]
        local = ["emoji1.png", "emoji3.png"]
        
        result = compute_emojis_to_download(remote, local)
        
        assert len(result) == 1
        assert result[0].name == "emoji2"

    def test_all_files_exist_locally(self):
        """Test when all remote emojis exist locally."""
        remote = [
            Emoji(name="emoji1", url="http://example.com/1.png", extension=".png"),
            Emoji(name="emoji2", url="http://example.com/2.gif", extension=".gif"),
        ]
        local = ["emoji1.png", "emoji2.gif"]
        
        result = compute_emojis_to_download(remote, local)
        
        assert result == []

    def test_handles_sanitized_filenames(self):
        """Test that sanitized filenames are matched correctly."""
        remote = [
            Emoji(name="emoji:special", url="http://example.com/1.png", extension=".png"),
        ]
        # Local file was sanitized when saved
        local = ["emoji_special.png"]
        
        result = compute_emojis_to_download(remote, local)
        
        assert result == []


class TestComputeEmojisToUpload:
    """Tests for compute_emojis_to_upload function."""

    def test_empty_local_list(self):
        """Test with no local files."""
        local = []
        remote = [
            Emoji(name="existing", url="http://example.com/1.png", extension=".png"),
        ]
        
        result = compute_emojis_to_upload(local, remote)
        
        assert result == []

    def test_empty_remote_list(self):
        """Test with no remote emojis - should upload all."""
        local = ["emoji1.png", "emoji2.gif"]
        remote = []
        
        result = compute_emojis_to_upload(local, remote)
        
        assert len(result) == 2
        assert "emoji1.png" in result
        assert "emoji2.gif" in result

    def test_some_existing_remote(self):
        """Test with some emojis already on remote."""
        local = ["emoji1.png", "emoji2.gif", "emoji3.png"]
        remote = [
            Emoji(name="emoji1", url="http://example.com/1.png", extension=".png"),
        ]
        
        result = compute_emojis_to_upload(local, remote)
        
        assert len(result) == 2
        assert "emoji2.gif" in result
        assert "emoji3.png" in result
        assert "emoji1.png" not in result

    def test_all_exist_on_remote(self):
        """Test when all local files exist on remote."""
        local = ["emoji1.png", "emoji2.gif"]
        remote = [
            Emoji(name="emoji1", url="http://example.com/1.png", extension=".png"),
            Emoji(name="emoji2", url="http://example.com/2.gif", extension=".gif"),
        ]
        
        result = compute_emojis_to_upload(local, remote)
        
        assert result == []

    def test_matches_by_name_not_extension(self):
        """Test that matching is by name, not full filename."""
        local = ["emoji1.png"]
        remote = [
            # Same name but different extension on remote
            Emoji(name="emoji1", url="http://example.com/1.gif", extension=".gif"),
        ]
        
        result = compute_emojis_to_upload(local, remote)
        
        # Should NOT upload because emoji1 already exists
        assert result == []


class TestIntegration:
    """Integration tests for sync logic."""

    def test_round_trip_consistency(self):
        """Test that download and upload logic are consistent."""
        # Simulate emojis on source workspace
        source_emojis = [
            Emoji(name="emoji1", url="http://source/1.png", extension=".png"),
            Emoji(name="emoji2", url="http://source/2.gif", extension=".gif"),
            Emoji(name="emoji3", url="http://source/3.png", extension=".png"),
        ]
        
        # Start with empty local storage
        local_files = []
        
        # Compute what to download
        to_download = compute_emojis_to_download(source_emojis, local_files)
        assert len(to_download) == 3
        
        # Simulate downloading - files appear in local storage
        local_files = [e.filename for e in to_download]
        
        # Emojis on destination workspace
        dest_emojis = [
            Emoji(name="emoji1", url="http://dest/1.png", extension=".png"),
        ]
        
        # Compute what to upload
        to_upload = compute_emojis_to_upload(local_files, dest_emojis)
        
        # Should upload emoji2 and emoji3 (emoji1 exists on dest)
        assert len(to_upload) == 2
        assert "emoji2.gif" in to_upload
        assert "emoji3.png" in to_upload
