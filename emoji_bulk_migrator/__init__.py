"""Emoji Bulk Migrator - Sync custom emojis between Slack workspaces.

This package provides tools to download custom emojis from one Slack
workspace and upload them to another, using local storage as an
intermediary.

Example usage:
    from emoji_bulk_migrator import (
        SlackWebApiHandler,
        LocalStorageHandler,
        download_emojis,
        upload_emojis,
    )
    from emoji_bulk_migrator.models import SlackConfig
    
    # Configure handlers
    source_config = SlackConfig(workspace="source", token="xoxp-...")
    source_api = SlackWebApiHandler(source_config)
    storage = LocalStorageHandler("./emojis")
    
    # Download emojis
    result = download_emojis(source_api, storage)
    print(f"Downloaded {result.processed} emojis")
"""

from emoji_bulk_migrator.models import (
    ApiProtocol,
    Emoji,
    SlackConfig,
    SyncResult,
)
from emoji_bulk_migrator.protocols import (
    SlackApiHandler,
    StorageHandler,
)
from emoji_bulk_migrator.local_storage import LocalStorageHandler
from emoji_bulk_migrator.slack_web_api import SlackWebApiHandler
from emoji_bulk_migrator.slack_http import SlackHttpHandler
from emoji_bulk_migrator.sync import (
    compute_emojis_to_download,
    compute_emojis_to_upload,
    download_emojis,
    upload_emojis,
    sync_emojis,
    sanitize_filename,
)

__version__ = "0.2.0"

__all__ = [
    # Models
    "ApiProtocol",
    "Emoji",
    "SlackConfig",
    "SyncResult",
    # Protocols
    "SlackApiHandler",
    "StorageHandler",
    # Handlers
    "LocalStorageHandler",
    "SlackWebApiHandler",
    "SlackHttpHandler",
    # Functions
    "compute_emojis_to_download",
    "compute_emojis_to_upload",
    "download_emojis",
    "upload_emojis",
    "sync_emojis",
    "sanitize_filename",
]
