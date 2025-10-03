# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: entry point for the terminal UI.
- `spotify_utils.py`, `upnext.py`, `lyrics_sync.py`: core playback, queueing, and lyrics.
- `gpt_dj.py`, `gpt_utils.py`, `genius_utils.py`, `logger_utils.py`: AI, helpers, and logging.
- `assets/`: images and UI assets. `docs/`: documentation. `tests/`: unit tests.
- `requirements.txt`: Python dependencies. `example.env` → copy to `.env`.

## Build, Test, and Development Commands
- Create venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Configure env: `cp example.env .env` and fill `OPENAI_API_KEY`, Spotify keys.
- Run app: `python main.py`
- Run tests: `python -m unittest -v`

## Coding Style & Naming Conventions
- Python 3.10+. Use PEP 8, 4‑space indentation, line length ~100.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`.
- Add type hints and docstrings to new/modified functions.
- Prefer small, focused functions; keep Spotify/OpenAI calls isolated behind utils.
- Use existing logging pattern (`logger_utils.py`) and avoid noisy prints.

## Testing Guidelines
- Framework: `unittest` (see `tests/`). Name files `test_*.py`, classes `*Test`.
- Run locally: `python -m unittest -v`.
- Mock external services (e.g., `unittest.mock.MagicMock` for Spotify/OpenAI). Avoid network I/O.
- Add tests alongside changes (e.g., `tests/test_upnext.py` pattern). Maintain or increase coverage.

## Commit & Pull Request Guidelines
- Commit style mirrors Conventional Commits: `feat(scope): summary`, `fix(scope): …` (e.g., `feat(ui): toggle keybinds`).
- Keep PRs focused and descriptive: purpose, key changes, and test steps.
- Link related issues; include screenshots or terminal captures for UI changes.
- Ensure `python -m unittest -v` passes and `.env` is not modified in PRs.

## Security & Configuration Tips
- Never commit secrets. Use `.env` loaded via `python-dotenv`.
- Required: `OPENAI_API_KEY`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`. Optional: Last.fm keys.
- Validate inputs from AI before acting; guard against empty/invalid responses.
- Be mindful of rate limits; centralize API calls in utils for retries/backoff.

