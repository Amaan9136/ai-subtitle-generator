# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- The text conversion step (translation, Hinglish and `auto` captions) now uses the Ollama cloud model `gpt-oss:20b` instead of a Groq text model. Groq is only used for speech-to-text. Set `OLLAMA_API_KEY_1` and optionally `OLLAMA_LLM_MODEL` in `.env`. `GROQ_LLM_MODEL` and the fallback models are removed.
- Several keys per service: `GROQ_API_KEY_1`, `GROQ_API_KEY_2`, ... and `OLLAMA_API_KEY_1`, `OLLAMA_API_KEY_2`, ... When a key hits a rate limit the script switches to the next key, and waits only when every key is limited.
- Rate limits: 429 replies wait for the `retry-after` time (up to 15 minutes) without using up the retries, and speech-to-text uploads retry up to 7 times.

### Fixed

- Ollama keys rejected with 401 or 403 are skipped in favor of the next key, and a single rejected key now shows a clear message. Quotes and spaces around Ollama keys in `.env` are ignored.

## [1.0.1] - 2026-10-07

### Added

- `auto` caption language for sound-to-sound, word-for-word captions in English letters, whatever language is spoken. Whisper runs with `temperature` 0.2 and a literal filler-word prompt for the timings, a local Wav2Vec 2.0 phoneme model reads the actual sounds of each line, and the Groq text model writes them in English letters without translating. Output is saved as `<name>-<src>-transliterate-auto.srt`.
- Local phoneme model (`facebook/wav2vec2-lv-60-espeak-cv-ft`, about 1.3 GB). It is looked for in `PHONEME_MODEL_PATH`, the hidden `models/` folder and the Hugging Face cache, and downloaded once into `models/` (hidden on Windows, `.models/` on macOS and Linux) when missing.
- `requirements-auto.txt` with the extra libraries for `auto` captions, and `PHONEME_MODEL` and `PHONEME_MODEL_PATH` settings.
- `models/` and `.models/` added to `.gitignore`.
- `LITERAL_PROMPT` and `LITERAL_TEMPERATURE` constants.

[1.0.1]: https://github.com/Amaan9136/ai-subtitle-generator/releases/tag/v1.0.1

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