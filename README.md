# Emoji Bulk Migrator

Sync custom emojis between Slack workspaces.

This tool allows you to download custom emojis from one Slack workspace and upload them to another, using local storage as an intermediary. It's useful for:

- Migrating emojis when moving to a new Slack workspace
- Keeping emojis in sync across multiple workspaces
- Backing up custom emojis locally

## Features

- **Download** emojis from a Slack workspace to local storage
- **Upload** emojis from local storage to a Slack workspace
- **Sync** emojis directly between workspaces
- **Incremental sync** - only downloads/uploads new emojis
- **Two API modes**: Official Slack Web API or HTTP-based (for non-admins)

## Requirements

- Python 3.10+
- Access to Slack workspaces with appropriate permissions
- API token with `emoji:read` scope (for downloading)
- API token with `admin.emoji:write` scope (for uploading, requires admin)

## Installation

```bash
# Using pip
pip install -r requirements.txt

# Using poetry
poetry install
```

## Configuration

### Environment Variables

The tool reads configuration from environment variables:

| Variable | Description |
|----------|-------------|
| `SOURCE_SLACK_WORKSPACE` | Source workspace name (e.g., `mycompany`) |
| `SOURCE_SLACK_TOKEN` | Source workspace API token |
| `SOURCE_SLACK_COOKIE` | Source workspace cookie (for HTTP mode) |
| `DEST_SLACK_WORKSPACE` | Destination workspace name |
| `DEST_SLACK_TOKEN` | Destination workspace API token |
| `DEST_SLACK_COOKIE` | Destination workspace cookie (for HTTP mode) |

### Command Line Arguments

All configuration can also be passed via command line arguments (which override environment variables).

## Usage

### Download Emojis

Download all custom emojis from a workspace to local storage:

```bash
# Using environment variables
export SOURCE_SLACK_WORKSPACE=mycompany
export SOURCE_SLACK_TOKEN=xoxp-your-token
python main.py download

# Using command line arguments
python main.py download \
    --source-workspace mycompany \
    --source-token xoxp-your-token \
    --storage-path ./my-emojis
```

### Upload Emojis

Upload emojis from local storage to a workspace:

```bash
# Using environment variables
export DEST_SLACK_WORKSPACE=newcompany
export DEST_SLACK_TOKEN=xoxp-your-token
python main.py upload

# Using command line arguments
python main.py upload \
    --dest-workspace newcompany \
    --dest-token xoxp-your-token
```

### Full Sync

Download from source and upload to destination in one command:

```bash
python main.py sync \
    --source-workspace sourcecompany \
    --source-token xoxp-source-token \
    --dest-workspace destcompany \
    --dest-token xoxp-dest-token
```

### List Local Emojis

See what emojis are stored locally:

```bash
python main.py list --storage-path ./emojis
```

### API Modes

By default, the tool uses the official Slack Web API. If you don't have admin access, you can use HTTP mode with browser session cookies:

```bash
python main.py download \
    --api-mode http \
    --source-workspace mycompany \
    --source-token your-session-token \
    --source-cookie "d=your-session-cookie"
```

### Verbose Output

For debugging, use the `-v` flag:

```bash
python main.py -v download --source-workspace mycompany --source-token xoxp-...
```

## Architecture

The application follows a "Functional Core, Imperative Shell" pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (main.py)                        │
├─────────────────────────────────────────────────────────────┤
│                     Sync Logic (sync.py)                    │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Pure Functions    │    │    Orchestration Logic      │ │
│  │ - compute_to_download│    │ - download_emojis()        │ │
│  │ - compute_to_upload │    │ - upload_emojis()          │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Protocols (protocols.py)                  │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  SlackApiHandler    │    │    StorageHandler           │ │
│  │    (Protocol)       │    │      (Protocol)             │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                       Implementations                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│  │SlackWebApiHdlr│ │SlackHttpHdlr  │ │LocalStorageHdlr   │  │
│  └───────────────┘ └───────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Protocol-based handlers**: Easy to swap implementations and mock for testing
2. **Pure sync functions**: Core logic is stateless and easy to test
3. **Frozen dataclasses**: Immutable data models prevent accidental mutations
4. **Incremental sync**: Avoids re-downloading/uploading existing emojis

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=emoji_bulk_migrator --cov-report=html

# Run specific test file
pytest emoji_bulk_migrator_tests/test_sync.py
```

### Project Structure

```
emoji_bulk_migrator/
├── __init__.py          # Package exports
├── models.py            # Data models (Emoji, SlackConfig, SyncResult)
├── protocols.py         # Handler protocols/interfaces
├── sync.py              # Core sync logic (pure functions)
├── local_storage.py     # Local file storage handler
├── slack_web_api.py     # Slack Web API handler
├── slack_http.py        # Slack HTTP handler
└── cli.py               # Command line interface

emoji_bulk_migrator_tests/
├── conftest.py          # Pytest fixtures
├── test_models.py       # Model tests
├── test_sync.py         # Sync logic tests
├── test_local_storage.py # Storage handler tests
├── test_handlers.py     # API handler tests
└── test_cli.py          # CLI tests
```

## Obtaining Slack Tokens

### For Web API Mode (Recommended for Admins)

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app or use an existing one
3. Add the following OAuth scopes:
   - `emoji:read` - for downloading emojis
   - `admin.emoji:write` - for uploading emojis (requires admin)
4. Install the app to your workspace
5. Copy the User OAuth Token (starts with `xoxp-`)

### For HTTP Mode (Non-Admins)

1. Open your Slack workspace in a browser
2. Open Developer Tools (F12)
3. Go to the Network tab
4. Navigate to the emoji customization page
5. Look for requests to `emoji.adminList` or similar
6. Copy the `token` from the request payload
7. Copy the `Cookie` header value

## Notes

- The tool skips emoji aliases (emojis that reference other emojis)
- Files with special characters in names (`:`, `;`) are sanitized
- The tool is idempotent - running it multiple times won't duplicate emojis
- Rate limiting is handled automatically with exponential backoff

## License

MIT License

## Credits

Inspired by [ExportImportSlackEmoji](https://github.com/Firenza/ExportImportSlackEmoji)
