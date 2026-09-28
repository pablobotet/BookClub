# Reading Club API

A local FastAPI backend for a reading club. Milestone 1 provides only the
application foundation; no domain entities or domain endpoints exist yet.

## Prerequisites

- Python 3.11 or later
- PostgreSQL installed and running locally (required for migrations and future
  database-backed endpoints)

## Setup

```bash
~/.local/bin/python3.11 -m pip install -e '.[dev]'
cp .env.example .env
```

Update `DATABASE_URL` in `.env` if your local PostgreSQL credentials differ.
The default database URL targets a database named `reading_club`.

## Run

```bash
uvicorn reading_club.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Test and quality checks

```bash
pytest
ruff check .
mypy
```

The test suite does not need PostgreSQL to be running.

## Migrations

With PostgreSQL running and the `reading_club` database created:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Alembic reads `DATABASE_URL` from the application settings.
