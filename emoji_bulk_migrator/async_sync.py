"""Async versions of sync operations with progress reporting.

Provides high-level async functions for downloading and uploading
emojis with concurrent execution and progress callbacks.
"""

import asyncio
import logging
from typing import Callable, Optional, Awaitable

from emoji_bulk_migrator.models import Emoji, SyncResult
from emoji_bulk_migrator.protocols import StorageHandler
from emoji_bulk_migrator.async_slack import AsyncSlackHandler
from emoji_bulk_migrator.sync import compute_emojis_to_download, compute_emojis_to_upload, sanitize_filename

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


async def async_download_emojis(
    api_handler: AsyncSlackHandler,
    storage_handler: StorageHandler,
    progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None,
) -> SyncResult:
    """Download emojis from a Slack workspace to local storage (async).
    
    Args:
        api_handler: Async handler for Slack API operations.
        storage_handler: Handler for local storage operations.
        progress_callback: Optional async callback(emoji_name, current, total).
        
    Returns:
        SyncResult with counts of processed, skipped, and failed items.
    """
    result = SyncResult()
    
    # Get current state
    logger.info("Fetching remote emoji list...")
    remote_emojis = await api_handler.list_emojis()
    logger.info(f"Found {len(remote_emojis)} custom emojis on remote")
    
    local_files = storage_handler.list_files()
    logger.info(f"Found {len(local_files)} existing local files")
    
    # Compute what needs to be downloaded
    to_download = compute_emojis_to_download(remote_emojis, local_files)
    result.skipped = len(remote_emojis) - len(to_download)
    
    if not to_download:
        logger.info("No new emojis to download")
        return result
    
    logger.info(f"Downloading {len(to_download)} emojis...")
    
    # Build URL to emoji mapping
    url_to_emoji = {emoji.url: emoji for emoji in to_download}
    urls = list(url_to_emoji.keys())
    
    # Progress wrapper
    async def on_progress(completed: int, total: int):
        if progress_callback and completed <= len(to_download):
            # Get the emoji name for the most recently completed
            emoji = to_download[completed - 1] if completed > 0 else to_download[0]
            await progress_callback(emoji.name, completed, total)
    
    # Download all concurrently
    download_results = await api_handler.download_many(urls, on_progress)
    
    # Process results
    for url, content_or_error in download_results:
        emoji = url_to_emoji[url]
        
        if isinstance(content_or_error, Exception):
            result.failed += 1
            error_msg = f"Failed to download {emoji.name}: {content_or_error}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        else:
            filename = sanitize_filename(emoji.filename)
            storage_handler.write_file(filename, content_or_error)
            result.processed += 1
            logger.debug(f"Downloaded: {emoji.name}")
    
    return result


async def async_upload_emojis(
    api_handler: AsyncSlackHandler,
    storage_handler: StorageHandler,
    progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None,
) -> SyncResult:
    """Upload emojis from local storage to a Slack workspace (async).
    
    Args:
        api_handler: Async handler for Slack API operations.
        storage_handler: Handler for local storage operations.
        progress_callback: Optional async callback(emoji_name, current, total).
        
    Returns:
        SyncResult with counts of processed, skipped, and failed items.
    """
    result = SyncResult()
    
    # Get current state
    logger.info("Fetching remote emoji list...")
    remote_emojis = await api_handler.list_emojis()
    logger.info(f"Found {len(remote_emojis)} custom emojis on remote")
    
    local_files = storage_handler.list_files()
    logger.info(f"Found {len(local_files)} local files")
    
    # Compute what needs to be uploaded
    to_upload = compute_emojis_to_upload(local_files, remote_emojis)
    result.skipped = len(local_files) - len(to_upload)
    
    if not to_upload:
        logger.info("No new emojis to upload")
        return result
    
    logger.info(f"Uploading {len(to_upload)} emojis...")
    
    # Prepare upload items: (name, data, content_type)
    upload_items = []
    for filename in to_upload:
        name = filename.rsplit(".", 1)[0] if "." in filename else filename
        content = storage_handler.read_file(filename)
        content_type = detect_content_type(filename)
        upload_items.append((name, content, content_type))
    
    # Progress wrapper
    async def on_progress(completed: int, total: int):
        if progress_callback and completed <= len(to_upload):
            name = upload_items[completed - 1][0] if completed > 0 else upload_items[0][0]
            await progress_callback(name, completed, total)
    
    # Upload all concurrently
    upload_results = await api_handler.upload_many(upload_items, on_progress)
    
    # Process results
    for name, error in upload_results:
        if error is not None:
            result.failed += 1
            error_msg = f"Failed to upload {name}: {error}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        else:
            result.processed += 1
            logger.debug(f"Uploaded: {name}")
    
    return result


async def async_sync_emojis(
    source_api: AsyncSlackHandler,
    dest_api: AsyncSlackHandler,
    storage_handler: StorageHandler,
    download: bool = True,
    upload: bool = True,
    progress_callback: Optional[Callable[[str, str, int, int], Awaitable[None]]] = None,
) -> tuple[SyncResult | None, SyncResult | None]:
    """Sync emojis from source workspace to destination workspace (async).
    
    Args:
        source_api: Async handler for source Slack workspace.
        dest_api: Async handler for destination Slack workspace.
        storage_handler: Handler for local storage.
        download: Whether to download from source.
        upload: Whether to upload to destination.
        progress_callback: Optional async callback(phase, emoji_name, current, total).
        
    Returns:
        Tuple of (download_result, upload_result), either can be None if skipped.
    """
    download_result = None
    upload_result = None
    
    if download:
        logger.info("=== Download Phase ===")
        
        async def download_progress(name, current, total):
            if progress_callback:
                await progress_callback("download", name, current, total)
        
        download_result = await async_download_emojis(
            source_api, storage_handler, download_progress
        )
        logger.info(
            f"Download complete: {download_result.processed} downloaded, "
            f"{download_result.skipped} skipped, {download_result.failed} failed"
        )
    
    if upload:
        logger.info("=== Upload Phase ===")
        
        async def upload_progress(name, current, total):
            if progress_callback:
                await progress_callback("upload", name, current, total)
        
        upload_result = await async_upload_emojis(
            dest_api, storage_handler, upload_progress
        )
        logger.info(
            f"Upload complete: {upload_result.processed} uploaded, "
            f"{upload_result.skipped} skipped, {upload_result.failed} failed"
        )
    
    return download_result, upload_result
