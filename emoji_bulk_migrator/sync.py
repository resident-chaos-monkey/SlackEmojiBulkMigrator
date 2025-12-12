"""Pure functions for emoji sync logic.

This module contains the core business logic as pure functions,
making them easy to test and reason about.
"""

import logging
import re
from typing import Callable

from emoji_bulk_migrator.models import Emoji, SyncResult
from emoji_bulk_migrator.protocols import SlackApiHandler, StorageHandler

logger = logging.getLogger(__name__)


def detect_content_type(filename: str) -> str:
    """Detect content type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    type_map = {
        "png": "image/png",
        "gif": "image/gif",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    return type_map.get(ext, "image/png")

# Characters that are invalid in filenames
INVALID_FILENAME_CHARS = re.compile(r'[:|;]')


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by replacing invalid characters.
    
    Args:
        filename: The original filename.
        
    Returns:
        Sanitized filename with invalid chars replaced by underscores.
    """
    return INVALID_FILENAME_CHARS.sub('_', filename)


def compute_emojis_to_download(
    remote_emojis: list[Emoji],
    local_files: list[str]
) -> list[Emoji]:
    """Determine which emojis need to be downloaded.
    
    Pure function that computes the difference between remote and local.
    
    Args:
        remote_emojis: List of emojis available on the remote workspace.
        local_files: List of filenames already in local storage.
        
    Returns:
        List of emojis that need to be downloaded.
    """
    local_set = {sanitize_filename(f) for f in local_files}
    
    to_download = []
    for emoji in remote_emojis:
        sanitized = sanitize_filename(emoji.filename)
        if sanitized not in local_set:
            to_download.append(emoji)
    
    return to_download


def compute_emojis_to_upload(
    local_files: list[str],
    remote_emojis: list[Emoji]
) -> list[str]:
    """Determine which local files need to be uploaded.
    
    Pure function that computes the difference between local and remote.
    
    Args:
        local_files: List of filenames in local storage.
        remote_emojis: List of emojis already on the remote workspace.
        
    Returns:
        List of filenames that need to be uploaded.
    """
    # Extract just the name part from remote emojis for comparison
    remote_names = {emoji.name for emoji in remote_emojis}
    
    to_upload = []
    for filename in local_files:
        # Extract name without extension
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        if name not in remote_names:
            to_upload.append(filename)
    
    return to_upload


def download_emojis(
    api_handler: SlackApiHandler,
    storage_handler: StorageHandler,
    progress_callback: Callable[[str, int, int], None] | None = None
) -> SyncResult:
    """Download emojis from a Slack workspace to local storage.
    
    Args:
        api_handler: Handler for Slack API operations.
        storage_handler: Handler for local storage operations.
        progress_callback: Optional callback(emoji_name, current, total).
        
    Returns:
        SyncResult with counts of processed, skipped, and failed items.
    """
    result = SyncResult()
    
    # Get current state
    logger.info("Fetching remote emoji list...")
    remote_emojis = api_handler.list_emojis()
    logger.info(f"Found {len(remote_emojis)} custom emojis on remote")
    
    local_files = storage_handler.list_files()
    logger.info(f"Found {len(local_files)} existing local files")
    
    # Compute what needs to be downloaded
    to_download = compute_emojis_to_download(remote_emojis, local_files)
    result.skipped = len(remote_emojis) - len(to_download)
    
    logger.info(f"Need to download {len(to_download)} emojis")
    
    # Download each emoji
    for i, emoji in enumerate(to_download):
        if progress_callback:
            progress_callback(emoji.name, i + 1, len(to_download))
        
        try:
            logger.debug(f"Downloading {emoji.name}...")
            content = api_handler.download_emoji(emoji.url)
            
            filename = sanitize_filename(emoji.filename)
            storage_handler.write_file(filename, content)
            
            result.processed += 1
            logger.info(f"Downloaded: {emoji.name}")
            
        except Exception as e:
            result.failed += 1
            error_msg = f"Failed to download {emoji.name}: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    return result


def upload_emojis(
    api_handler: SlackApiHandler,
    storage_handler: StorageHandler,
    progress_callback: Callable[[str, int, int], None] | None = None
) -> SyncResult:
    """Upload emojis from local storage to a Slack workspace.
    
    Args:
        api_handler: Handler for Slack API operations.
        storage_handler: Handler for local storage operations.
        progress_callback: Optional callback(emoji_name, current, total).
        
    Returns:
        SyncResult with counts of processed, skipped, and failed items.
    """
    result = SyncResult()
    
    # Get current state
    logger.info("Fetching remote emoji list...")
    remote_emojis = api_handler.list_emojis()
    logger.info(f"Found {len(remote_emojis)} custom emojis on remote")
    
    local_files = storage_handler.list_files()
    logger.info(f"Found {len(local_files)} local files")
    
    # Compute what needs to be uploaded
    to_upload = compute_emojis_to_upload(local_files, remote_emojis)
    result.skipped = len(local_files) - len(to_upload)
    
    logger.info(f"Need to upload {len(to_upload)} emojis")
    
    # Upload each emoji
    for i, filename in enumerate(to_upload):
        # Extract emoji name (filename without extension)
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        if progress_callback:
            progress_callback(name, i + 1, len(to_upload))
        
        try:
            logger.debug(f"Uploading {name}...")
            content = storage_handler.read_file(filename)
            content_type = detect_content_type(filename)
            
            api_handler.upload_emoji(name, content, content_type)
            
            result.processed += 1
            logger.info(f"Uploaded: {name}")
            
        except Exception as e:
            result.failed += 1
            error_msg = f"Failed to upload {name}: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    return result


def sync_emojis(
    source_api: SlackApiHandler,
    dest_api: SlackApiHandler,
    storage_handler: StorageHandler,
    download: bool = True,
    upload: bool = True,
    progress_callback: Callable[[str, str, int, int], None] | None = None
) -> tuple[SyncResult | None, SyncResult | None]:
    """Sync emojis from source workspace to destination workspace.
    
    Uses local storage as an intermediary.
    
    Args:
        source_api: Handler for source Slack workspace.
        dest_api: Handler for destination Slack workspace.
        storage_handler: Handler for local storage.
        download: Whether to download from source.
        upload: Whether to upload to destination.
        progress_callback: Optional callback(phase, emoji_name, current, total).
        
    Returns:
        Tuple of (download_result, upload_result), either can be None if skipped.
    """
    download_result = None
    upload_result = None
    
    if download:
        logger.info("=== Download Phase ===")
        download_callback = None
        if progress_callback:
            download_callback = lambda n, c, t: progress_callback("download", n, c, t)
        download_result = download_emojis(source_api, storage_handler, download_callback)
        logger.info(
            f"Download complete: {download_result.processed} downloaded, "
            f"{download_result.skipped} skipped, {download_result.failed} failed"
        )
    
    if upload:
        logger.info("=== Upload Phase ===")
        upload_callback = None
        if progress_callback:
            upload_callback = lambda n, c, t: progress_callback("upload", n, c, t)
        upload_result = upload_emojis(dest_api, storage_handler, upload_callback)
        logger.info(
            f"Upload complete: {upload_result.processed} uploaded, "
            f"{upload_result.skipped} skipped, {upload_result.failed} failed"
        )
    
    return download_result, upload_result
