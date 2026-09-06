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


@pytest.fixture(scope="session")
def env():
    return _env()


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
