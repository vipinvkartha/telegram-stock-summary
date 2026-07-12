# Telegram Stock Summarizer

Backend service that monitors configured Telegram stock-market channels, stores messages, extracts stock mentions, generates AI-assisted market summaries, and exposes the result through a REST API and Telegram bot commands.

The app is currently a Python/FastAPI backend under `backend/`.

## Features

- Collects new Telegram channel/group messages using Telethon.
- Supports manual backfill of recent Telegram history.
- Extracts stock mentions, including common US tickers and Indian/NSE symbols.
- Generates stock discussion summaries and balanced AI analysis with Gemini.
- Stores messages, stocks, summaries, analyses, and reports in Postgres.
- Serves latest reports through REST endpoints and Telegram bot commands.
- Runs scheduled reports with APScheduler.
- Deploys to Railway with Docker and managed Postgres.

## Project Layout

```text
backend/
  app/
    ai/             Gemini provider, prompts, JSON parsing, mock provider
    api/            FastAPI routes and dependencies
    collector/      Telegram collection and backfill
    config/         Settings and logging
    database/       SQLAlchemy session/base
    models/         Database models
    processor/      Normalization, deduplication, stock extraction, ranking
    repositories/   Data access
    scheduler/      Scheduled report generation
    telegram/       Telegram bot commands
  migrations/       Alembic migrations
  scripts/          Operational helper scripts
  tests/            Pytest suite
```

## Local Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
DATABASE_URL=sqlite+aiosqlite:///./dev.db uvicorn app.main:create_app --factory --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Run tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

## Environment Variables

Core:

```text
DATABASE_URL=postgresql+asyncpg://...
ENVIRONMENT=production
LOG_LEVEL=INFO
AUTO_CREATE_SCHEMA=false
ADMIN_API_TOKEN=<secret token for protected admin endpoints>
```

AI:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=<gemini api key>
GEMINI_MODEL=gemini-2.5-flash
AI_REQUEST_TIMEOUT_SECONDS=45
MAX_REPORT_STOCKS=2
```

Telegram collection:

```text
TELEGRAM_API_ID=<my.telegram.org api_id>
TELEGRAM_API_HASH=<my.telegram.org api_hash>
TELEGRAM_SESSION_STRING=<telethon string session>
TELEGRAM_CHANNELS=https://t.me/channel1,https://t.me/channel2
```

Telegram bot:

```text
BOT_TOKEN=<bot token from @BotFather>
```

Reports:

```text
REPORT_TIMES=09:00,18:00
REPORT_TIMEZONE=Europe/Berlin
DEFAULT_REPORT_HOURS=12
MAX_MESSAGES_PER_STOCK=80
```

## Telegram Session Setup

The bot token is only for bot commands. Message collection uses a Telegram user session through Telethon.

Generate a session string locally:

```bash
cd backend
railway run --service api .venv/bin/python scripts/create_telegram_session.py
```

Set the printed value in Railway:

```bash
railway variable set TELEGRAM_SESSION_STRING="<printed session string>" --service api
railway redeploy --service api --environment production
```

## Railway Deployment

The service is configured by `backend/railway.toml`. Deploy the backend directory as the Railway root:

```bash
railway up backend --path-as-root --service api --environment production
```

This uses the Dockerfile, runs Alembic migrations before deploy, starts Uvicorn on Railway's `$PORT`, and health-checks `/health`.

Railway `restart` may not work for uploaded deployments. Use:

```bash
railway redeploy --service api --environment production
```

## Backfill Old Telegram Messages

The live collector only receives new messages. To import recent history, call the protected backfill endpoint:

```bash
curl -X POST https://api-production-9294.up.railway.app/telegram/backfill \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_API_TOKEN" \
  -d '{"limit_per_channel":200}'
```

Then generate a report:

```bash
curl -X POST https://api-production-9294.up.railway.app/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"hours_back":168,"report_type":"manual"}'
```

## API

```text
GET  /health
GET  /stocks
GET  /watchlist
GET  /reports/latest
POST /reports/generate
POST /telegram/backfill                 protected by X-Admin-Token
GET  /telegram/extraction-diagnostics   protected by X-Admin-Token
```

## Telegram Bot Commands

```text
/start
/help
/report
/summary
/watchlist
/add TSLA
/remove TSLA
/settings
/history
```

## Notes

- `MAX_REPORT_STOCKS=2` is recommended on Gemini free tier because each stock can require a summarize call and an analysis call.
- Bot tokens, Gemini keys, Telegram API hashes, and Telethon session strings are secrets. Do not commit them.
- Reports are informational only and include a "Not financial advice" disclaimer.
