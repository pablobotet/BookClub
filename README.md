# Reading Club API

A local FastAPI backend for a reading club. Milestone 2 provides managed user
profiles, reading groups, and group memberships; authentication and ownership
semantics are intentionally not implemented yet.

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

## API v1

- `POST`, `GET`, `GET /{id}`, and `PATCH /{id}` for `/api/v1/users`
- `POST`, `GET`, `GET /{id}`, and `PATCH /{id}` for `/api/v1/groups`
- `POST /api/v1/groups/{group_id}/members` adds a user as `member` (default)
  or `admin`.
- `GET /api/v1/groups/{group_id}/members` lists group memberships.
- `DELETE /api/v1/groups/{group_id}/members/{user_id}` removes a membership.

Emails are stored lowercase. User email, group name, and user/group
memberships are unique. Creating a group does not automatically create a
membership because there is no authenticated current user yet.

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
