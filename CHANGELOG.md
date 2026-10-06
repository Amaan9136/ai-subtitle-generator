# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `FFMPEG_PATH` and `FFPROBE_PATH` settings in `.env`. When empty, FFmpeg and FFprobe are found on `PATH`.
- MIT `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and `CITATION.cff`.
- GitHub issue forms, pull request template, Dependabot config and a CI workflow with a secret scan.
- README sections for quick start, FFmpeg setup, privacy and security, contributing and license.

### Changed

- FFmpeg and FFprobe are no longer hardcoded to `C:\ffmpeg\bin`, so the tool works on macOS and Linux.
- `.gitignore` now also excludes `client_secret*.json`, other `.env.*` files, key files, `.srt` captions and common audio and video files.

### Fixed

- Google Drive file names are reduced to a safe base name before download, so a crafted name cannot write outside `drive_downloads/`.
- `token.json` is saved with owner-only permissions.
- The text model fallback now uses `qwen/qwen3.6-27b`, the Groq model ID, instead of a non-existent `qwen/qwen3.8-27b`.
- The README no longer says `openai/gpt-oss-120b` was retired, and the 404 troubleshooting entry is accurate.
