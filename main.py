#!/usr/bin/env python3
"""Entry point for the emoji sync application."""

import logging
import sys

from emoji_bulk_migrator.cli import (
    parse_args,
    setup_logging,
    get_source_config,
    get_dest_config,
    validate_config,
)
from emoji_bulk_migrator.local_storage import LocalStorageHandler
from emoji_bulk_migrator.slack_web_api import SlackWebApiHandler
from emoji_bulk_migrator.slack_http import SlackHttpHandler
from emoji_bulk_migrator.sync import download_emojis, upload_emojis

logger = logging.getLogger(__name__)


def create_api_handler(config, api_mode: str):
    """Create the appropriate API handler based on mode."""
    if api_mode == "http":
        return SlackHttpHandler(config)
    else:
        return SlackWebApiHandler(config)


def cmd_download(args) -> int:
    """Handle the download command."""
    source_config = get_source_config(args)
    
    if not validate_config(source_config, "Source"):
        return 1
    
    logger.info(f"Downloading emojis from workspace: {source_config.workspace}")
    
    storage = LocalStorageHandler(args.storage_path)
    source_api = create_api_handler(source_config, args.api_mode)
    
    result = download_emojis(source_api, storage)
    
    logger.info(f"Download complete!")
    logger.info(f"  Downloaded: {result.processed}")
    logger.info(f"  Skipped:    {result.skipped}")
    logger.info(f"  Failed:     {result.failed}")
    
    if result.errors:
        for error in result.errors:
            logger.error(f"  - {error}")
    
    return 0 if result.failed == 0 else 1


def cmd_upload(args) -> int:
    """Handle the upload command."""
    dest_config = get_dest_config(args)
    
    if not validate_config(dest_config, "Destination"):
        return 1
    
    logger.info(f"Uploading emojis to workspace: {dest_config.workspace}")
    
    storage = LocalStorageHandler(args.storage_path)
    dest_api = create_api_handler(dest_config, args.api_mode)
    
    result = upload_emojis(dest_api, storage)
    
    logger.info(f"Upload complete!")
    logger.info(f"  Uploaded:   {result.processed}")
    logger.info(f"  Skipped:    {result.skipped}")
    logger.info(f"  Failed:     {result.failed}")
    
    if result.errors:
        for error in result.errors:
            logger.error(f"  - {error}")
    
    return 0 if result.failed == 0 else 1


def cmd_sync(args) -> int:
    """Handle the sync command."""
    source_config = get_source_config(args)
    dest_config = get_dest_config(args)
    
    if not validate_config(source_config, "Source"):
        return 1
    if not validate_config(dest_config, "Destination"):
        return 1
    
    storage = LocalStorageHandler(args.storage_path)
    source_api = create_api_handler(source_config, args.api_mode)
    dest_api = create_api_handler(dest_config, args.api_mode)
    
    # Download phase
    logger.info(f"=== Downloading from {source_config.workspace} ===")
    download_result = download_emojis(source_api, storage)
    logger.info(f"Downloaded: {download_result.processed}, Skipped: {download_result.skipped}")
    
    # Upload phase
    logger.info(f"=== Uploading to {dest_config.workspace} ===")
    upload_result = upload_emojis(dest_api, storage)
    logger.info(f"Uploaded: {upload_result.processed}, Skipped: {upload_result.skipped}")
    
    # Summary
    logger.info("=== Sync Complete ===")
    total_errors = download_result.failed + upload_result.failed
    
    if total_errors > 0:
        logger.warning(f"Completed with {total_errors} errors")
        return 1
    
    return 0


def cmd_list(args) -> int:
    """Handle the list command."""
    storage = LocalStorageHandler(args.storage_path)
    files = storage.list_files()
    
    if not files:
        logger.info(f"No emojis found in {args.storage_path}")
        return 0
    
    logger.info(f"Found {len(files)} emojis in {args.storage_path}:")
    for filename in sorted(files):
        print(f"  {filename}")
    
    return 0


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    
    if args.command is None:
        # No command specified, show help
        parse_args(["--help"])
        return 1
    
    commands = {
        "download": cmd_download,
        "upload": cmd_upload,
        "sync": cmd_sync,
        "list": cmd_list,
    }
    
    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Error: {e}")
            if args.verbose:
                logger.exception("Full traceback:")
            return 1
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
