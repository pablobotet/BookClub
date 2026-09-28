# Reading Club API

A local FastAPI backend for a reading club. Milestone 4 provides managed user
profiles, reading groups, memberships, a global book catalog, and group-scoped
reviews and votes; authentication is intentionally not implemented yet.

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
- `POST`, `GET`, `GET /{id}`, and `PATCH /{id}` for `/api/v1/books`.
- `POST` and `GET /api/v1/groups/{group_id}/reviews`, plus `GET` and `PATCH`
  for `/api/v1/groups/{group_id}/reviews/{review_id}`.
- `POST` and `GET /api/v1/groups/{group_id}/votes`; `DELETE` retracts a vote.
- `POST /api/v1/groups/{group_id}/selections` draws and records a next book;
  `GET /api/v1/groups/{group_id}/selections` lists the draw history and
  `GET /api/v1/groups/{group_id}/selections/latest` returns the newest draw.

Emails are stored lowercase. User email, group name, and user/group
memberships are unique. Creating a group does not automatically create a
membership because there is no authenticated current user yet. ISBNs are unique
when supplied. Reviews and votes require an active user who belongs to the
group; request bodies carry `user_id` until authentication exists. A member may
review or vote for a specific book only once per group.

Only an active group admin may request a selection, using
`requested_by_user_id`. Every distinct book with a current vote is an eligible
candidate, and each candidate has equal probability regardless of how many
votes it received: votes nominate candidates, rather than weighting the draw.
Each draw is persisted independently with its candidate snapshot and count;
votes are not removed, so repeated draws are allowed and auditable.

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
