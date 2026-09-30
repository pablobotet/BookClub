"""Safety checks for the PostgreSQL integration database setup script."""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "setup_test_db.sh"


def run_script(**environment: str) -> subprocess.CompletedProcess[str]:
    """Run setup without inheriting test-database configuration."""
    env = os.environ.copy()
    env.pop("TEST_DATABASE_URL", None)
    env.pop("TEST_DATABASE_ADMIN_URL", None)
    env.update(environment)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=SCRIPT.parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_setup_script_rejects_missing_test_url() -> None:
    result = run_script()

    assert result.returncode == 1
    assert "TEST_DATABASE_URL must be set" in result.stdout


def test_setup_script_rejects_non_test_database_before_connecting() -> None:
    result = run_script(TEST_DATABASE_URL="postgresql://pablobotet@localhost/reading_club")

    assert result.returncode == 1
    assert "expected reading_club_test" in result.stderr


def test_setup_script_rejects_non_maintenance_admin_database() -> None:
    result = run_script(
        TEST_DATABASE_URL="postgresql://pablobotet@localhost/reading_club_test",
        TEST_DATABASE_ADMIN_URL="postgresql://pablobotet@localhost/reading_club",
    )

    assert result.returncode == 1
    assert "postgres maintenance database" in result.stderr
