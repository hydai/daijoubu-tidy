# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

大丈夫整理術 (Daijoubu Tidy) - A Discord bot for AI-powered decluttering assistance. Users upload item photos, the bot analyzes them via OpenAI Vision API, and creates trackable tasks with keep/consider/discard recommendations.

## Development Commands

```bash
# Start bot with database
make start

# Stop bot and database
make stop

# Run bot only (assumes db is running)
make run

# Install dependencies
make install          # production
make dev-install      # dev + pre-commit hooks

# Linting and formatting
make lint             # ruff check src tests
make format           # ruff format + fix

# Testing
make test             # pytest -v --cov=src --cov-report=term-missing

# Database
make db-up            # start PostgreSQL container
make db-down          # stop PostgreSQL container
make db-upgrade       # alembic upgrade head
make db-migrate       # alembic revision --autogenerate -m "message"
```

## Architecture

```
src/
├── bot/
│   ├── main.py           # Entry point, DaijoubuBot class
│   └── cogs/
│       ├── declutter.py  # /declutter, /tasks, /task-* commands
│       └── summary.py    # /stats, /summary, /export commands
├── core/
│   ├── config.py         # Pydantic settings (loads .env)
│   └── database.py       # SQLAlchemy async + pgvector init
├── models/
│   └── declutter_task.py # DeclutterTask table (UUID pk, status, decision)
└── services/
    ├── ai.py             # AIService.analyze_image_for_declutter()
    └── declutter.py      # DeclutterTaskService (CRUD + stats)
```

**Key patterns:**
- Async throughout: `asyncpg`, `AsyncOpenAI`, `aiosqlite` (tests)
- Database sessions via `async with get_db() as db:` context manager
- Discord.py slash commands with `@app_commands.command()`
- Services accept db session in constructor

## Configuration

Required environment variables (see `.env.example`):
- `DISCORD_BOT_TOKEN` - Discord bot token
- `OPENAI_API_KEY` - OpenAI API key

Optional:
- `VISION_MODEL` - AI model (default: `gpt-4.1-mini`), supports: `gpt-4.1-nano`, `gpt-4.1`, `gpt-4o-mini`, `gpt-4o`
- `DISCORD_GUILD_ID` - For faster command sync during development
- `DATABASE_URL` - PostgreSQL connection string

## Tech Stack

- Python 3.12, discord.py 2.3+, SQLAlchemy 2.0+ (async)
- PostgreSQL 16 with pgvector extension
- Alembic migrations, Ruff linting, pytest-asyncio
