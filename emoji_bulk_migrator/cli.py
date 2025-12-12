"""Command-line interface for the emoji sync application."""

import argparse
import logging
import sys
from typing import Optional

from emoji_bulk_migrator.models import ApiProtocol, SlackConfig


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="emoji-sync",
        description="Sync custom emojis between Slack workspaces.",
        epilog="""
Examples:
  # Download emojis from source workspace to local storage
  %(prog)s download --source-workspace mycompany --source-token xoxp-...

  # Upload emojis from local storage to destination workspace  
  %(prog)s upload --dest-workspace othercompany --dest-token xoxp-...

  # Full sync from source to destination
  %(prog)s sync --source-workspace src --source-token xoxp-... \\
                --dest-workspace dest --dest-token xoxp-...

Environment Variables:
  SOURCE_SLACK_WORKSPACE  Source workspace name
  SOURCE_SLACK_TOKEN      Source API token
  SOURCE_SLACK_COOKIE     Source session cookie (for HTTP mode)
  DEST_SLACK_WORKSPACE    Destination workspace name
  DEST_SLACK_TOKEN        Destination API token
  DEST_SLACK_COOKIE       Destination session cookie (for HTTP mode)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    parser.add_argument(
        "--storage-path",
        type=str,
        default="./emojis",
        help="Local directory for emoji storage (default: ./emojis)",
    )
    parser.add_argument(
        "--api-mode",
        type=str,
        choices=["web_api", "http"],
        default="web_api",
        help="API mode: 'web_api' (official SDK) or 'http' (session-based)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download emojis from a Slack workspace to local storage",
    )
    _add_source_args(download_parser)

    # Upload command
    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload emojis from local storage to a Slack workspace",
    )
    _add_dest_args(upload_parser)

    # Sync command (download + upload)
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync emojis from source workspace to destination workspace",
    )
    _add_source_args(sync_parser)
    _add_dest_args(sync_parser)

    # List command (show local files)
    list_parser = subparsers.add_parser(
        "list",
        help="List emojis in local storage",
    )

    return parser


def _add_source_args(parser: argparse.ArgumentParser) -> None:
    """Add source workspace arguments to a parser."""
    group = parser.add_argument_group("Source workspace")
    group.add_argument(
        "--source-workspace",
        type=str,
        help="Source Slack workspace name (or set SOURCE_SLACK_WORKSPACE)",
    )
    group.add_argument(
        "--source-token",
        type=str,
        help="Source API token (or set SOURCE_SLACK_TOKEN)",
    )
    group.add_argument(
        "--source-cookie",
        type=str,
        help="Source session cookie for HTTP mode (or set SOURCE_SLACK_COOKIE)",
    )


def _add_dest_args(parser: argparse.ArgumentParser) -> None:
    """Add destination workspace arguments to a parser."""
    group = parser.add_argument_group("Destination workspace")
    group.add_argument(
        "--dest-workspace",
        type=str,
        help="Destination Slack workspace name (or set DEST_SLACK_WORKSPACE)",
    )
    group.add_argument(
        "--dest-token",
        type=str,
        help="Destination API token (or set DEST_SLACK_TOKEN)",
    )
    group.add_argument(
        "--dest-cookie",
        type=str,
        help="Destination session cookie for HTTP mode (or set DEST_SLACK_COOKIE)",
    )


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_source_config(args: argparse.Namespace) -> SlackConfig:
    """Build source config from args and environment."""
    config = SlackConfig.from_env("SOURCE_")
    
    # Override with command line args if provided
    if hasattr(args, 'source_workspace') and args.source_workspace:
        config = SlackConfig(
            workspace=args.source_workspace,
            token=args.source_token or config.token,
            cookie=args.source_cookie or config.cookie,
        )
    elif hasattr(args, 'source_token') and args.source_token:
        config = SlackConfig(
            workspace=config.workspace,
            token=args.source_token,
            cookie=args.source_cookie or config.cookie,
        )
    
    return config


def get_dest_config(args: argparse.Namespace) -> SlackConfig:
    """Build destination config from args and environment."""
    config = SlackConfig.from_env("DEST_")
    
    # Override with command line args if provided
    if hasattr(args, 'dest_workspace') and args.dest_workspace:
        config = SlackConfig(
            workspace=args.dest_workspace,
            token=args.dest_token or config.token,
            cookie=args.dest_cookie or config.cookie,
        )
    elif hasattr(args, 'dest_token') and args.dest_token:
        config = SlackConfig(
            workspace=config.workspace,
            token=args.dest_token,
            cookie=args.dest_cookie or config.cookie,
        )
    
    return config


def validate_config(config: SlackConfig, name: str) -> bool:
    """Validate that required config fields are present."""
    errors = []
    
    if not config.workspace:
        errors.append(f"{name} workspace is required")
    if not config.token:
        errors.append(f"{name} token is required")
    
    if errors:
        for error in errors:
            logging.error(error)
        return False
    
    return True


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = create_parser()
    return parser.parse_args(args)
