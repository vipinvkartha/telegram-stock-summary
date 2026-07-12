# AGENTS.md

Guidance for coding agents working in this repository.

## Repository Shape

- Main application code lives in `backend/`.
- The backend is a FastAPI app created by `app.main:create_app`.
- Production deployment is Railway using `backend/railway.toml` and `backend/Dockerfile`.
- Database migrations are managed with Alembic in `backend/migrations/`.

## Working Directory

Run backend commands from:

```bash
cd backend
```

Use the local virtualenv when available:

```bash
source .venv/bin/activate
```

## Verification

Run the test suite before committing backend changes:

```bash
pytest
```

The test suite uses SQLite and should not need external services.

## Deployment

Deploy to Railway from the repository root:

```bash
railway up backend --path-as-root --service api --environment production
```

For uploaded Railway deployments, prefer redeploy over restart:

```bash
railway redeploy --service api --environment production
```

## Secrets

Never commit real values for:

- `BOT_TOKEN`
- `GEMINI_API_KEY`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `ADMIN_API_TOKEN`
- `DATABASE_URL` with real credentials

The app redacts Telegram bot tokens in logs, but old logs or terminal output may still contain secrets. Rotate exposed tokens.

## Operational Details

- Telegram bot commands use `BOT_TOKEN`.
- Telegram collection uses Telethon with `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`, and `TELEGRAM_CHANNELS`.
- The live collector only receives new messages. Use `POST /telegram/backfill` to import recent channel history.
- Protected admin endpoints require the `X-Admin-Token` header matching `ADMIN_API_TOKEN`.
- Gemini free-tier quota is low; keep `MAX_REPORT_STOCKS` small unless billing/quota is increased.

## Code Style

- Prefer existing patterns in `backend/app`.
- Keep route handlers thin; put domain behavior in services or collector classes.
- Avoid adding public endpoints for administrative actions unless protected.
- Add focused tests under `backend/tests` for behavior changes.
- Do not remove log redaction or secret handling protections.
