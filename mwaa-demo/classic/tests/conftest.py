"""Pytest configuration for DAG tests.

Sets up the environment so DAG modules can be imported without a running
Airflow instance or an initialised Airflow database.

Environment variables are set at module level (before any fixture runs)
because Airflow reads them at import time during `settings.initialize()`.
"""

import os
import sys
import tempfile
from pathlib import Path

# --- Environment setup (must happen before any Airflow import) ---
_tmp_home = tempfile.mkdtemp(prefix="airflow_test_")
os.environ["AIRFLOW_HOME"] = _tmp_home
os.environ["AIRFLOW__CORE__EXECUTOR"] = "SequentialExecutor"
os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "False"
os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = (
    f"sqlite:///{_tmp_home}/airflow.db"
)
# Disable the structured logging that causes circular import issues in test
os.environ["AIRFLOW__LOGGING__LOGGING_CONFIG_CLASS"] = ""
os.environ["AIRFLOW__CORE__COLORED_CONSOLE_LOG"] = "False"

# --- Add dags/ to sys.path so DAG modules can be imported ---
_dags_dir = str(Path(__file__).resolve().parent.parent / "dags")
if _dags_dir not in sys.path:
    sys.path.insert(0, _dags_dir)
