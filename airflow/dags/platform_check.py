"""A DAG that proves the platform is wired together.

It does nothing useful on purpose. Its job is to fail loudly when one of the
connections the real pipeline depends on is broken -- the warehouse, the project
code mounted into the image, and dbt in its separate virtualenv -- so that a
genuine pipeline failure is never confused with a platform that was never
plugged in properly.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess

from airflow.sdk import dag, task


@dag(
    dag_id="platform_check",
    description="Confirms the warehouse, the project code and dbt are reachable",
    schedule=None,
    start_date=dt.datetime(2026, 9, 1),
    catchup=False,
    tags=["platform"],
)
def platform_check():

    @task
    def warehouse_is_reachable() -> str:
        import psycopg

        with psycopg.connect(
            host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
            dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
            password=os.environ["DSE_PG_PASSWORD"],
        ) as connection, connection.cursor() as cursor:
            cursor.execute(
                """select string_agg(nspname, ', ' order by nspname)
                   from pg_namespace
                   where nspname in ('raw', 'staging', 'intermediate', 'marts')"""
            )
            layers = cursor.fetchone()[0]
        if layers != "intermediate, marts, raw, staging":
            raise RuntimeError(f"warehouse is missing layer schemas, found: {layers}")
        return layers

    @task
    def project_code_is_importable() -> str:
        """The loader is imported, not shelled out to, so a broken mount fails here."""
        from ingestion.load_day_end import SOURCE_COLUMNS, parse  # noqa: F401

        return f"loader importable, {len(SOURCE_COLUMNS)} source columns"

    @task
    def dbt_is_runnable() -> str:
        finished = subprocess.run(
            [os.environ["DBT_EXECUTABLE"], "debug", "--project-dir", "/opt/project/dbt"],
            capture_output=True, text=True,
        )
        if finished.returncode != 0:
            raise RuntimeError(f"dbt debug failed:\n{finished.stdout[-2000:]}")
        return "dbt connected to the warehouse"

    warehouse_is_reachable() >> project_code_is_importable() >> dbt_is_runnable()


platform_check()
