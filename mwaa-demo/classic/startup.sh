#!/bin/sh
# MWAA startup script — runs on every scheduler, worker, and webserver before Airflow starts.
# Creates an isolated virtualenv for dbt Core so dbt's dependency pins never clash with
# Airflow's constraints. The dbt_anycompany_analytics DAG (Cosmos) calls $DBT_EXECUTABLE_PATH.
#
# Keep versions in sync with scripts/build_dbt_manifest.sh and the README.

export DBT_VENV_PATH="${AIRFLOW_HOME}/dbt_venv"
export DBT_EXECUTABLE_PATH="${DBT_VENV_PATH}/bin/dbt"

# Workers run dbt and schedulers parse DAGs; the webserver needs neither.
if [ "${MWAA_AIRFLOW_COMPONENT}" != "webserver" ]; then
  echo "Installing dbt Core into ${DBT_VENV_PATH}"
  python3 -m venv "${DBT_VENV_PATH}"
  "${DBT_VENV_PATH}/bin/pip" install --quiet --no-cache-dir \
    dbt-core==1.12.6 \
    dbt-redshift==1.11.1
  "${DBT_EXECUTABLE_PATH}" --version
fi
