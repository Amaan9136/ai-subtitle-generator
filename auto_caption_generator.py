import os
import re
import json
import sys
import time
import shutil
import subprocess
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)
try:
    import requests
except ImportError:
    print("requests is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)
try:
    # Optional - only needed to show a real byte-by-byte progress bar while
    # uploading audio chunks to Groq. Without it, uploads still work fine,
    # they just show a plain "uploading..." line instead of a moving bar.
    from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
    HAS_UPLOAD_PROGRESS = True
except ImportError:
    HAS_UPLOAD_PROGRESS = False
# ─────────────────────────────────────────────────────────────────────────────
# FFmpeg configuration
# ─────────────────────────────────────────────────────────────────────────────
FFMPEG = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.getenv("FFPROBE_PATH") or shutil.which("ffprobe") or "ffprobe"
# ─────────────────────────────────────────────────────────────────────────────
# Folders
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_captions"     # final .srt files land here
DOWNLOAD_DIR = BASE_DIR / "drive_downloads"   # local copies of files pulled from Google Drive (temporary - cleaned up after each video)
TEMP_DIR = BASE_DIR / "caption_temp"          # scratch space for extracted audio chunks
# ─────────────────────────────────────────────────────────────────────────────
# Speech-to-text configuration - Groq's hosted Whisper API (free tier, no local
# model download, no local storage used for weights). Get a free key at:
# https://console.groq.com/keys  and put it in your .env file as GROQ_API_KEY.
# ─────────────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "whisper-large-v3")     # or "whisper-large-v3-turbo" (faster, still free tier)
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
LLM_FALLBACK_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"]
RESOLVED_LLM_MODEL = None
DEFAULT_SOURCE_LANG = os.getenv("SOURCE_LANG", "auto")
DEFAULT_TARGET_LANG = os.getenv("TARGET_LANG", "hing")
CUSTOM_PROMPT = os.getenv("CUSTOM_PROMPT", "")
LITERAL_PROMPT = "Umm, uh, let's see... so like, reference code, standard accent, dunno, gonna, standard, 'cause, yeah."
LITERAL_TEMPERATURE = 0.2
PHONEME_MODEL = os.getenv("PHONEME_MODEL", "facebook/wav2vec2-lv-60-espeak-cv-ft")
MODELS_DIR = BASE_DIR / ("models" if os.name == "nt" else ".models")
PHONEME_DIR = MODELS_DIR / PHONEME_MODEL.split("/")[-1]
PHONEME_STATE = None
GROQ_API_BASE = "https://api.groq.com/openai/v1/audio"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_TIMEOUT_SECONDS = 300
LLM_BATCH_SIZE = 25
LLM_MAX_RETRIES = 3
LLM_TIMEOUT_SECONDS = 60
LLM_MAX_COMPLETION_TOKENS = 8192
# Groq's free tier caps uploads at 25MB per file. We keep chunks tiny and safe
# by re-encoding audio to a small mono/low-bitrate mp3 and splitting long
# videos into fixed-length chunks before uploading each one.
AUDIO_CHUNK_SECONDS = 600     # 10 minutes per upload chunk
AUDIO_BITRATE_FOR_STT = "64k"  # small mono mp3 - plenty for speech recognition
# ─────────────────────────────────────────────────────────────────────────────
# Google Drive configuration
# ─────────────────────────────────────────────────────────────────────────────
# 1. Go to https://console.cloud.google.com/ -> create/select a project
# 2. Enable the "Google Drive API"
# 3. Configure the OAuth consent screen (External is fine, add yourself as a test user)
# 4. Create OAuth client ID credentials -> Application type: "Desktop app"
# 5. Download the JSON and save it next to this script as credentials.json
GOOGLE_CREDENTIALS_FILE = str(BASE_DIR / "credentials.json")   # OAuth client secret downloaded from Google Cloud Console
GOOGLE_TOKEN_FILE = str(BASE_DIR / "token.json")               # created automatically after the first successful login
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".3gp", ".3g2", ".mpg", ".mpeg", ".mts", ".m2ts", ".ogv", ".vob", ".asf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac", ".amr", ".awb", ".wma", ".aiff", ".aif", ".3ga", ".caf", ".mka", ".ac3", ".mp2", ".weba", ".m4b"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "ur": "Urdu", "kn": "Kannada", "ml": "Malayalam", "hing": "Hinglish", "auto": "Auto (sound-based, English letters)"}
LANGUAGE_CODES = {name.lower(): code for code, name in LANGUAGE_NAMES.items()}
SRT_KINDS = ("translate", "transcribe", "transliterate")
LANGUAGE_ALIASES = {"ka": "kn", "ma": "ml", "hinglish": "hing"}
SOURCE_OPTIONS = ["auto", "en", "hi", "ur", "kn", "ml"]
TARGET_OPTIONS = ["en", "hi", "ur", "kn", "ml", "hing", "auto"]
# ─────────────────────────────────────────────────────────────────────────────
# Small shared helpers (same style as the rest of the project)
# ─────────────────────────────────────────────────────────────────────────────
def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
def format_size(size):
    return f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
def print_progress_bar(percent, prefix="", suffix="", bar_width=30):
    percent = max(0.0, min(100.0, percent))
    filled = int(bar_width * percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\r{prefix} [{bar}] {percent:6.2f}% {suffix}", end="", flush=True)
def get_duration(path):
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    duration_text = result.stdout.strip()
    if not duration_text:
        raise ValueError("FFprobe returned an empty duration.")
    return float(duration_text)
def is_media(path):
    return Path(path).suffix.lower() in MEDIA_EXTENSIONS
def srt_name(stem, src, kind, lang):
    return f"{stem}-{src}-{kind}-{lang}.srt"
def srt_regex(stem, lang=None, kind=None):
    return re.compile(rf"{re.escape(stem)}-[^-]+-({kind or '|'.join(SRT_KINDS)})-{re.escape(lang) if lang else '[^-]+'}\.srt", re.I)
def srt_exists(stem, lang, folder=None):
    return any(srt_regex(stem, lang).fullmatch(p.name) for d in (OUTPUT_DIR, folder) if d and d.is_dir() for p in d.iterdir())
def find_transcript(stem, folder):
    return next((p for d in (OUTPUT_DIR, folder) if d.is_dir() for p in sorted(d.iterdir()) if srt_regex(stem, None, "transcribe").fullmatch(p.name)), None)
def parse_srt_time(value):
    hours, minutes, rest = value.strip().split(":")
    secs, ms = rest.replace(".", ",").split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(ms) / 1000
def read_srt(srt_path):
    segments = []
    for block in re.split(r"\r?\n\s*\r?\n", srt_path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            start, end = lines[1].split("-->")
            segments.append((parse_srt_time(start), parse_srt_time(end), " ".join(line.strip() for line in lines[2:]).strip()))
    return segments
def ask_language(label, default, options):
    while True:
        value = input(f"{label} [{'/'.join(options)}] (Enter = {default}): ").strip().lower() or default
        value = LANGUAGE_ALIASES.get(value, value)
        if value in options:
            return value
        print(f"  '{value}' is not supported. Choose one of: {', '.join(options)}")
# ─────────────────────────────────────────────────────────────────────────────
# Step 1: resolve the input into a local video file
#   - a local file path            -> used as-is
#   - a local folder path          -> every video inside is queued
#   - a Google Drive file link/ID  -> downloaded to DOWNLOAD_DIR
#   - a Google Drive folder link   -> every video inside is downloaded and queued
# ─────────────────────────────────────────────────────────────────────────────
DRIVE_HOST_PATTERN = re.compile(r"drive\.google\.com|docs\.google\.com")
DRIVE_ID_PATTERNS = [
    re.compile(r"/d/([a-zA-Z0-9_-]{10,})"),
    re.compile(r"[?&]id=([a-zA-Z0-9_-]{10,})"),
    re.compile(r"/folders/([a-zA-Z0-9_-]{10,})"),
]
def looks_like_drive_input(text):
    return bool(DRIVE_HOST_PATTERN.search(text)) or re.fullmatch(r"[a-zA-Z0-9_-]{20,}", text) is not None
def extract_drive_id(text):
    for pattern in DRIVE_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", text):
        return text
    raise ValueError(f"Could not find a Google Drive file/folder ID in: {text}")
def get_drive_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\nGoogle Drive libraries are not installed. Run:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    creds = None
    token_path = Path(GOOGLE_TOKEN_FILE)
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), DRIVE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(GOOGLE_CREDENTIALS_FILE).is_file():
                print(f"\n{GOOGLE_CREDENTIALS_FILE} was not found.")
                print("Download OAuth client credentials (Desktop app type) from")
                print("https://console.cloud.google.com/apis/credentials")
                print(f"and save them as {GOOGLE_CREDENTIALS_FILE} next to this script.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(token_path, 0o600)
    return build("drive", "v3", credentials=creds)
def drive_get_metadata(service, file_id):
    return service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
def download_drive_file(service, file_id, dest_dir):
    from googleapiclient.http import MediaIoBaseDownload
    import io
    metadata = drive_get_metadata(service, file_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / (Path(metadata["name"].replace("\\", "/")).name.lstrip(".") or file_id)
    request = service.files().get_media(fileId=file_id)
    buffer = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(buffer, request)
    print(f"\nDownloading from Google Drive: {metadata['name']}")
    done = False
    start_time = time.time()
    while not done:
        status, done = downloader.next_chunk()
        if status:
            percent = status.progress() * 100
            elapsed = time.time() - start_time
            downloaded = format_size(int(status.progress() * status.total_size)) if status.total_size else format_size(status.resumable_progress)
            total = format_size(status.total_size) if status.total_size else "?"
            print_progress_bar(percent, prefix="  downloading", suffix=f"| {downloaded}/{total} | {format_time(elapsed)} elapsed")
    buffer.close()
    print_progress_bar(100, prefix="  downloading", suffix="| done" + " " * 10)
    print()
    return dest_path
def list_drive_folder_files(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=query, spaces="drive", fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results
def resolve_inputs(raw_input_text, target_lang):
    """Returns a list of (local Path, was_downloaded_from_drive: bool) tuples ready to be captioned."""
    text = raw_input_text.strip().strip('"')
    if looks_like_drive_input(text):
        drive_id = extract_drive_id(text)
        service = get_drive_service()
        metadata = drive_get_metadata(service, drive_id)
        if metadata["mimeType"] == "application/vnd.google-apps.folder":
            files = list_drive_folder_files(service, drive_id)
            drive_names = {f["name"].lower() for f in files}
            media = sorted((f for f in files if is_media(f["name"])), key=lambda f: int(f.get("size") or 0))
            videos = [f for f in media if not any(srt_regex(Path(f["name"]).stem, target_lang).fullmatch(name) for name in drive_names) and not srt_exists(Path(f["name"]).stem, target_lang)]
            if not media:
                print("No audio or video files were found in that Google Drive folder.")
            elif len(videos) < len(media):
                print(f"Skipping {len(media) - len(videos)} file(s) that already have a -{target_lang}.srt.")
            return [(download_drive_file(service, video["id"], DOWNLOAD_DIR), True) for video in videos]
        if srt_exists(Path(metadata["name"]).stem, target_lang):
            print(f"Skipping {metadata['name']} - a -{target_lang}.srt already exists.")
            return []
        return [(download_drive_file(service, drive_id, DOWNLOAD_DIR), True)]
    local_path = Path(text)
    if local_path.is_dir():
        media = sorted((p for p in local_path.iterdir() if p.is_file() and is_media(p)), key=lambda p: (p.stat().st_size, p.name.lower()))
        videos = [p for p in media if not srt_exists(p.stem, target_lang, local_path)]
        if not media:
            print(f"No audio or video files were found in: {local_path}")
        elif len(videos) < len(media):
            print(f"Skipping {len(media) - len(videos)} file(s) that already have a -{target_lang}.srt.")
        return [(video, False) for video in videos]
    if local_path.is_file():
        if srt_exists(local_path.stem, target_lang, local_path.parent):
            print(f"Skipping {local_path.name} - a -{target_lang}.srt already exists.")
            return []
        return [(local_path, False)]
    print(f"Path not found and not a recognizable Google Drive link/ID: {text}")
    return []
# ─────────────────────────────────────────────────────────────────────────────
# Step 2: transcribe with Groq's hosted Whisper API (online, no model download)
# ─────────────────────────────────────────────────────────────────────────────
def extract_audio_chunk(video_path, start_seconds, chunk_duration, out_path, progress_label=""):
    command = [
        FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(start_seconds), "-t", str(chunk_duration),
        "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "libmp3lame", "-b:a", AUDIO_BITRATE_FOR_STT,
        "-progress", "pipe:1", "-nostats", str(out_path),
    ]
    process = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    current = 0.0
    start_time = time.time()
    log = []
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        if line.startswith("out_time_ms="):
            try:
                current = int(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                pass
        elif line == "progress=end":
            current = chunk_duration
        else:
            if not re.match(r"\w+=", line):
                log.append(line)
            continue
        percent = (current / chunk_duration * 100) if chunk_duration > 0 else 100
        elapsed = time.time() - start_time
        print_progress_bar(percent, prefix=f"  {progress_label} extracting audio",
                            suffix=f"| {format_time(elapsed)} elapsed")
    process.wait()
    stderr_output = "\n".join(log[-10:])
    print_progress_bar(100, prefix=f"  {progress_label} extracting audio", suffix="| done" + " " * 10)
    print()
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to extract audio: {stderr_output.strip()[:500]}")
def groq_transcribe_chunk(audio_path, progress_label="", language=None, translate=False, literal=False):
    if not GROQ_API_KEY:
        print("\nGROQ_API_KEY is not set.")
        print("Get a free key at https://console.groq.com/keys and put it in your .env file.")
        sys.exit(1)
    endpoint = f"{GROQ_API_BASE}/{'translations' if translate else 'transcriptions'}"
    fields = {
        "model": GROQ_MODEL,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "segment",
    }
    if language and not translate:
        fields["language"] = language
    if literal:
        fields["temperature"] = str(LITERAL_TEMPERATURE)
    if literal or CUSTOM_PROMPT:
        fields["prompt"] = f"{LITERAL_PROMPT} {CUSTOM_PROMPT}"[:500] if literal else CUSTOM_PROMPT[:500]
    with open(audio_path, "rb") as audio_file:
        if HAS_UPLOAD_PROGRESS:
            fields["file"] = (audio_path.name, audio_file, "audio/mpeg")
            encoder = MultipartEncoder(fields=fields)
            start_time = time.time()
            def _on_progress(monitor):
                percent = (monitor.bytes_read / monitor.len * 100) if monitor.len else 100
                elapsed = time.time() - start_time
                print_progress_bar(
                    percent, prefix=f"  {progress_label} uploading to Groq",
                    suffix=f"| {format_size(monitor.bytes_read)}/{format_size(monitor.len)} | {format_time(elapsed)} elapsed",
                )
            monitor = MultipartEncoderMonitor(encoder, _on_progress)
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": monitor.content_type},
                data=monitor,
                timeout=GROQ_TIMEOUT_SECONDS,
            )
            print_progress_bar(100, prefix=f"  {progress_label} uploading to Groq", suffix="| done" + " " * 10)
            print()
        else:
            size = audio_path.stat().st_size
            print(f"  {progress_label} uploading to Groq ({format_size(size)})... ", end="", flush=True)
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": (audio_path.name, audio_file, "audio/mpeg")},
                data=fields,
                timeout=GROQ_TIMEOUT_SECONDS,
            )
            print("done.")
    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:500]} retry-after={response.headers.get('retry-after', '')}")
    return response.json()
def transcribe_video(video_path, duration, source_lang, target_lang):
    segments = []
    detected = None
    chunk_start = 0.0
    chunk_index = 0
    total_chunks = max(1, -int(-duration // AUDIO_CHUNK_SECONDS) - (1 if duration > AUDIO_CHUNK_SECONDS and 0 < duration % AUDIO_CHUNK_SECONDS < 30 else 0))
    while chunk_start < duration:
        chunk_duration = duration - chunk_start if chunk_index + 1 >= total_chunks else AUDIO_CHUNK_SECONDS
        chunk_path = TEMP_DIR / f"{video_path.stem}_chunk{chunk_index}.mp3"
        chunk_label = f"[chunk {chunk_index + 1}/{total_chunks}, {format_time(chunk_start)}-{format_time(chunk_start + chunk_duration)}]"
        print()
        extract_audio_chunk(video_path, chunk_start, chunk_duration, chunk_path, progress_label=chunk_label)
        result = {}
        try:
            if chunk_path.exists() and chunk_path.stat().st_size >= 2048:
                for attempt in range(4):
                    try:
                        result = groq_transcribe_chunk(chunk_path, progress_label=chunk_label, language=None if source_lang == "auto" else source_lang, translate=target_lang == "en" and source_lang != "en", literal=target_lang == "auto")
                        break
                    except (RuntimeError, requests.RequestException) as error:
                        if "invalid_media_file" in str(error):
                            print(f"  {chunk_label} skipped, Groq could not read this audio chunk.")
                            break
                        if attempt == 3 or not (isinstance(error, requests.RequestException) or any(f"error {code}:" in str(error) for code in (429, 500, 502, 503, 504))):
                            raise RuntimeError(str(error)) from error
                        wait = min(120, float(m.group(1)) if (m := re.search(r"retry-after=([\d.]+)", str(error))) else 20 * (attempt + 1))
                        print(f"\n  {chunk_label} {str(error)[:100]} - retrying in {wait:.0f}s ({attempt + 1}/3)")
                        time.sleep(wait)
            else:
                print(f"  {chunk_label} no audio in this range, skipped.")
        finally:
            # Always remove the temp audio chunk once it's been uploaded (success or failure).
            chunk_path.unlink(missing_ok=True)
        detected = detected or result.get("language")
        chunk_segments = result.get("segments")
        if chunk_segments:
            for seg in chunk_segments:
                text = seg.get("text", "").strip()
                if text:
                    start = seg["start"] + chunk_start
                    end = seg["end"] + chunk_start
                    segments.append((start, end, text))
                    print(f"  [{format_time(start)} -> {format_time(end)}] {text}")
        else:
            text = (result.get("text") or "").strip()
            if text:
                segments.append((chunk_start, chunk_start + chunk_duration, text))
                print(f"  [{format_time(chunk_start)} -> {format_time(chunk_start + chunk_duration)}] {text}")
        chunk_start += chunk_duration
        chunk_index += 1
    return segments, detected
def needs_conversion(source_lang, target_lang):
    return target_lang == "auto" or target_lang != "en" and target_lang != source_lang and not (source_lang == "en" and target_lang == "hing")
def resolve_llm_model():
    global RESOLVED_LLM_MODEL
    if RESOLVED_LLM_MODEL:
        return RESOLVED_LLM_MODEL
    try:
        response = requests.get(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=GROQ_TIMEOUT_SECONDS)
        available = {model["id"] for model in response.json()["data"]} if response.status_code == 200 else set()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        available = set()
    RESOLVED_LLM_MODEL = next((model for model in [GROQ_LLM_MODEL, *LLM_FALLBACK_MODELS] if model in available), GROQ_LLM_MODEL)
    if RESOLVED_LLM_MODEL != GROQ_LLM_MODEL:
        print(f"\n  Text model {GROQ_LLM_MODEL} is not available on your Groq account, using {RESOLVED_LLM_MODEL} instead.")
    return RESOLVED_LLM_MODEL
def groq_convert_batch(texts, target_lang):
    instruction = (
        "Do NOT translate and do NOT fix grammar. A line may look like 'IPA: <phonemes actually heard> | HEARD: <rough speech-to-text guess>'. Treat the IPA as the truth for the sounds and use HEARD only to find word boundaries. If a line has no IPA part, transliterate the text itself. Write every word, in order, in plain English (Roman) letters exactly as it sounds, whatever language it is spoken in, keeping every filler and repetition. Never output IPA symbols, the IPA/HEARD labels or any non-Latin script."
        if target_lang == "auto" else "Translate the meaning into Hinglish: natural spoken Hindi/Urdu written in Roman (English) letters the way people text it, keeping English words as they are. Never use Devanagari, Arabic, Kannada or Malayalam script."
        if target_lang == "hing" else f"Translate into {LANGUAGE_NAMES[target_lang]}, written in its native script."
    )
    messages = [
        {"role": "system", "content": f"You convert subtitle lines transcribed from speech that may mix English, Hindi, Urdu, Kannada and Malayalam. {instruction} Keep names and numbers, keep each line short and in the same order. {' Context about the audio: ' + CUSTOM_PROMPT + '.' if CUSTOM_PROMPT else ''} Reply with JSON only, in the form {{\"lines\": [...]}}, containing exactly {len(texts)} strings, one per input line."},
        {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
    ]
    for _ in range(LLM_MAX_RETRIES):
        try:
            response = requests.post(
                GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model": resolve_llm_model(), "messages": messages, "temperature": 0.2, "response_format": {"type": "json_object"}, "max_completion_tokens": LLM_MAX_COMPLETION_TOKENS, **({"reasoning_effort": "low"} if resolve_llm_model().startswith("openai/gpt-oss") else {})},
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except requests.Timeout:
            continue
        if response.status_code == 429:
            time.sleep(min(float(response.headers.get("retry-after", 10)), 30))
            continue
        if response.status_code == 400 and "json_validate_failed" in response.text:
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Groq chat API error {response.status_code}: {response.text[:500]}")
        try:
            lines = json.loads(response.json()["choices"][0]["message"]["content"])["lines"]
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        if isinstance(lines, list) and len(lines) == len(texts) and all(isinstance(line, str) for line in lines):
            return [line.strip() or original for line, original in zip(lines, texts)]
    if len(texts) > 1:
        return groq_convert_batch(texts[:len(texts) // 2], target_lang) + groq_convert_batch(texts[len(texts) // 2:], target_lang)
    raise RuntimeError("Groq did not return usable converted lines.")
def find_phoneme_model(snapshot_download):
    candidates = [os.getenv("PHONEME_MODEL_PATH"), PHONEME_DIR]
    try:
        candidates.append(snapshot_download(PHONEME_MODEL, local_files_only=True))
    except Exception:
        pass
    return next((Path(c) for c in candidates if c and (Path(c) / "config.json").is_file() and any((Path(c) / f).is_file() for f in ("model.safetensors", "pytorch_model.bin"))), None)
def download_phoneme_model(snapshot_download):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["attrib", "+h", str(MODELS_DIR)], capture_output=True)
    print(f"\n  Phoneme model not found on this computer. Downloading {PHONEME_MODEL} (about 1.3 GB, one time only) into {MODELS_DIR}...")
    for revision, weights in (("refs/pr/2", "model.safetensors"), (None, "model.safetensors"), (None, "pytorch_model.bin")):
        try:
            return Path(snapshot_download(PHONEME_MODEL, revision=revision, local_dir=PHONEME_DIR, allow_patterns=["*.json", weights]))
        except Exception as error:
            print(f"  Download attempt failed: {str(error)[:200]}")
    return None
def load_phoneme_model():
    global PHONEME_STATE
    if PHONEME_STATE:
        return PHONEME_STATE
    try:
        import numpy
        import torch
        from huggingface_hub import snapshot_download
        from transformers import Wav2Vec2ForCTC
    except ImportError:
        print("\n  The local phoneme model needs extra libraries. Run: pip install -r requirements-auto.txt")
        print("  Continuing with Whisper text only.")
        return None
    path = find_phoneme_model(snapshot_download) or download_phoneme_model(snapshot_download)
    if not path:
        print("\n  Could not get the phoneme model. Continuing with Whisper text only.")
        return None
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vocab = json.loads((path / "vocab.json").read_text(encoding="utf-8"))
    PHONEME_STATE = (numpy, torch, Wav2Vec2ForCTC.from_pretrained(str(path), torch_dtype=torch.float16 if device == "cuda" else torch.float32).to(device).eval(), {i: t for t, i in vocab.items()}, device)
    print(f"\n  Phoneme model loaded from {path} on {device}." + ("" if device == "cuda" else " PyTorch cannot see a GPU, so this runs on the CPU. Install the CUDA build of PyTorch to use your GPU."))
    return PHONEME_STATE
def recognise_phonemes(video_path, segments):
    state = load_phoneme_model()
    if not state:
        return None
    numpy, torch, model, id2tok, device = state
    audio = numpy.frombuffer(subprocess.run(
        [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        stdin=subprocess.DEVNULL, capture_output=True).stdout, dtype=numpy.int16)
    label = "  recognising sounds locally"
    results = []
    for index, (start, end, _) in enumerate(segments):
        print_progress_bar(index / len(segments) * 100, prefix=label, suffix=f"| {index}/{len(segments)} lines")
        sounds = []
        for window in range(int(start * 16000), int(end * 16000), 320000):
            wave = audio[window:min(window + 320000, int(end * 16000))].astype(numpy.float32) / 32768
            if len(wave) < 1600:
                continue
            wave = (wave - wave.mean()) / numpy.sqrt(wave.var() + 1e-7)
            with torch.inference_mode():
                ids = model(torch.from_numpy(wave)[None].to(device, model.dtype)).logits[0].argmax(-1).tolist()
            sounds += [id2tok[i] for k, i in enumerate(ids) if (k == 0 or i != ids[k - 1]) and id2tok[i] not in ("<pad>", "<s>", "</s>", "<unk>")]
        results.append(" ".join(sounds))
    print_progress_bar(100, prefix=label, suffix="| done" + " " * 10)
    print()
    return results
def convert_segments(segments, target_lang, hints=None):
    label = f"  converting to {LANGUAGE_NAMES[target_lang]}"
    converted = []
    failed = 0
    for batch_start in range(0, len(segments), LLM_BATCH_SIZE):
        batch = segments[batch_start:batch_start + LLM_BATCH_SIZE]
        print_progress_bar(batch_start / len(segments) * 100, prefix=label, suffix=f"| {batch_start}/{len(segments)} lines")
        try:
            texts = groq_convert_batch([f"IPA: {hints[batch_start + i]} | HEARD: {text}" if hints and hints[batch_start + i] else text for i, (_, _, text) in enumerate(batch)], target_lang)
        except (RuntimeError, requests.RequestException) as error:
            print(f"\n  Conversion failed for lines {batch_start + 1}-{batch_start + len(batch)}: {error}")
            failed += 1
            texts = [text for _, _, text in batch]
        converted.extend((start, end, text) for (start, end, _), text in zip(batch, texts))
    print_progress_bar(100, prefix=label, suffix="| done" + " " * 10)
    print()
    return converted, failed
# ─────────────────────────────────────────────────────────────────────────────
# Step 3: write the .srt caption file
# ─────────────────────────────────────────────────────────────────────────────
def format_srt_timestamp(seconds):
    total_ms = max(0, round(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
def write_srt(segments, srt_path):
    lines = []
    for index, (start, end, text) in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    srt_path.write_text("\n".join(lines), encoding="utf-8")
# ─────────────────────────────────────────────────────────────────────────────
# Orchestration: one full video, start to finish
#   video -> temp audio chunks -> Groq -> .srt -> cleanup temp files
#   (no caption burn-in / muxing back onto the video)
# ─────────────────────────────────────────────────────────────────────────────
def process_video(video_path, downloaded_from_drive=False, source_lang=DEFAULT_SOURCE_LANG, target_lang=DEFAULT_TARGET_LANG):
    video_path = Path(video_path)
    print("\n" + "=" * 80)
    print(f"CAPTIONING: {video_path.name}")
    print("=" * 80)
    if not video_path.exists():
        print(f"File not found: {video_path}")
        return
    if not shutil.which(FFMPEG) or not shutil.which(FFPROBE):
        print("FFmpeg/FFprobe were not found. Install them, add them to your PATH, or set FFMPEG_PATH and FFPROBE_PATH in your .env file.")
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        duration = get_duration(video_path)
    except Exception as error:
        print(f"Could not read video duration: {error}")
        return
    srt_dir = OUTPUT_DIR if downloaded_from_drive else video_path.parent
    converting = needs_conversion(source_lang, target_lang)
    saved_transcript = find_transcript(video_path.stem, srt_dir) if converting and target_lang != "auto" else None
    saved = []
    failed = 0
    try:
        if saved_transcript:
            print(f"\nReusing existing transcript: {saved_transcript.name}")
            segments = read_srt(saved_transcript)
        else:
            print("\nTranscribing via Groq's hosted Whisper API (online - nothing downloaded locally)...")
            segments, detected = transcribe_video(video_path, duration, source_lang, target_lang)
            if segments and converting and target_lang != "auto":
                saved.append(srt_dir / srt_name(video_path.stem, source_lang, "transcribe", source_lang if source_lang != "auto" else LANGUAGE_CODES.get((detected or "").lower(), (detected or "auto").lower())))
                write_srt(segments, saved[-1])
        if segments and converting:
            segments, failed = convert_segments(segments, target_lang, recognise_phonemes(video_path, segments) if target_lang == "auto" else None)
    except RuntimeError as error:
        print(f"\nGroq API request failed: {error}")
        cleanup_after_video(video_path, downloaded_from_drive)
        return
    if not segments:
        print("No speech was detected in this video - no .srt file was generated.")
        cleanup_after_video(video_path, downloaded_from_drive)
        return
    if failed:
        print(f"\n{failed} batch(es) failed to convert, so no translation file was written. Run again to retry{'' if target_lang == 'auto' else ' from the saved transcript'}.")
    else:
        saved.append(srt_dir / srt_name(video_path.stem, source_lang, "transliterate" if target_lang == "auto" else "translate" if converting or (target_lang == "en" and source_lang != "en") else "transcribe", target_lang))
        write_srt(segments, saved[-1])
    print("=" * 80)
    print("INCOMPLETE" if failed else "COMPLETE")
    print("=" * 80)
    for srt_path in saved:
        print(f"Subtitle file : {srt_path}")
    print("=" * 80)
    cleanup_after_video(video_path, downloaded_from_drive)
def cleanup_after_video(video_path, downloaded_from_drive):
    """Removes anything temporary for this video: leftover chunk files in
    TEMP_DIR, and - if the video itself was pulled from Google Drive just for
    this run - the local copy of that video too. The .srt in OUTPUT_DIR is
    the only thing meant to stick around."""
    video_path = Path(video_path)
    # Any leftover audio chunks for this video (normally already removed as they're
    # uploaded, but this also clears out chunks left behind by an interrupted run).
    for leftover_chunk in TEMP_DIR.glob(f"{video_path.stem}_chunk*.mp3"):
        leftover_chunk.unlink(missing_ok=True)
    # The video itself, only if it's a temporary local copy downloaded from Drive.
    if downloaded_from_drive:
        try:
            video_path.unlink(missing_ok=True)
            print(f"Removed temporary Google Drive download: {video_path.name}")
        except Exception as error:
            print(f"Could not remove temporary Google Drive download ({video_path.name}): {error}")
def main():
    global CUSTOM_PROMPT
    print("=" * 80)
    print("AUTO CAPTION GENERATOR - via Groq's hosted Whisper API")
    print("=" * 80)
    print(f"FFmpeg          : {FFMPEG}")
    print(f"FFprobe         : {FFPROBE}")
    print(f"Groq model      : {GROQ_MODEL} | text model: {GROQ_LLM_MODEL}")
    print(f"Output folder   : {OUTPUT_DIR.resolve()}")
    if not HAS_UPLOAD_PROGRESS:
        print("Tip            : pip install requests-toolbelt for a live upload progress bar")
        print("                 (uploads still work fine without it).")
    if not GROQ_API_KEY:
        print("\nGROQ_API_KEY is not set. Add it to a .env file next to this script:")
        print("GROQ_API_KEY=your_key_here")
        print("Get a free key at https://console.groq.com/keys")
        sys.exit(1)
    print("\nLanguage codes: en English | hi Hindi | ur Urdu | kn Kannada (ka works too) | ml Malayalam (ma works too) | hing Hinglish | auto sound-based English letters (caption language only)")
    print("Audio language can also be 'auto' to let Whisper detect it.")
    source_lang = ask_language("\nAudio language (what is spoken)", DEFAULT_SOURCE_LANG, SOURCE_OPTIONS)
    target_lang = ask_language("Caption language (what the .srt should contain)", DEFAULT_TARGET_LANG, TARGET_OPTIONS)
    CUSTOM_PROMPT = input("Custom prompt about the audio, e.g. mixed languages/names (Enter = none): ").strip() or CUSTOM_PROMPT
    print("\nAccepted input: a local audio/video file, a local folder of audio/video files,")
    print("a Google Drive file link/ID, or a Google Drive folder link/ID.")
    raw_input_text = input("\nEnter file/folder path or Google Drive link/ID: ")
    videos = resolve_inputs(raw_input_text, target_lang)
    if not videos:
        print("\nNothing to process.")
        return
    print(f"\n{len(videos)} file(s) queued for captioning.")
    total_videos = len(videos)
    for index, (video_path, downloaded_from_drive) in enumerate(videos, start=1):
        print(f"\n[File {index}/{total_videos}]")
        try:
            process_video(video_path, downloaded_from_drive, source_lang, target_lang)
        except Exception as error:
            print(f"\nFailed on {Path(video_path).name}: {error}")
            cleanup_after_video(video_path, downloaded_from_drive)
if __name__ == "__main__":
    main()