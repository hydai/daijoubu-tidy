# 大丈夫整理術

AI-powered personal information organizer Discord Bot.

## Features

- **Smart Collection**: Save text, URLs with automatic metadata extraction
- **AI Classification**: Automatic content categorization using GPT
- **Semantic Search**: Find information using natural language queries (pgvector)
- **Tagging**: Manual tagging for organization
- **Summaries**: Daily/weekly AI-generated summaries
- **Export**: Export data in JSON or CSV format

## Quick Start

```bash
# Install dependencies
uv venv && uv pip install -e ".[dev]"

# Start database
docker compose up -d db

# Run migrations
source .venv/bin/activate
alembic upgrade head

# Start bot
python -m src.bot.main
```

## Discord Commands

| Command | Description |
|---------|-------------|
| `/save <content>` | Save text |
| `/save-url <url>` | Save URL with metadata |
| `/search <query>` | Semantic search |
| `/find <keyword>` | Keyword search |
| `/tag <id> <tags>` | Add tags |
| `/list` | List items |
| `/summary` | AI summary |
| `/stats` | Statistics |
| `/export` | Export data |

## Tech Stack

- Python 3.12+
- discord.py
- PostgreSQL + pgvector
- SQLAlchemy (async)
- OpenAI API
