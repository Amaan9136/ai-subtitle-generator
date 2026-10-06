# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-07

First public release.

### Added

- Captions from audio and video via Groq's hosted Whisper API, saved as `.srt` files, for local files, folders and Google Drive.
- Caption languages: English, Hindi, Urdu, Kannada, Malayalam and Hinglish.
- `FFMPEG_PATH` and `FFPROBE_PATH` settings in `.env`. When empty, FFmpeg and FFprobe are found on `PATH`, so the tool works on Windows, macOS and Linux.
- MIT `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and `CITATION.cff`.
- GitHub issue forms, pull request template, Dependabot config and a CI workflow with a secret scan.

### Security

- Google Drive file names are reduced to a safe base name before download, so a crafted name cannot write outside `drive_downloads/`.
- `token.json` is saved with owner-only permissions.
- `.gitignore` excludes `client_secret*.json`, other `.env.*` files, key files, `.srt` captions and common audio and video files.

[1.0.0]: https://github.com/Amaan9136/ai-subtitle-generator/releases/tag/v1.0.0