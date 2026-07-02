#!/usr/bin/env python
"""Verify that Alembic migrations apply cleanly against a REAL PostgreSQL instance.

This script exists because SQLite (used by this project's automated test
suite) cannot adequately validate several things this schema relies on:
native PostgreSQL ENUM types, JSONB, partial indexes, UUID columns,
CHECK/UNIQUE constraints, and timezone-aware timestamps. Passing the test
suite is not the same as having validated the schema — this script is the
honest way to actually do that.

Usage:
    python scripts/check_postgres_migrations.py [--skip-roundtrip]

Behavior:
    1. Reads DATABASE_URL (from a real environment variable, falling back to
       .env — same resolution as the app, via `Settings`).
    2. Refuses to continue if it does not look like a PostgreSQL URL.
    3. Opens a real connection and runs `SELECT 1`. Fails loudly and exits
       non-zero if that does not work (e.g. Docker Compose isn't running).
    4. Runs `alembic upgrade head`, then `alembic current`.
    5. Unless --skip-roundtrip is passed, also runs `alembic downgrade base`
       followed by `alembic upgrade head` again, to prove the migrations are
       reversible and re-appliable, not just appliable once.

This script never prints a success message unless every step above actually
succeeded — it does not "assume" or "simulate" success.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"


def _get_database_url() -> str:
    sys.path.insert(0, str(SRC_ROOT))
    from blueberry_microid.infrastructure.config.settings import Settings

    return Settings().database_url


def _check_connection(database_url: str) -> None:
    from sqlalchemy import create_engine, text

    print(f"[1/4] Checking connection to PostgreSQL ({database_url}) ...")
    try:
        # A short connect_timeout makes this fail fast (a few seconds)
        # instead of hanging when nothing is listening on the target host
        # (e.g. Docker Compose was never started).
        engine = create_engine(database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure here means "not validated"
        print("FAILED: could not connect to PostgreSQL.")
        print(f"  {type(exc).__name__}: {exc}")
        print()
        print("Is PostgreSQL running? Try:")
        print("  docker compose up -d")
        print("  docker compose ps   # wait until postgres is 'healthy'")
        sys.exit(1)
    print("  OK: connection established.")


def _run_alembic(*args: str) -> None:
    print(f"[..] Running: alembic {' '.join(args)}")
    result = subprocess.run(["alembic", *args], cwd=REPO_ROOT)
    if result.returncode != 0:
        print(f"FAILED: 'alembic {' '.join(args)}' exited with status {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    skip_roundtrip = "--skip-roundtrip" in sys.argv

    database_url = _get_database_url()
    if not database_url.startswith("postgresql"):
        print(f"DATABASE_URL does not look like PostgreSQL: {database_url!r}")
        print("This check is only meaningful against a real PostgreSQL instance;")
        print("refusing to report a false positive against SQLite or another dialect.")
        sys.exit(1)

    _check_connection(database_url)

    print("[2/4] Applying migrations ...")
    _run_alembic("upgrade", "head")

    print("[3/4] Current revision:")
    _run_alembic("current")

    if not skip_roundtrip:
        print("[4/4] Verifying migrations are reversible (downgrade to base, then upgrade again) ...")
        _run_alembic("downgrade", "base")
        _run_alembic("upgrade", "head")
    else:
        print("[4/4] Skipped (--skip-roundtrip).")

    print()
    print("SUCCESS: migrations were applied to and verified against a real PostgreSQL instance.")


if __name__ == "__main__":
    main()
