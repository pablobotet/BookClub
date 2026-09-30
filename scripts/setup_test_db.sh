#!/usr/bin/env bash
# Create and migrate the dedicated local PostgreSQL database used by integration tests.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

# Exported values take precedence, which supports CI without a .env.test file.
provided_test_url=${TEST_DATABASE_URL-}
provided_admin_url=${TEST_DATABASE_ADMIN_URL-}
if [[ -f .env.test ]]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env.test
    set +a
fi
if [[ -n "$provided_test_url" ]]; then
    TEST_DATABASE_URL=$provided_test_url
fi
if [[ -n "$provided_admin_url" ]]; then
    TEST_DATABASE_ADMIN_URL=$provided_admin_url
fi

if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
    printf '%s\n' "TEST_DATABASE_URL must be set in .env.test or the environment."
    exit 1
fi
if [[ ! -x .venv/bin/python || ! -x .venv/bin/alembic ]]; then
    printf '%s\n' "Missing .venv tools. Install the project with: python3 -m pip install -e '.[dev]'"
    exit 1
fi
if ! command -v psql >/dev/null 2>&1 || ! command -v createdb >/dev/null 2>&1; then
    printf '%s\n' "psql and createdb are required to create the test database."
    exit 1
fi

# Parse credentials and invoke PostgreSQL tools in Python so secrets never become
# shell arguments or output. Database and role names are strictly validated.
TEST_DATABASE_URL="$TEST_DATABASE_URL" \
TEST_DATABASE_ADMIN_URL="${TEST_DATABASE_ADMIN_URL:-}" \
    .venv/bin/python - <<'PY'
import os
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

DATABASE_NAME = "reading_club_test"
ROLE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


def error(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_url(value: str, name: str) -> tuple[dict[str, str], str, str]:
    url = urlsplit(value)
    if url.scheme not in {"postgresql", "postgresql+asyncpg"} or not url.hostname:
        error(f"{name} must be a PostgreSQL URL with a host")
    database = unquote(url.path.lstrip("/"))
    if not database or "/" in database:
        error(f"{name} must name one database")
    user = unquote(url.username or "")
    if not ROLE.fullmatch(user):
        error(f"{name} must contain a simple PostgreSQL role name")
    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": url.hostname,
            "PGPORT": str(url.port or 5432),
            "PGUSER": user,
            "PGPASSWORD": unquote(url.password or ""),
        }
    )
    return environment, database, user


test_environment, database, test_role = parse_url(
    os.environ["TEST_DATABASE_URL"], "TEST_DATABASE_URL"
)
if database != DATABASE_NAME:
    error(f"Refusing to operate on database '{database}'; expected {DATABASE_NAME}.")

admin_url = os.environ.get("TEST_DATABASE_ADMIN_URL")
if admin_url:
    admin_environment, admin_database, _ = parse_url(
        admin_url, "TEST_DATABASE_ADMIN_URL"
    )
    if admin_database != "postgres":
        error("TEST_DATABASE_ADMIN_URL must target the postgres maintenance database")
else:
    admin_environment = test_environment
    admin_database = "postgres"


def psql(query: str) -> str:
    result = subprocess.run(
        ["psql", admin_database, "-v", "ON_ERROR_STOP=1", "-tAc", query],
        env=admin_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


try:
    if psql(f"SELECT 1 FROM pg_roles WHERE rolname = '{test_role}'") != "1":
        error(f"PostgreSQL role '{test_role}' does not exist; create it before setup.")
    owner = psql(
        "SELECT pg_get_userbyid(datdba) FROM pg_database "
        f"WHERE datname = '{DATABASE_NAME}'"
    )
    if not owner:
        subprocess.run(
            ["createdb", "--owner", test_role, DATABASE_NAME],
            env=admin_environment,
            check=True,
        )
    elif owner != test_role:
        error(
            f"{DATABASE_NAME} is owned by '{owner}', not '{test_role}'. "
            "Drop and recreate the dedicated test database or correct its owner."
        )
except subprocess.CalledProcessError:
    error("Unable to create or inspect reading_club_test; check PostgreSQL access.")
PY

DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/alembic upgrade head
printf '%s\n' "Test database is ready. Run: TEST_DATABASE_URL=... .venv/bin/pytest -m integration"
