# 📋 Changelog

All notable changes to this project will be documented in this file.

---

## [0.3.0] - 2024-12-12

### ✨ Added
- **Async support** with configurable concurrency (`-c` flag)
- **Semaphore-based throttling** to respect rate limits
- **Exponential backoff retry** for failed requests
- **`count` command** to check remote emoji count without downloading
- **Short option aliases** (`-sw`, `-st`, `-dw`, `-dt`)
- **Environment variable support** for all configuration

### 🔄 Changed
- **Complete architecture redesign** using "Functional Core, Imperative Shell" pattern
- **Migrated CLI from argparse to Click** for better UX
- **Protocol-based handlers** for easy swapping of implementations
- **Immutable dataclasses** for all data models

### 🐛 Fixed
- **`SlackWebApiHandler.upload_emoji`** was completely broken (ignored image data)
- **Missing content-type detection** in upload flow
- **Duplicate `-p` flag** in CLI arguments

### 🗑️ Removed
- Old handlers with hardcoded workspace URLs
- Config files with embedded credentials
- Unused async/sync mixed code

---

## [0.2.0] - 2024-XX-XX

### Added
- Initial Click CLI migration
- Poetry dependency management
- Basic test suite

---

## [0.1.0] - Initial Release

### Added
- Basic emoji download functionality
- Basic emoji upload functionality
- Local file storage
- HTTP and Web API handlers (partial)

---

## Legend

| Emoji | Type |
|-------|------|
| ✨ | New features |
| 🔄 | Changes |
| 🐛 | Bug fixes |
| 🗑️ | Removed |
| 🔒 | Security |
| 📝 | Documentation |
