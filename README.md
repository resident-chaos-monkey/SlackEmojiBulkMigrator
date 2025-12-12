# 🎭 Slack Emoji Sync

> **Sync custom emojis between Slack workspaces with ease**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-106%20passing-brightgreen.svg)](#-testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📥 **Download** | Fetch all custom emojis from a Slack workspace |
| 📤 **Upload** | Push emojis to a destination workspace |
| 🔄 **Sync** | Full two-way sync between workspaces |
| ⚡ **Fast Mode** | Concurrent downloads/uploads (up to 10x faster) |
| 🛡️ **Safe Mode** | Sequential processing to avoid rate limits |
| 🔁 **Incremental** | Only syncs new emojis (skips existing) |
| 🔄 **Retry Logic** | Automatic retry with exponential backoff |

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/resident-chaos-monkey/slack-emoji-sync.git
cd slack-emoji-sync

# Install dependencies (choose one)
pip install -r requirements.txt    # pip
poetry install                      # poetry
```

### Basic Usage

```bash
# Download emojis from a workspace
python main.py download -sw mycompany -st xoxp-your-token

# Upload emojis to another workspace
python main.py upload -dw newcompany -dt xoxp-dest-token

# Full sync between workspaces
python main.py sync \
    -sw source-workspace -st xoxp-source-token \
    -dw dest-workspace -dt xoxp-dest-token
```

---

## 📖 Commands

### 📥 Download

Download all custom emojis from a Slack workspace to local storage.

```bash
python main.py download --source-workspace WORKSPACE --source-token TOKEN
```

| Option | Short | Environment Variable | Description |
|--------|-------|---------------------|-------------|
| `--source-workspace` | `-sw` | `SOURCE_SLACK_WORKSPACE` | Workspace name |
| `--source-token` | `-st` | `SOURCE_SLACK_TOKEN` | API token |
| `--source-cookie` | `-sc` | `SOURCE_SLACK_COOKIE` | Session cookie (HTTP mode) |

### 📤 Upload

Upload emojis from local storage to a Slack workspace.

```bash
python main.py upload --dest-workspace WORKSPACE --dest-token TOKEN
```

| Option | Short | Environment Variable | Description |
|--------|-------|---------------------|-------------|
| `--dest-workspace` | `-dw` | `DEST_SLACK_WORKSPACE` | Workspace name |
| `--dest-token` | `-dt` | `DEST_SLACK_TOKEN` | API token |
| `--dest-cookie` | `-dc` | `DEST_SLACK_COOKIE` | Session cookie (HTTP mode) |

### 🔄 Sync

Download from source and upload to destination in one command.

```bash
python main.py sync \
    -sw source -st xoxp-source \
    -dw dest -dt xoxp-dest
```

### 📋 List

List emojis stored locally.

```bash
python main.py list
```

### 🔢 Count

Count emojis in a remote workspace without downloading.

```bash
python main.py count -sw myworkspace -st xoxp-token
```

---

## ⚡ Concurrency

Control download/upload speed with the `-c` / `--concurrency` flag:

```bash
# Sequential (safest - no rate limiting issues)
python main.py -c 1 download -sw workspace -st token

# Moderate (good balance)
python main.py -c 5 download -sw workspace -st token

# Fast (may hit rate limits, has retry logic)
python main.py -c 10 download -sw workspace -st token
```

| Level | Speed | Rate Limit Risk | Recommended For |
|-------|-------|-----------------|-----------------|
| `-c 1` | 1x | 🟢 None | Uploads, debugging |
| `-c 5` | 5x | 🟡 Low | General use |
| `-c 10` | 10x | 🟠 Medium | Large downloads |
| `-c 20` | 20x | 🔴 High | Bulk operations |

---

## 🔐 Authentication

### Option 1: Environment Variables (Recommended)

```bash
export SOURCE_SLACK_WORKSPACE=mycompany
export SOURCE_SLACK_TOKEN=xoxp-1234567890-...
export DEST_SLACK_WORKSPACE=newcompany
export DEST_SLACK_TOKEN=xoxp-0987654321-...

# Now run without arguments
python main.py sync
```

### Option 2: Command Line Arguments

```bash
python main.py download \
    --source-workspace mycompany \
    --source-token xoxp-1234567890-...
```

### Getting Your Token

#### For Workspace Admins (Web API)

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app or select existing
3. Add OAuth scopes:
   - `emoji:read` — for downloading
   - `admin.emoji:write` — for uploading
4. Install to workspace
5. Copy the **User OAuth Token** (`xoxp-...`)

#### For Non-Admins (HTTP Mode)

1. Open Slack in browser
2. Open Developer Tools → Network tab
3. Go to **Customize Workspace** → **Emoji**
4. Find a request to `emoji.adminList`
5. Copy the `token` from the request body
6. Copy the `Cookie` header

```bash
python main.py --api-mode http download \
    -sw workspace \
    -st xoxe-token \
    -sc "d=xoxd-..."
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (Click)                             │
│                        main.py / cli.py                         │
├─────────────────────────────────────────────────────────────────┤
│                      Sync Logic (sync.py)                       │
│  ┌──────────────────────┐    ┌────────────────────────────────┐ │
│  │    Pure Functions    │    │     Orchestration Logic        │ │
│  │ • compute_to_download│    │ • download_emojis()            │ │
│  │ • compute_to_upload  │    │ • upload_emojis()              │ │
│  │ • sanitize_filename  │    │ • sync_emojis()                │ │
│  └──────────────────────┘    └────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                   Protocols (protocols.py)                      │
│         SlackApiHandler          StorageHandler                 │
├─────────────────────────────────────────────────────────────────┤
│                      Implementations                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ WebAPI      │ │ HTTP        │ │ Async       │ │ Local     │ │
│  │ Handler     │ │ Handler     │ │ Handler     │ │ Storage   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

- 🧩 **Functional Core, Imperative Shell** — Pure functions for logic, classes for I/O
- 🔌 **Protocol-based Handlers** — Easily swap implementations
- 🧊 **Immutable Data** — Frozen dataclasses prevent bugs
- ✅ **Incremental Sync** — Never re-downloads or re-uploads existing emojis

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=emoji_bulk_migrator

# Run specific test file
pytest emoji_bulk_migrator_tests/test_sync.py -v
```

**106 tests** covering:
- ✅ Data models
- ✅ Sync logic (pure functions)
- ✅ Local storage handler
- ✅ API handlers
- ✅ Async operations
- ✅ CLI commands

---

## 📁 Project Structure

```
slack-emoji-sync/
├── 📄 main.py                    # Entry point
├── 📄 pyproject.toml             # Dependencies & config
├── 📄 requirements.txt           # Pip dependencies
│
├── 📁 emoji_bulk_migrator/       # Main package
│   ├── 📄 models.py              # Data models
│   ├── 📄 protocols.py           # Handler interfaces
│   ├── 📄 sync.py                # Core sync logic
│   ├── 📄 local_storage.py       # File storage
│   ├── 📄 slack_web_api.py       # Web API handler
│   ├── 📄 slack_http.py          # HTTP handler
│   ├── 📄 async_slack.py         # Async handler
│   ├── 📄 async_sync.py          # Async operations
│   └── 📄 cli.py                 # CLI commands
│
└── 📁 emoji_bulk_migrator_tests/ # Test suite
    ├── 📄 test_models.py
    ├── 📄 test_sync.py
    ├── 📄 test_handlers.py
    └── ...
```

---

## 📝 Example Output

```
$ python main.py -c 10 download -sw mycompany -st xoxp-...

Mode: Concurrent (concurrency=10)
Downloading emojis from workspace: mycompany
Fetching remote emoji list...
Found 6269 custom emojis on remote
Found 6250 existing local files
Downloading 19 emojis...

Download complete!
  Downloaded: 19
  Skipped:    6250
```

---

## ⚠️ Notes

- 🔄 **Idempotent** — Running multiple times won't duplicate emojis
- 🏷️ **Aliases Skipped** — Emoji aliases are not downloaded
- 🧹 **Filename Sanitization** — Special characters (`:`, `|`, `;`) are replaced
- ⏱️ **Rate Limits** — Use `-c 1` if you encounter 429 errors

---

## 🙏 Credits

Inspired by [ExportImportSlackEmoji](https://github.com/Firenza/ExportImportSlackEmoji)

---

## 📄 License

MIT License - feel free to use, modify, and distribute.
