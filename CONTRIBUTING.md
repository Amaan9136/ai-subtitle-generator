# Contributing

Thanks for wanting to help. Bug reports, fixes, new language support, documentation improvements and ideas are all welcome.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). By contributing code you agree that it is released under the project's [MIT License](LICENSE).

## Before you start

- Search the [existing issues](../../issues) and pull requests first to avoid duplicates.
- For a large change, open an issue to discuss it before writing code.
- For a security problem, do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## Reporting a bug

Open an issue with the bug report template and include:

- Your operating system, Python version and FFmpeg version (`ffmpeg -version`)
- The audio and caption language you chose
- The exact steps and the full error text

Remove your API key, file paths you want to keep private, and any private transcript text before pasting logs. Never attach `.env`, `credentials.json` or `token.json`.

## Suggesting a feature

Open an issue with the feature request template. Say what problem you are solving, not only the solution you have in mind.

## Development setup

1. Fork the repository and clone your fork.
2. Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell activate with `.venv\Scripts\Activate.ps1`.

3. Copy `.env.example` to `.env` and add your own Groq key. If FFmpeg is not on your `PATH`, set `FFMPEG_PATH` and `FFPROBE_PATH` there.
4. Create a branch for your change:

```bash
git checkout -b fix/short-description
```

## Checks to run

CI runs these on every pull request, so run them locally first:

```bash
python -m py_compile auto_caption_generator.py
python -c "import auto_caption_generator"
```

Then run the tool by hand on a short audio clip for the languages your change touches. CI cannot call the Groq API, so this manual run matters.

## Code guidelines

- Match the style of the surrounding code: naming, quotes, spacing and structure.
- Keep changes focused. Do not reformat or reorder code you are not changing.
- Keep the script working on Python 3.10 and newer.
- Read secrets only from environment variables or `.env`. Never hardcode keys, tokens or personal paths.
- Treat anything that comes from outside as untrusted: Google Drive file names, API responses and user input.
- Do not add a dependency unless it is needed. If you add one, put it in `requirements.txt` (or `requirements-auto.txt` if only the `auto` sound-to-sound mode needs it) and mention it in your pull request.

### Adding a language

Language support lives in the constants near the top of `auto_caption_generator.py`: `LANGUAGE_NAMES`, `SOURCE_OPTIONS`, `TARGET_OPTIONS` and `LANGUAGE_ALIASES`. `auto` is a special caption language (sound-to-sound in English letters) handled by `LITERAL_PROMPT`, `LITERAL_TEMPERATURE`, `needs_conversion` and the local phoneme model (`recognise_phonemes`). Add the language there, update the language tables in the README and `.env.example`, and test both transcription and conversion with real audio.

## Documentation

Update the README, `.env.example` and `CHANGELOG.md` when your change affects how people use the tool.

## Pull requests

1. Push your branch to your fork and open a pull request against `main`.
2. Fill in the pull request template.
3. Keep the pull request to one topic. Smaller pull requests get reviewed faster.
4. Be ready to make changes after review.

Commit messages should be short and in the imperative mood, for example `Fix Drive filename handling`.

## Credit

Contributors are listed on the GitHub contributors page. Thank you for helping.