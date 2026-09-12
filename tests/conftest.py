import gzip
import hashlib
import json
import os
import pathlib
import subprocess

import psycopg
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures"


def _env() -> dict:
    env = dict(os.environ)
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env.setdefault(key, value)
    return env


# Tests run against their own database, never the working one.
#
# Not fastidiousness: the row-count guard derives its expectation from the days
# already loaded, so a warehouse holding real history (median ~650 instruments)
# correctly refuses a 6-row fixture day as truncated. The fixture also shares a
# date with real captured data, and loading it would replace that day. Both
# problems vanish with a separate database and neither can be papered over in
# the assertions.
TEST_DATABASE = "dse_test"


@pytest.fixture(scope="session")
def env():
    base = _env()

    admin = psycopg.connect(
        host=base["DSE_PG_HOST"], port=base["DSE_PG_PORT"], dbname="postgres",
        user=base["DSE_PG_USER"], password=base["DSE_PG_PASSWORD"], autocommit=True,
    )
    with admin:
        with admin.cursor() as cursor:
            cursor.execute(f'drop database if exists "{TEST_DATABASE}" with (force)')
            cursor.execute(f'create database "{TEST_DATABASE}"')

    testing = dict(base, DSE_PG_DATABASE=TEST_DATABASE)

    with psycopg.connect(
        host=testing["DSE_PG_HOST"], port=testing["DSE_PG_PORT"], dbname=TEST_DATABASE,
        user=testing["DSE_PG_USER"], password=testing["DSE_PG_PASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            for layer in ("raw", "staging", "intermediate", "marts"):
                cursor.execute(f"create schema if not exists {layer}")
        connection.commit()

    return testing


@pytest.fixture(scope="session")
def landing(tmp_path_factory):
    """Gzip the committed fixtures into a landing directory shaped like the real one.

    The fixtures are stored as plain HTML so they stay reviewable in diffs; the
    loader still reads gzip, so compressing here keeps the real code path under test.
    """
    directory = tmp_path_factory.mktemp("landing")
    for source in sorted(FIXTURES.glob("day_end_*.html")):
        date = source.stem.removeprefix("day_end_")
        payload = source.read_bytes()
        (directory / f"{date}.html.gz").write_bytes(gzip.compress(payload))
        (directory / f"{date}.json").write_text(
            json.dumps({
                "trade_date": date,
                "trading_day": True,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "file": f"{date}.html.gz",
            })
        )
    return directory


@pytest.fixture(scope="session")
def warehouse(landing, env):
    """Load every landed fixture and build the models. Yields a live connection."""
    subprocess.run(
        ["uv", "run", "python", "-m", "ingestion.load_day_end", "--landing", str(landing)],
        cwd=REPO, env=env, check=True, capture_output=True, text=True,
    )
    built = subprocess.run(
        ["uv", "run", "dbt", "build"],
        cwd=REPO / "dbt", env=env, capture_output=True, text=True,
    )
    if built.returncode != 0:
        pytest.fail(f"dbt build failed:\n{built.stdout}\n{built.stderr}")

    with psycopg.connect(
        host=env["DSE_PG_HOST"], port=env["DSE_PG_PORT"], dbname=env["DSE_PG_DATABASE"],
        user=env["DSE_PG_USER"], password=env["DSE_PG_PASSWORD"],
    ) as connection:
        yield connection


@pytest.fixture(scope="session")
def client(warehouse, env):
    """An HTTP client against the API, with the warehouse already built.

    Depends on `warehouse` so the data is loaded before the app is asked for it.
    """
    from fastapi.testclient import TestClient

    for key in ("DSE_PG_HOST", "DSE_PG_PORT", "DSE_PG_DATABASE", "DSE_PG_USER", "DSE_PG_PASSWORD"):
        os.environ[key] = env[key]

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
