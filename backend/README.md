# Telegram AI Stock Analyst

MVP backend for monitoring public Telegram stock channels, extracting discussed stocks,
summarizing discussion clusters, generating AI investment analysis, and delivering reports
through REST and Telegram bot surfaces.

## Quick Start

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`.

For local development without Postgres:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
DATABASE_URL=sqlite+aiosqlite:///./dev.db uvicorn app.main:create_app --factory --reload
```

## Key Environment Variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL. Use `postgresql+asyncpg://...` in production. |
| `GEMINI_API_KEY` | Enables the real Gemini provider. Without it, the app uses a deterministic mock provider. |
| `GEMINI_MODEL` | Defaults to `gemini-2.5-flash`. |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | Enables Telethon channel collection. |
| `TELEGRAM_CHANNELS` | Comma-separated public channel usernames or links. |
| `BOT_TOKEN` | Enables Telegram bot commands. |
| `REPORT_TIMES` | Comma-separated report times such as `09:00,18:00`. |
| `REPORT_TIMEZONE` | Timezone used for scheduled reports. |

## MVP Behavior

- Stores raw Telegram messages and extracted links.
- Normalizes, deduplicates, extracts ticker/company mentions, clusters, and ranks messages.
- Keeps AI access behind `LLMProvider`; app code does not depend directly on Gemini.
- Generates persisted report payloads and formatted Telegram-ready text.
- Exposes `/health`, `/stocks`, `/reports/latest`, `/reports/generate`, and `/watchlist`.
- Runs scheduled reports at configured times through APScheduler.

## Tests

```bash
cd backend
pytest
```
