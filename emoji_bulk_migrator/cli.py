"""Command-line interface for the emoji sync application using Click."""

import logging
import sys
from typing import Optional

import click

from emoji_bulk_migrator.models import SlackConfig
from emoji_bulk_migrator.local_storage import LocalStorageHandler
from emoji_bulk_migrator.slack_web_api import SlackWebApiHandler
from emoji_bulk_migrator.slack_http import SlackHttpHandler
from emoji_bulk_migrator.sync import download_emojis, upload_emojis

logger = logging.getLogger(__name__)


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


def create_api_handler(config: SlackConfig, api_mode: str):
    """Create the appropriate API handler based on mode."""
    if api_mode == "http":
        return SlackHttpHandler(config)
    return SlackWebApiHandler(config)


def validate_config(config: SlackConfig, name: str) -> bool:
    """Validate that required config fields are present."""
    errors = []
    if not config.workspace:
        errors.append(f"{name} workspace is required")
    if not config.token:
        errors.append(f"{name} token is required")
    
    if errors:
        for error in errors:
            click.echo(click.style(f"Error: {error}", fg="red"), err=True)
        return False
    return True


class Config:
    """Holds configuration passed through Click context."""
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.storage_path = "./emojis"
        self.api_mode = "web_api"


pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("-q", "--quiet", is_flag=True, help="Suppress all output except errors")
@click.option(
    "--storage-path",
    default="./emojis",
    envvar="EMOJI_STORAGE_PATH",
    type=click.Path(),
    help="Local directory for emoji storage"
)
@click.option(
    "--api-mode",
    type=click.Choice(["web_api", "http"]),
    default="web_api",
    envvar="SLACK_API_MODE",
    help="API mode: 'web_api' (official SDK) or 'http' (session-based)"
)
@click.version_option(version="0.2.0", prog_name="emoji-sync")
@click.pass_context
def cli(ctx, verbose, quiet, storage_path, api_mode):
    """Sync custom emojis between Slack workspaces.
    
    \b
    Examples:
      # Download emojis from source workspace
      emoji-sync download --source-workspace mycompany --source-token xoxp-...
    
      # Upload emojis to destination workspace
      emoji-sync upload --dest-workspace newcompany --dest-token xoxp-...
    
      # Full sync between workspaces
      emoji-sync sync --source-workspace src --source-token xoxp-src \\
                      --dest-workspace dest --dest-token xoxp-dest
    
    \b
    Environment Variables:
      SOURCE_SLACK_WORKSPACE  Source workspace name
      SOURCE_SLACK_TOKEN      Source API token
      DEST_SLACK_WORKSPACE    Destination workspace name
      DEST_SLACK_TOKEN        Destination API token
    """
    ctx.ensure_object(Config)
    ctx.obj.verbose = verbose
    ctx.obj.quiet = quiet
    ctx.obj.storage_path = storage_path
    ctx.obj.api_mode = api_mode
    
    setup_logging(verbose, quiet)
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("--source-workspace", "-sw", envvar="SOURCE_SLACK_WORKSPACE", help="Source Slack workspace name")
@click.option("--source-token", "-st", envvar="SOURCE_SLACK_TOKEN", help="Source API token")
@click.option("--source-cookie", "-sc", envvar="SOURCE_SLACK_COOKIE", help="Source session cookie (for HTTP mode)")
@pass_config
def download(config, source_workspace, source_token, source_cookie):
    """Download emojis from a Slack workspace to local storage."""
    slack_config = SlackConfig(
        workspace=source_workspace or "",
        token=source_token or "",
        cookie=source_cookie
    )
    
    if not validate_config(slack_config, "Source"):
        raise SystemExit(1)
    
    click.echo(f"Downloading emojis from workspace: {slack_config.workspace}")
    
    storage = LocalStorageHandler(config.storage_path)
    api_handler = create_api_handler(slack_config, config.api_mode)
    
    try:
        result = download_emojis(api_handler, storage)
        
        click.echo()
        click.echo(click.style("Download complete!", fg="green", bold=True))
        click.echo(f"  Downloaded: {result.processed}")
        click.echo(f"  Skipped:    {result.skipped}")
        
        if result.failed > 0:
            click.echo(click.style(f"  Failed:     {result.failed}", fg="red"))
            for error in result.errors:
                click.echo(click.style(f"    - {error}", fg="red"), err=True)
            raise SystemExit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if config.verbose:
            logger.exception("Full traceback:")
        raise SystemExit(1)


@cli.command()
@click.option("--dest-workspace", "-dw", envvar="DEST_SLACK_WORKSPACE", help="Destination Slack workspace name")
@click.option("--dest-token", "-dt", envvar="DEST_SLACK_TOKEN", help="Destination API token")
@click.option("--dest-cookie", "-dc", envvar="DEST_SLACK_COOKIE", help="Destination session cookie (for HTTP mode)")
@pass_config
def upload(config, dest_workspace, dest_token, dest_cookie):
    """Upload emojis from local storage to a Slack workspace."""
    slack_config = SlackConfig(
        workspace=dest_workspace or "",
        token=dest_token or "",
        cookie=dest_cookie
    )
    
    if not validate_config(slack_config, "Destination"):
        raise SystemExit(1)
    
    click.echo(f"Uploading emojis to workspace: {slack_config.workspace}")
    
    storage = LocalStorageHandler(config.storage_path)
    api_handler = create_api_handler(slack_config, config.api_mode)
    
    try:
        result = upload_emojis(api_handler, storage)
        
        click.echo()
        click.echo(click.style("Upload complete!", fg="green", bold=True))
        click.echo(f"  Uploaded:   {result.processed}")
        click.echo(f"  Skipped:    {result.skipped}")
        
        if result.failed > 0:
            click.echo(click.style(f"  Failed:     {result.failed}", fg="red"))
            for error in result.errors:
                click.echo(click.style(f"    - {error}", fg="red"), err=True)
            raise SystemExit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if config.verbose:
            logger.exception("Full traceback:")
        raise SystemExit(1)


@cli.command()
@click.option("--source-workspace", "-sw", envvar="SOURCE_SLACK_WORKSPACE", help="Source Slack workspace name")
@click.option("--source-token", "-st", envvar="SOURCE_SLACK_TOKEN", help="Source API token")
@click.option("--source-cookie", "-sc", envvar="SOURCE_SLACK_COOKIE", help="Source session cookie (for HTTP mode)")
@click.option("--dest-workspace", "-dw", envvar="DEST_SLACK_WORKSPACE", help="Destination Slack workspace name")
@click.option("--dest-token", "-dt", envvar="DEST_SLACK_TOKEN", help="Destination API token")
@click.option("--dest-cookie", "-dc", envvar="DEST_SLACK_COOKIE", help="Destination session cookie (for HTTP mode)")
@pass_config
def sync(config, source_workspace, source_token, source_cookie, dest_workspace, dest_token, dest_cookie):
    """Sync emojis from source workspace to destination workspace.
    
    Downloads emojis from the source workspace to local storage,
    then uploads them to the destination workspace.
    """
    source_config = SlackConfig(
        workspace=source_workspace or "",
        token=source_token or "",
        cookie=source_cookie
    )
    dest_config = SlackConfig(
        workspace=dest_workspace or "",
        token=dest_token or "",
        cookie=dest_cookie
    )
    
    if not validate_config(source_config, "Source"):
        raise SystemExit(1)
    if not validate_config(dest_config, "Destination"):
        raise SystemExit(1)
    
    storage = LocalStorageHandler(config.storage_path)
    source_api = create_api_handler(source_config, config.api_mode)
    dest_api = create_api_handler(dest_config, config.api_mode)
    
    try:
        # Download phase
        click.echo(click.style(f"=== Downloading from {source_config.workspace} ===", bold=True))
        download_result = download_emojis(source_api, storage)
        click.echo(f"Downloaded: {download_result.processed}, Skipped: {download_result.skipped}")
        
        click.echo()
        
        # Upload phase
        click.echo(click.style(f"=== Uploading to {dest_config.workspace} ===", bold=True))
        upload_result = upload_emojis(dest_api, storage)
        click.echo(f"Uploaded: {upload_result.processed}, Skipped: {upload_result.skipped}")
        
        click.echo()
        click.echo(click.style("=== Sync Complete ===", fg="green", bold=True))
        
        total_errors = download_result.failed + upload_result.failed
        if total_errors > 0:
            click.echo(click.style(f"Completed with {total_errors} errors", fg="yellow"))
            raise SystemExit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if config.verbose:
            logger.exception("Full traceback:")
        raise SystemExit(1)


@cli.command("list")
@pass_config
def list_emojis(config):
    """List emojis in local storage."""
    storage = LocalStorageHandler(config.storage_path)
    files = storage.list_files()
    
    if not files:
        click.echo(f"No emojis found in {config.storage_path}")
        return
    
    click.echo(f"Found {len(files)} emojis in {config.storage_path}:")
    click.echo()
    
    for filename in sorted(files):
        click.echo(f"  {filename}")


@cli.command()
@click.option("--source-workspace", "-sw", envvar="SOURCE_SLACK_WORKSPACE", help="Source Slack workspace name")
@click.option("--source-token", "-st", envvar="SOURCE_SLACK_TOKEN", help="Source API token")
@click.option("--source-cookie", "-sc", envvar="SOURCE_SLACK_COOKIE", help="Source session cookie (for HTTP mode)")
@pass_config
def count(config, source_workspace, source_token, source_cookie):
    """Count emojis in a remote workspace (without downloading)."""
    slack_config = SlackConfig(
        workspace=source_workspace or "",
        token=source_token or "",
        cookie=source_cookie
    )
    
    if not validate_config(slack_config, "Source"):
        raise SystemExit(1)
    
    api_handler = create_api_handler(slack_config, config.api_mode)
    
    try:
        click.echo(f"Fetching emoji list from {slack_config.workspace}...")
        emojis = api_handler.list_emojis()
        
        click.echo()
        click.echo(click.style(f"Found {len(emojis)} custom emojis", fg="green", bold=True))
        
        # Show extension breakdown
        extensions = {}
        for emoji in emojis:
            ext = emoji.extension.lower()
            extensions[ext] = extensions.get(ext, 0) + 1
        
        if extensions:
            click.echo()
            click.echo("By type:")
            for ext, count in sorted(extensions.items(), key=lambda x: -x[1]):
                click.echo(f"  {ext}: {count}")
                
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if config.verbose:
            logger.exception("Full traceback:")
        raise SystemExit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
