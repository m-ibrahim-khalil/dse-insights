# Airflow image with this project's ingestion code and dbt available.
#
# dbt lives in its own virtualenv rather than alongside Airflow. dbt-core and
# Airflow pin conflicting versions of several shared libraries, and resolving
# them into one environment produces an install that satisfies neither. Keeping
# them apart is the documented way out, and it means an Airflow upgrade cannot
# silently change the dbt that builds the warehouse.

FROM apache/airflow:3.3.1-python3.12

# The DAG imports the loader directly, so its dependencies belong in Airflow's
# own environment. These are deliberately few -- Python only fetches and loads.
RUN pip install --no-cache-dir \
      "psycopg[binary]==3.3.5" \
      "beautifulsoup4==4.14.2" \
      "certifi"

# The image runs as the unprivileged airflow user, which cannot write to /opt,
# so the directory is created with ownership before dropping back.
USER root
RUN mkdir -p /opt/dbt-venv && chown airflow:root /opt/dbt-venv
USER airflow

# Pinned to the versions the test suite and the two-year load were proven against.
RUN python -m venv /opt/dbt-venv \
 && /opt/dbt-venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/dbt-venv/bin/pip install --no-cache-dir \
      "dbt-core==1.12.3" \
      "dbt-postgres==1.11.0"

ENV DBT_EXECUTABLE=/opt/dbt-venv/bin/dbt \
    PYTHONPATH=/opt/project
