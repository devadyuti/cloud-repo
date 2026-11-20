# Design

## Layout
```
devicefarm-demo/
  tests/test_sample_app.py   # Appium + pytest
  tests/conftest.py          # driver fixture (Device Farm env vars, local fallback)
  requirements.txt           # Appium-Python-Client, pytest
  testspec.yml               # Device Farm custom test env spec
  scripts/run_demo.sh        # create project, pool, uploads, run, poll
  scripts/fetch_results.sh   # download artifacts by run ARN
  scripts/package.sh         # build test_bundle.zip
  ci/buildspec.yml
  ci/github-actions.yml
  Makefile
  RUNBOOK.md
  README.md
```

## Key decisions
- Appium Python + pytest: most common framework, framework-agnostic demo story.
- Driver fixture reads Device Farm-provided env (DEVICEFARM_DEVICE_PLATFORM_NAME, DEVICEFARM_APP_PATH, etc.); Appium server at http://127.0.0.1:4723.
- testspec phases: install (pip install -r requirements), pre_test (start appium), test (pytest --junitxml=$DEVICEFARM_LOG_DIR/junit.xml), post_test.
- CLI flow: `aws devicefarm create-project` -> `create-device-pool` (rules: PLATFORM=ANDROID, AVAILABILITY=HIGHLY_AVAILABLE, maxDevices=3) -> `create-upload` (ANDROID_APP, APPIUM_PYTHON_TEST_PACKAGE, APPIUM_PYTHON_TEST_SPEC) -> curl PUT to presigned URL -> poll `get-upload` -> `schedule-run` -> poll `get-run`.
- State (ARNs) cached in `.demo_state.json` for idempotency.
