# Auto Caption Generator

Generates `.srt` subtitle files from audio and video using Groq's hosted Whisper API. No model downloads, no GPU needed. It handles single files, whole folders, and Google Drive files or folders, and can write captions in English, Hindi, Urdu, Kannada, Malayalam or Hinglish.

## Features

- Audio and video input, including WhatsApp `.amr` voice notes
- Local files, local folders, Google Drive files and Google Drive folders
- You choose the spoken language and the caption language every run
- Typed and language-suffixed output (`name-auto-translate-hing.srt`, `name-auto-transcribe-hi.srt`) so transcripts and translations are both kept and never overwrite each other
- Files that already have a caption for the chosen language are skipped automatically
- Long audio is split into 10-minute chunks and the timestamps are stitched back together

## Requirements

- Python 3.9+
- FFmpeg and FFprobe installed (the script expects `C:\ffmpeg\bin\ffmpeg.exe` and `C:\ffmpeg\bin\ffprobe.exe`, change `FFMPEG` and `FFPROBE` at the top of `auto_caption_generator.py` if yours are elsewhere)
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

3. Copy `.env.example` to `.env` and add your key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=whisper-large-v3
GROQ_LLM_MODEL=openai/gpt-oss-120b
SOURCE_LANG=auto
TARGET_LANG=hing
```

`.env` is in `.gitignore`, so your key is not committed.

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
Caption language (what the .srt should contain) [en/hi/ur/kn/ml/hing] (Enter = hing):
Enter file/folder path or Google Drive link/ID:
```

Press Enter on the first two to use the defaults from `.env`. For the path you can give:

| Input | Example |
|---|---|
| Local audio or video file | `D:\Recordings\AUD-20200303-WA0034.amr` |
| Local folder (every audio/video file directly inside it) | `D:\0 AMAAN MAIN\` |
| Google Drive file link | `https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrSt/view` |
| Google Drive folder link | `https://drive.google.com/drive/folders/1XyZ...` |
| Bare Drive file or folder ID | `1AbCdEfGhIjKlMnOpQrSt` |

Paths with spaces work, with or without quotes. Folders are read one level deep, not into subfolders.

## Language codes

| Code | Language | As audio language | As caption language |
|---|---|---|---|
| `auto` | Let Whisper detect the language | Yes | No |
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

Examples:

- Malayalam audio, `hi` captions: Malayalam is transcribed, then translated into Hindi in Devanagari script
- Malayalam audio, `hing` captions: Malayalam is transcribed, then the meaning is written as Hindi in English letters, for example "kya haal hai"
- Hindi audio, `hing` captions: the Hindi is written in English letters

Hinglish here means the meaning rendered as Hindi in English letters with English words kept as they are. It is not a letter-by-letter spelling of Malayalam or Kannada. Spelling is chosen by the AI model, so the same word can be spelled slightly differently between lines.

### How it works

1. FFmpeg extracts the audio in 10-minute mono mp3 chunks.
2. Each chunk goes to Groq's Whisper (`transcriptions` with your audio language, or `translations` when the captions are English and the audio is not).
3. If the caption language needs conversion, the transcript is sent to a Groq text model in batches of 25 lines and returned with the original timings.
4. The transcript is saved as `<name>-<audio language>-transcribe-<spoken language>.srt` before conversion, then the converted captions as `<name>-<audio language>-translate-<caption language>.srt`. If a batch fails to convert, no translation file is written, a warning is printed, and the next run reuses the saved transcript and only repeats the conversion.

### Accuracy notes

- Whisper handles one language per request. If you force one language on audio that mixes several, the other languages will come out badly. Use `auto` for mixed audio, and set the real language (not a guess) when the audio is a single language.
- Malayalam and Kannada are the least reliable, and mixed passages are weaker than single-language ones. Review those captions.
- Translated captions go through two steps, so a transcription mistake carries into the translation.

## Output and skipping

Every output is named `<file name>-<src>-<type>-<target>.srt`, where src is the audio language you picked (`auto`, `hi`, ...), the type is `translate` or `transcribe` and target is the caption language, for example `AUD-20200303-WA0034-auto-translate-hing.srt` and `AUD-20200303-WA0034-auto-transcribe-hi.srt`.

- **Transcribe and translate:** both files are kept side by side in the same folder.
- **Same language, or English audio with Hinglish captions:** one `transcribe` file named with the caption language.
- **Non-English audio with English captions:** one `translation` file, made by Whisper in a single step.

- **Local files:** the `.srt` is saved next to the source file.
- **Google Drive files:** the `.srt` is saved in `output_captions/` next to the script. The downloaded copy is deleted after captioning.

A file is skipped when a caption for the same language already exists:

| Source | Checked for `<name>-<src>-translate-<lang>.srt` or `<name>-<src>-transcribe-<lang>.srt` |
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
| `GROQ_LLM_MODEL` | `openai/gpt-oss-120b` | Text model used for translation and Hinglish. If it is not available on your account the script picks `qwen/qwen3.8-27b` automatically |
| `SOURCE_LANG` | `auto` | Default for the audio language prompt |
| `TARGET_LANG` | `hing` | Default for the caption language prompt |

Set at the top of the script:

| Constant | Default | Meaning |
|---|---|---|
| `FFMPEG`, `FFPROBE` | `C:\ffmpeg\bin\...` | Paths to FFmpeg and FFprobe |
| `AUDIO_CHUNK_SECONDS` | `600` | Length of each upload chunk |
| `AUDIO_BITRATE_FOR_STT` | `64k` | Bitrate of the uploaded audio |
| `LLM_BATCH_SIZE` | `25` | Caption lines converted per request |

## Troubleshooting

- **FFmpeg/FFprobe were not found:** fix `FFMPEG` and `FFPROBE` at the top of the script.
- **GROQ_API_KEY is not set:** check that `.env` is next to the script and contains your key.
- **Groq API error or rate limit:** the free tier has request limits. The error is printed and that file is skipped. Wait a bit and run again. Files that finished are skipped on the rerun.
- **No speech detected:** no `.srt` is written for that file.
- **Could not read video duration:** FFprobe could not read the file. Check that it plays.
- **A file keeps being skipped:** a `<name>-<src>-translate-<lang>.srt` or `<name>-<src>-transcribe-<lang>.srt` for that language exists in the folder or in `output_captions/`. Delete it to redo the file.
- **Model not found (404):** Groq retired `openai/gpt-oss-120b` on 2026-08-16. Remove the old `GROQ_LLM_MODEL` line from `.env` or set it to `openai/gpt-oss-120b`.

## Project files

| File | Purpose |
|---|---|
| `auto_caption_generator.py` | The tool |
| `.env.example` | Template for `.env` |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Keeps keys, tokens and generated files out of git |