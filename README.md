# Auto Caption Generator

[![CI](https://github.com/Amaan9136/ai-subtitle-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Amaan9136/ai-subtitle-generator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Generates `.srt` subtitle files from audio and video using Groq's hosted Whisper API. No model downloads and no GPU needed, except the optional phoneme model for `auto` captions. It handles single files, whole folders, and Google Drive files or folders, and can write captions in English, Hindi, Urdu, Kannada, Malayalam or Hinglish, or write every word as it sounds in English letters with no translation (`auto` caption language).

## Quick start

```bash
git clone https://github.com/Amaan9136/ai-subtitle-generator.git
cd ai-subtitle-generator
pip install -r requirements.txt
cp .env.example .env
python auto_caption_generator.py
```

On Windows PowerShell use `Copy-Item .env.example .env` instead of `cp`. Put your Groq key in `.env` before running, and make sure FFmpeg is installed. The full setup is below.

## Features

- Audio and video input, including WhatsApp `.amr` voice notes
- Local files, local folders, Google Drive files and Google Drive folders
- You choose the spoken language and the caption language every run
- `auto` as the caption language gives sound-to-sound, word-for-word captions in English letters, whatever language is spoken, using a local phoneme model
- Typed and language-suffixed output (`name-auto-translate-hing.srt`, `name-auto-transcribe-hi.srt`, `name-auto-transliterate-auto.srt`) so transcripts and translations are both kept and never overwrite each other
- Files that already have a caption for the chosen language are skipped automatically
- Long audio is split into 10-minute chunks and the timestamps are stitched back together

## Requirements

- Python 3.10+
- FFmpeg and FFprobe installed, either on your `PATH` or set with `FFMPEG_PATH` and `FFPROBE_PATH` in `.env` (see [FFmpeg setup](#ffmpeg-setup))
- A free Groq API key: https://console.groq.com/keys
- Google Drive credentials, only if you use Drive links (see below)

## Setup

1. Install the dependencies:

```powershell
pip install -r requirements.txt
```

2. Optional, for a live upload progress bar:

```powershell
pip install requests-toolbelt
```

3. Optional, only for `auto` (sound-to-sound) captions. This installs PyTorch and Transformers:

```powershell
pip install -r requirements-auto.txt
```

4. Copy `.env.example` to `.env` and add your key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=whisper-large-v3
GROQ_LLM_MODEL=openai/gpt-oss-120b
FFMPEG_PATH=
FFPROBE_PATH=
SOURCE_LANG=auto
TARGET_LANG=hing
```

`.env` is in `.gitignore`, so your key is not committed. Never share your `.env` file or paste its contents in an issue.

### FFmpeg setup

The script uses `FFMPEG_PATH` and `FFPROBE_PATH` from `.env` when they are set. When they are empty it looks for `ffmpeg` and `ffprobe` on your `PATH`.

Install FFmpeg from https://ffmpeg.org/download.html and check that both commands work:

```bash
ffmpeg -version
ffprobe -version
```

If both print a version, you need no extra setup. If FFmpeg is installed somewhere that is not on your `PATH`, put the full paths in `.env`:

```env
FFMPEG_PATH=C:/ffmpeg/bin/ffmpeg.exe
FFPROBE_PATH=C:/ffmpeg/bin/ffprobe.exe
```

On Windows use forward slashes and no quotes. Double quotes turn `\f` and `\b` in a path into control characters and break it.

### Google Drive setup (only for Drive links)

1. Go to https://console.cloud.google.com/ and create or select a project
2. Enable the **Google Drive API**
3. Set up the OAuth consent screen (External is fine) and add your own Google account as a test user
4. Create an **OAuth client ID** with application type **Desktop app**
5. Download the JSON, rename it `credentials.json` and put it next to `auto_caption_generator.py`

The first Drive run opens a browser to approve read-only access. A `token.json` is then saved so you are not asked again. Both files are in `.gitignore`.

## Running

```powershell
python auto_caption_generator.py
```

You are asked three things, in this order:

```
Audio language (what is spoken) [auto/en/hi/ur/kn/ml] (Enter = auto):
Caption language (what the .srt should contain) [en/hi/ur/kn/ml/hing/auto] (Enter = hing):
Enter file/folder path or Google Drive link/ID:
```

Press Enter on the first two to use the defaults from `.env`. For the path you can give:

| Input | Example |
|---|---|
| Local audio or video file | `D:\Recordings\AUD-20200303-WA0034.amr` |
| Local folder (every audio/video file directly inside it) | `D:\Recordings\` |
| Google Drive file link | `https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrSt/view` |
| Google Drive folder link | `https://drive.google.com/drive/folders/1XyZ...` |
| Bare Drive file or folder ID | `1AbCdEfGhIjKlMnOpQrSt` |

Paths with spaces work, with or without quotes. Folders are read one level deep, not into subfolders.

## Language codes

| Code | Language | As audio language | As caption language |
|---|---|---|---|
| `auto` | Audio: Whisper detects the language. Captions: every word written as it sounds in English letters, no translation | Yes | Yes |
| `en` | English | Yes | Yes |
| `hi` | Hindi (Devanagari script) | Yes | Yes |
| `ur` | Urdu | Yes | Yes |
| `kn` | Kannada | Yes | Yes |
| `ml` | Malayalam | Yes | Yes |
| `hing` | Hinglish (Hindi in English letters) | No | Yes |

`ka` is accepted as `kn` and `ma` as `ml`. File names use the standard `kn` and `ml`. `hinglish` is accepted as `hing`.

## What each language choice does

| Audio | Captions | What happens |
|---|---|---|
| English | English | Transcribed as is |
| English | Hinglish | Transcribed, English text left as is (no conversion) |
| English | Hindi, Urdu, Kannada or Malayalam | Transcribed, then translated |
| Any other language, or `auto` | English | Translated to English by Whisper |
| Any other language, or `auto` | Hinglish, Hindi, Urdu, Kannada or Malayalam | Transcribed, then translated by the text model |
| Hindi, Urdu, Kannada or Malayalam | The same language | Transcribed as is |
| Any language, or `auto` | `auto` | Transcribed literally, then written word for word in English letters as it sounds. No translation |

Examples:

- Malayalam audio, `hi` captions: Malayalam is transcribed, then translated into Hindi in Devanagari script
- Malayalam audio, `hing` captions: Malayalam is transcribed, then the meaning is written as Hindi in English letters, for example "kya haal hai"
- Hindi audio, `hing` captions: the Hindi is written in English letters

### Sound-to-sound captions (`auto` caption language)

Use `auto` for both prompts to get a word-for-word transcript in English letters, whatever language is spoken. The text is written from how each line sounds, not from what a language model thinks was said.

1. Groq's Whisper runs with `temperature` set to `0.2` and a casual prompt full of filler words and contractions (`LITERAL_PROMPT`), so it writes down what it hears instead of correcting grammar. Your `CUSTOM_PROMPT` is added after it. This gives the line timings and a rough text.
2. A local Wav2Vec 2.0 phoneme model (`facebook/wav2vec2-lv-60-espeak-cv-ft`) listens to each line again and writes the real phonemes (IPA), in any language.
3. The Groq text model turns the phonemes into plain English letters, using the rough Whisper text only to find word boundaries. It does not translate.

The phoneme model is the only local download. It is about 1.3 GB (the model has 300 million parameters, but the weights file is far bigger than 300 MB). The script looks for it, in this order:

1. The folder in `PHONEME_MODEL_PATH`, if you set it
2. The hidden `models/` folder next to the script
3. Your Hugging Face cache

If none has it, it is downloaded once into `models/`. That folder is hidden: on Windows it gets the Hidden attribute, on macOS and Linux it is named `.models/`. It is in `.gitignore`. A GPU is used when PyTorch can see one, otherwise the CPU, which is slower.

It needs the extra libraries once:

```powershell
pip install -r requirements-auto.txt
```

Without them, `auto` captions still work but only from the Whisper text, and a message says so. The spelling is chosen by the text model, so the same sound can be spelled slightly differently between lines.

Hinglish here means the meaning rendered as Hindi in English letters with English words kept as they are. It is not a letter-by-letter spelling of Malayalam or Kannada. Spelling is chosen by the AI model, so the same word can be spelled slightly differently between lines.

### How it works

1. FFmpeg extracts the audio in 10-minute mono mp3 chunks.
2. Each chunk goes to Groq's Whisper (`transcriptions` with your audio language, or `translations` when the captions are English and the audio is not).
3. If the caption language needs conversion, the transcript is sent to a Groq text model in batches of 25 lines and returned with the original timings. For `auto` captions step 2 uses literal transcription (`temperature` 0.2 and `LITERAL_PROMPT`) and this step only transliterates into English letters.
4. The transcript is saved as `<name>-<audio language>-transcribe-<spoken language>.srt` before conversion, then the converted captions as `<name>-<audio language>-translate-<caption language>.srt`. With `auto` captions the raw transcript is not saved, and the single output is `<name>-<audio language>-transliterate-auto.srt`. If a batch fails to convert, no translation file is written, a warning is printed, and the next run reuses the saved transcript and only repeats the conversion.

### Accuracy notes

- Whisper handles one language per request. If you force one language on audio that mixes several, the other languages will come out badly. Use `auto` for mixed audio, and set the real language (not a guess) when the audio is a single language.
- Malayalam and Kannada are the least reliable, and mixed passages are weaker than single-language ones. Review those captions.
- Translated captions go through two steps, so a transcription mistake carries into the translation.
- `auto` captions follow the sound of each word, so non-English speech is not translated and the spelling can vary. The phoneme model can mishear noisy audio, and it is not as good as Whisper at telling real words from sounds.

## Output and skipping

Every output is named `<file name>-<src>-<type>-<target>.srt`, where src is the audio language you picked (`auto`, `hi`, ...), the type is `translate`, `transcribe` or `transliterate` and target is the caption language, for example `AUD-20200303-WA0034-auto-translate-hing.srt` and `AUD-20200303-WA0034-auto-transcribe-hi.srt`.

- **Transcribe and translate:** both files are kept side by side in the same folder.
- **Same language, or English audio with Hinglish captions:** one `transcribe` file named with the caption language.
- **`auto` captions:** one `transliterate` file, for example `AUD-20200303-WA0034-auto-transliterate-auto.srt`.
- **Non-English audio with English captions:** one `translation` file, made by Whisper in a single step.

- **Local files:** the `.srt` is saved next to the source file.
- **Google Drive files:** the `.srt` is saved in `output_captions/` next to the script. The downloaded copy is deleted after captioning.

A file is skipped when a caption for the same language already exists:

| Source | Checked for `<name>-<src>-translate-<lang>.srt`, `<name>-<src>-transcribe-<lang>.srt` or `<name>-<src>-transliterate-<lang>.srt` |
|---|---|
| Local file or folder | The folder you gave and `output_captions/` |
| Google Drive folder | The Drive folder and `output_captions/` |
| Single Drive file | `output_captions/` |

Skipping is per language. An existing `AUD-1-auto-translate-en.srt` does not stop `AUD-1-auto-translate-hing.srt` from being created. Older caption files named `name-hing.srt` or just `name.srt` are not counted and those files will be processed again.

## Supported formats

- **Video:** mp4, mov, mkv, avi, webm, m4v, flv, wmv, 3gp, 3g2, mpg, mpeg, mts, m2ts, ogv, vob, asf
- **Audio:** mp3, wav, m4a, aac, ogg, oga, opus, flac, amr, awb, wma, aiff, aif, 3ga, caf, mka, ac3, mp2, weba, m4b

The lists are `VIDEO_EXTENSIONS` and `AUDIO_EXTENSIONS` at the top of the script.

## Configuration

Set in `.env`:

| Setting | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | none | Your Groq key (required) |
| `GROQ_MODEL` | `whisper-large-v3` | Speech model. `whisper-large-v3-turbo` is faster but slightly less accurate |
| `GROQ_LLM_MODEL` | `openai/gpt-oss-120b` | Text model used for translation, Hinglish and sound-based `auto` captions. If it is not available on your account the script falls back to `qwen/qwen3.6-27b` (a Groq preview model) and then `openai/gpt-oss-20b` |
| `SOURCE_LANG` | `auto` | Default for the audio language prompt |
| `TARGET_LANG` | `hing` | Default for the caption language prompt. Set `auto` for sound-to-sound captions |
| `CUSTOM_PROMPT` | empty | Default hint about the audio, e.g. mixed languages or names |
| `PHONEME_MODEL` | `facebook/wav2vec2-lv-60-espeak-cv-ft` | Hugging Face phoneme model used for `auto` captions |
| `PHONEME_MODEL_PATH` | empty | Folder of a phoneme model you already have. When empty, `models/` and the Hugging Face cache are checked, then it is downloaded |
| `FFMPEG_PATH` | empty | Full path to `ffmpeg`. When empty, `ffmpeg` is looked up on your `PATH` |
| `FFPROBE_PATH` | empty | Full path to `ffprobe`. When empty, `ffprobe` is looked up on your `PATH` |

Set at the top of the script:

| Constant | Default | Meaning |
|---|---|---|
| `AUDIO_CHUNK_SECONDS` | `600` | Length of each upload chunk |
| `AUDIO_BITRATE_FOR_STT` | `64k` | Bitrate of the uploaded audio |
| `LLM_BATCH_SIZE` | `25` | Caption lines converted per request |
| `LITERAL_TEMPERATURE` | `0.2` | Whisper temperature for `auto` captions. Keep it at or below `0.6` |
| `LITERAL_PROMPT` | casual filler-word string | Whisper prompt for `auto` captions that stops grammar correction |

## Troubleshooting

- **FFmpeg/FFprobe were not found:** install FFmpeg and add it to your `PATH`, or set `FFMPEG_PATH` and `FFPROBE_PATH` in `.env` (see [FFmpeg setup](#ffmpeg-setup)).
- **GROQ_API_KEY is not set:** check that `.env` is next to the script and contains your key.
- **Groq API error or rate limit:** the free tier has request limits. The error is printed and that file is skipped. Wait a bit and run again. Files that finished are skipped on the rerun.
- **No speech detected:** no `.srt` is written for that file.
- **Could not read video duration:** FFprobe could not read the file. Check that it plays.
- **A file keeps being skipped:** a `<name>-<src>-translate-<lang>.srt`, `<name>-<src>-transcribe-<lang>.srt` or `<name>-<src>-transliterate-<lang>.srt` for that language exists in the folder or in `output_captions/`. Delete it to redo the file.
- **The phoneme model libraries are missing:** run `pip install -r requirements-auto.txt`. Until then `auto` captions use the Whisper text only.
- **The phoneme model download fails:** check your internet connection and free disk space (about 1.3 GB), then run again. Or download the model yourself and set `PHONEME_MODEL_PATH` to its folder.
- **`auto` captions are slow:** the phoneme model runs on your machine. A GPU with CUDA PyTorch is much faster than the CPU.
- **Model not found (404):** the model in `GROQ_LLM_MODEL` is not available on your Groq account. Groq retires models from time to time, see https://console.groq.com/docs/deprecations. Remove the `GROQ_LLM_MODEL` line from `.env` to use the default, or set it to a model your account can use.

## Project files

| File | Purpose |
|---|---|
| `auto_caption_generator.py` | The tool |
| `.env.example` | Template for `.env` |
| `requirements.txt` | Python dependencies |
| `requirements-auto.txt` | Extra dependencies for `auto` sound-to-sound captions |
| `.gitignore` | Keeps keys, tokens, recordings and generated files out of git |
| `LICENSE` | MIT license |
| `CONTRIBUTING.md` | How to report bugs, suggest features and send pull requests |
| `CODE_OF_CONDUCT.md` | Community rules |
| `SECURITY.md` | How to report a vulnerability privately |
| `CHANGELOG.md` | Notable changes between versions |
| `CITATION.cff` | Citation metadata for the GitHub "Cite this repository" button |
| `.github/` | CI workflow, Dependabot config, issue and pull request templates |

## Privacy and security

- Your audio is sent to Groq for transcription, and transcripts (and, for `auto` captions, the phonemes read locally from your audio) are sent to a Groq text model when conversion is needed. The audio itself is only processed locally by the phoneme model, never uploaded for that step. Read Groq's terms and data policy before captioning private or sensitive recordings.
- Google Drive access is read-only. Files are downloaded to `drive_downloads/` and deleted after each file is captioned.
- `credentials.json` and `token.json` stay on your machine. Treat them like passwords and never commit or share them.
- This project sends no analytics or telemetry. The only network calls go to Groq and, if you use Drive, Google.
- To report a security problem, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Contributing

Bug reports, ideas and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first, and please follow the [Code of Conduct](CODE_OF_CONDUCT.md). If the project is useful to you, a star on GitHub helps other people find it.

## License

Released under the [MIT License](LICENSE).

Created by [Amaan Mohammed Khalander](https://github.com/Amaan9136).

This project is not affiliated with or endorsed by Groq, Google or the FFmpeg project. Caption output comes from AI models and can contain mistakes, so review it before publishing.