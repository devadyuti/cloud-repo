# Requirements delta: Airflow 2.10.3 → 2.11.2

This is the artifact to walk the customer through. The gap between these two
files *is* their upgrade problem.

## The two files

| Package | 2.10.3 (Python 3.11) | 2.11.2 (Python 3.12) | Change |
|---|---|---|---|
| `apache-airflow-providers-amazon` | `9.0.0` | `9.22.0` | 22 minor versions |
| `apache-airflow-providers-http` | `4.13.2` | `6.0.0` | **major**, crosses 5.x |
| Python runtime | 3.11 | 3.12 | **interpreter change** |

Constraint URLs:

- `constraints-2.10.3/constraints-3.11.txt`
- `constraints-2.11.2/constraints-3.12.txt`

Both sets of pins were read directly from those constraint files, so each pin
agrees with its own constraint set.

## Finding 1 — the source requirements file was already broken

`mwaa-demo/classic/requirements.txt` (the other engagement's file, left
untouched) declares one constraint set and then pins versions that set does not
contain:

| | declared/pinned | what the constraint file actually resolves to |
|---|---|---|
| constraint | `constraints-2.10.4/constraints-3.11.txt` | — |
| `providers-amazon` | pinned `9.6.0` | `9.1.0` |
| `providers-http` | pinned `4.12.0` | `4.13.3` |

Verified by fetching the constraint file. When an explicit pin contradicts
`--constraint`, pip fails to resolve, and on MWAA that surfaces as a failed
environment create or update — not as an obvious dependency error.

Also: **MWAA has no 2.10.4.** The supported 2.10 builds are 2.10.1 and 2.10.3.
So that file pointed a 2.10.3-or-2.10.1 environment at constraints for a
version MWAA never offered.

**Question for the customer:** what constraint URL is in their current
`requirements.txt`, and does it match their actual environment version? If it
disagrees, they were carrying a latent failure into the upgrade.

## Finding 2 — Python 3.11 → 3.12 is the real hazard

2.10.x runs Python 3.11; 2.11.x and every 3.x run Python 3.12. Any dependency
without a 3.12-compatible wheel, or anything compiled against 3.11, fails on
the 2.11 side. This is the most likely cause of their rolled-back upgrade and
it is invisible if you only look at the Airflow version numbers.

## Finding 3 — the HTTP provider crosses a major version

`4.13.2 → 6.0.0`. Worth checking the 5.0.0 and 6.0.0 changelogs before the
upgrade. The good news for *these* DAGs: `cdc_ingestion.py` and
`external_system_integration.py` already use `HttpOperator` (the modern name)
rather than the long-deprecated `SimpleHttpOperator`, so the most common
breakage here does not apply.

Not independently verified: whether `HttpOperator` exists in the `4.12.0` that
the source file pinned. It was introduced in the 4.13.x line, so the source
combination may have been failing DAG import as well. Our 2.10.3 file pins
`4.13.2`, which does contain it.

## Finding 4 — the DAGs are Airflow 2 style, which is good news

Despite `classic/stacks/mwaa_stack.py` pinning `airflow_version="3.2.1"`, all
seven DAGs use classic Airflow 2 imports (`from airflow import DAG`,
`airflow.operators.python`, `airflow.utils.task_group`). None use `airflow.sdk`
or Airflow 3 Asset APIs. They should import cleanly on 2.10.3 and 2.11.2 with
no changes.

They will **not** survive the later 3.x hop unchanged. Known breakages to fix
at that point:

- `from airflow.operators.python import PythonOperator, BranchPythonOperator`
  → moves to `airflow.providers.standard.operators.python` in Airflow 3.
- `from airflow.utils.task_group import TaskGroup` → moves under the Task SDK.
- `from airflow.models import Variable` → Task SDK access pattern in Airflow 3.

That list is the customer's 3.x migration checklist, and it is short — which is
the encouraging part of the story.

## Upgrade sequence (do not skip the ordering)

1. Upload `requirements-2.11.2.txt` as `requirements.txt`. Note the new S3
   object version.
2. Edit the environment and change the Airflow version to `2.11.2` **and** the
   requirements version to the one from step 1, in the **same** update.
3. Watch `UPDATING` → `CREATING_SNAPSHOT` → `UPDATING` → `AVAILABLE`.

Changing the Airflow version while leaving the previous requirements version
selected installs 3.11-era pins onto a 3.12 interpreter. That is the failure
mode, reproduced on purpose if you want to show it.
