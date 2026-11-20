# AWS Device Farm demo kit (Example Bank, 11 Nov 2026)

## What this demo is about

Mobile banking apps have to work on the phones customers actually use: many
manufacturers, screen sizes and Android versions. Testing on emulators or a
handful of office phones misses problems that only show up on specific real
devices or OS versions.

**AWS Device Farm** is a managed fleet of real phones and tablets in AWS
(`us-west-2`). You upload your app and your tests, choose devices, and Device
Farm runs them and records video, logs, screenshots and performance data. You
can also open a **remote access session** and use a real phone from your
browser.

This kit shows three things end to end, using the public AWS sample Android app
and synthetic data only:

1. **Automated testing on real devices.** Three Appium + pytest tests run in
   parallel on up to 3 Android devices, and the results (video, screenshots,
   logs, JUnit) are downloaded.
2. **Remote access.** You tap through the app on a real phone in the browser,
   then drive that same phone with the same tests from your laptop.
3. **CI/CD.** The same script runs from CodeBuild or GitHub Actions on every
   change.

### How it fits together

```
 laptop / CI                              AWS Device Farm (us-west-2)
 ───────────                              ───────────────────────────
 tests/*.py ─┐
 requirements ├─ package.sh ─► test_bundle.zip ─┐
 wheelhouse  ─┘                                 │  create-upload + PUT
 sample APK ── patch_apk.sh ─► app-debug.apk ───┼─────────────────────► project
 testspec.yml ──────────────────────────────────┘                        │
                                                                         ▼
 run_demo.sh ── schedule-run ──────────────────────────────► device pool (3 Android)
      │                                                       each device:
      │  poll get-run                                         install app, start Appium,
      ▼                                                       pytest, record video/logs
 summary + console URL ◄─────────────────────────────────────────────────┘
 fetch_results.sh ─► results/<run-id>/<job>/{file,screenshot,log}

 remote_session.sh start ─► remote access session (1 phone, browser view)
 remote_launch.py / pytest ── Appium over remoteDriverEndpoint ─► same phone
```

### What the tests do

The app is the [AWS Device Farm sample app for Android](https://github.com/aws-samples/aws-device-farm-sample-app-for-android)
(`com.amazonaws.devicefarm.android.referenceapp`). The login credentials are
`admin` / `password`, which are built into the sample app.

| Test | Steps | Screenshots |
|------|-------|-------------|
| `test_app_launches` | App opens; menu button is visible | `launched` |
| `test_navigate_to_login_page` | Menu ☰ > "Login Page"; login button visible | `login-page` |
| `test_login_form_shows_result` | Enter `admin`/`password`, tap login, expect "You are logged on as admin" | `form-filled`, `result` |

## Prerequisites

| Tool | Why |
|------|-----|
| AWS CLI v2, default profile (or env credentials) with `devicefarm:*` | All Device Farm calls. The scripts force `us-west-2`, so a different `AWS_REGION` in your shell is ignored |
| Python 3.11 | Matches the Python on the Device Farm test host; used for packaging and local runs |
| `jq`, `zip`, `curl` | State file, bundle, uploads |
| `apktool` (`brew install apktool`), JDK (`keytool`, `jarsigner`) | Re-targeting the sample APK (see `make apk`) |
| `ruff` | `make lint` only |

Check access with `aws sts get-caller-identity`.

## Quick start

```bash
cd devicefarm-demo
make run           # build everything, run on 3 real devices, print results (~5-8 min)
make results       # download video, logs, screenshots of that run

make remote        # open a real phone in a remote access session (~2 min to start)
make remote-launch # bring the app to the foreground
make remote-test   # drive that phone with the same 3 tests from your laptop
make remote-stop   # stop the session (stops billing)
```

## Commands explained

### `make apk`: prepare the app
Runs `scripts/patch_apk.sh`.

- **Why it exists:** the prebuilt sample APK targets Android SDK 22. Android 14
  and later refuse to install it (`INSTALL_FAILED_DEPRECATED_SDK_VERSION`).
- **What it does:** downloads the APK from GitHub into
  `build/app-debug-original.apk`, unpacks it with `apktool`, sets
  `targetSdkVersion` to 24 (change with `TARGET_SDK=`), rebuilds it, and signs
  it with a throwaway debug key (`build/debug.keystore`).
- **Output:** `build/app-debug.apk`.
- **Side effect:** with target SDK 24 or higher, Android asks for permissions at
  runtime. The tests grant them automatically (`autoGrantPermissions`).
- Demo use only. For a real app, use your own release build.

### `make package`: build the test bundle
Runs `scripts/package.sh`.

- **What it does:** creates `build/test_bundle.zip` in the Device Farm "Appium
  Python" format:
  - `tests/`: the test files
  - `requirements.txt`: `Appium-Python-Client` and `pytest`, pinned
  - `wheelhouse/`: those packages and their dependencies, pre-downloaded
- **Why `wheelhouse/`:** the wheels are downloaded for Linux x86_64 and
  Python 3.11, whatever machine you build on, so the device host can install
  them offline.
- **Output:** the zip's contents and the wheel count.

### `make lint`: local quality checks
Runs `ruff check` and `ruff format --check` on `tests/`, then `bash -n` on every
script. Needs no AWS access.

### `make run`: the full automated run
Runs `make apk` and `make package`, then `scripts/run_demo.sh`.

1. **Project:** reuses `example-bank-devicefarm-demo`, or creates it with a
   10-minute job timeout (`create-project`).
2. **Device pool:** reuses `android-top3`, or creates it (`create-device-pool`).
   The rules are platform Android and availability "highly available", with a
   maximum of 3 devices. Device Farm picks the actual models, so they can vary
   between runs.
3. **Uploads:** for the APK (`ANDROID_APP`), the bundle
   (`APPIUM_PYTHON_TEST_PACKAGE`) and `testspec.yml`
   (`APPIUM_PYTHON_TEST_SPEC`):
   - `create-upload` returns a presigned S3 URL
   - `curl -T` sends the file to it
   - the script polls `get-upload` until the status is `SUCCEEDED`
   - Device Farm validates each file here
4. **Run:** `schedule-run` with test type `APPIUM_PYTHON`, video capture on, and
   a 10-minute job timeout.
5. **Poll:** `get-run` every 20 seconds until `COMPLETED`.
6. **Summary:**
   - pass/fail counters
   - a table of the devices with each one's OS, result and minutes billed
   - the console URL for the run
   - The script exits non-zero if the run didn't pass, so CI fails.

On each device, Device Farm follows `testspec.yml`:

| Phase | What happens |
|-------|--------------|
| `install` | `devicefarm-cli use python 3.11` and `use appium 2`; offline `pip install --user` from `wheelhouse/` |
| `pre_test` | Start the Appium server (UiAutomator2) on `127.0.0.1:4723/wd/hub` with the device's details; wait until it answers |
| `test` | `python -m pytest tests/ -v --junitxml=$DEVICEFARM_LOG_DIR/junit.xml` |
| `post_test` | Log completion; everything in `$DEVICEFARM_LOG_DIR` is kept as an artifact |

**State and idempotency:** ARNs are cached in `.demo_state.json`, so running it
again reuses the project and pool. Only new uploads and a new run are created.

**Options:**

| Variable | Effect |
|----------|--------|
| `NO_WAIT=1` | Start the run and exit without polling (useful live) |
| `APP_PATH=/path/app.apk` | Test a different APK |
| `BUNDLE_PATH=` | Use a different test bundle |
| `PROJECT_NAME=` | Use a different project name |
| `POOL_NAME=` | Use a different device pool name |

### `make results`: download artifacts
Runs `scripts/fetch_results.sh [RUN_ARN]`. Without an argument it uses the last
run in `.demo_state.json`.

- **What it does:** lists the `FILE`, `SCREENSHOT` and `LOG` artifacts and
  downloads them into `results/<run-id>/<job-id>/{file,screenshot,log}/`.
- **What you get:**
  - video (`.mp4`)
  - logcat
  - `Test_spec_output` (the full console output of the test spec; start here
    when debugging)
  - your screenshots
  - Customer Artifacts (`junit.xml`, `appium.log`)
- **Device map:** `results/<run-id>/devices.tsv` maps job ids to device names.

### `make why`: explain why a run failed
Runs `scripts/explain_failures.sh [RUN_ARN]`. Defaults to the last run; pick
another with `make why RUN=<run-arn>`. Downloads artifacts first if needed.

For each device it prints:
- the result and Android version
- Device Farm's own message for the failed lifecycle suite (Setup, Tests or
  Teardown). For example, an APK install error shows up under Setup.
- each failed pytest test with its first error line, read from `junit.xml`
  (Device Farm itself only says "Tests failed" for custom-environment runs)
- the screenshot, video and test spec log to open next

### `make remote`: start a remote access session
Runs `scripts/remote_session.sh start`.

1. Picks a device that runs Android, supports remote access and is highly
   available. Filter by name with `DEVICE_NAME="Galaxy S23"` (substring match).
2. Uploads the APK.
3. Creates the session with `create-remote-access-session` and waits until it
   is `RUNNING`, which takes about 2 minutes.
4. Installs the app with `install-to-remote-access-session`.
5. Saves the session ARN and its Appium endpoint (`remoteDriverEndpoint`) in
   `.demo_state.json`.

Then open the console: Device Farm > Mobile device testing >
`example-bank-devicefarm-demo` > Remote access > the running session. Billing is per
minute until you stop the session.

### `make remote-launch`: open the app in the session
Runs `scripts/remote_launch.py`.

- **Why you need it:** the app installs but doesn't open by itself, and on
  Samsung it's only in the app drawer.
- **What it does:** connects to the session's Appium endpoint, checks
  `is_app_installed`, starts `MainActivity`, then disconnects. The session and
  the app stay open.
- **Prints:** `Installed: True` and `Foreground package: ...referenceapp`.
- **When to use it:** whenever the app is closed, for example after tapping the
  sample app's "Crashes/Bugs" menu item, which crashes the app on purpose.

### `make remote-test`: drive the remote phone from your laptop
Runs `scripts/remote_session.sh test`.

- **What it does:** creates `.venv` (Python 3.11) if needed, then runs the same
  `pytest tests -v` with `APPIUM_URL` set to the session's endpoint. You watch
  the phone in the browser while the tests run (about 1 minute).
- **Where screenshots go:** `screenshots/`.
- **Why it works:** `conftest.py` sees there are no `DEVICEFARM_*` variables
  and uses its "local" capabilities. It sends no `udid` and no
  `platformVersion`, because the remote endpoint rejects those.

### `make remote-stop`: stop the session
Runs `scripts/remote_session.sh stop`. Stops the session, which also stops
billing, and clears the saved endpoint. You can also click **Stop session** in
the console.

### `make clean`
Removes `build/`, `results/`, `screenshots/`, `.pytest_cache` and `.venv`. It
doesn't touch AWS resources or `.demo_state.json`.

## CI/CD examples

| File | What it shows |
|------|---------------|
| `ci/buildspec.yml` | CodeBuild: Python 3.11, `make package`, `run_demo.sh`, then `fetch_results.sh`. Results are published as build artifacts and a JUnit report. The CodeBuild role needs `devicefarm:*` on the project |
| `ci/github-actions.yml` | GitHub Actions on PRs to `main` or a manual trigger. Uses an OIDC role (`secrets.DEVICEFARM_ROLE_ARN`), no long-lived keys. Same steps, results uploaded as a workflow artifact |

Both run `run_demo.sh`, which exits non-zero on a failed run, so a failing
device test blocks the pipeline.

## Files

| Path | Purpose |
|------|---------|
| `tests/test_sample_app.py` | The 3 tests |
| `tests/conftest.py` | Appium driver fixture: uses Device Farm details on the device host, local/remote capabilities elsewhere; grants permissions; dismisses Android 14+ "built for an older version of Android" dialog; `screenshot()` helper |
| `testspec.yml` | Device Farm custom environment spec (Amazon Linux 2 host) |
| `requirements.txt` | Pinned test dependencies |
| `scripts/patch_apk.sh` | Re-target and re-sign the sample APK |
| `scripts/package.sh` | Build `test_bundle.zip` |
| `scripts/run_demo.sh` | Project, pool, uploads, run, poll, summary |
| `scripts/fetch_results.sh` | Download run artifacts |
| `scripts/remote_session.sh` | Remote access `start` / `test` / `stop` |
| `scripts/remote_launch.py` | Check the app is installed and open it in the session |
| `ci/` | CodeBuild and GitHub Actions examples |
| `RUNBOOK.md` | Dry run, live demo timing, banking talking points, backup plan |
| `.demo_state.json` | Cached ARNs and remote endpoint (git-ignored; contains a presigned URL, don't share) |

## What we learned in the dry run (good demo talking points)

| Problem found | Cause | Fix in this kit |
|---------------|-------|-----------------|
| App wouldn't install on Pixel 8 (Android 14) and Pixel 10 Pro XL (Android 16) | Sample APK targets SDK 22; Android 14+ requires a target of at least 23–24 | `make apk` sets target SDK to 24 |
| Tests never ran | Python 3.11 from `devicefarm-cli` has no `ensurepip`/`virtualenv`, so no venv could be created | `testspec.yml` installs with `pip install --user` and runs `python -m pytest` |
| All tests failed on Android 15, passed on Android 13 | Android 15 shows "This app was built for an older version of Android" over the app | `conftest.py` taps OK on that dialog if it appears |
| App "disappeared" in remote session | "Crashes/Bugs" menu item crashes the app on purpose; new installs aren't on the Samsung home screen | `make remote-launch` |

The same app behaved differently on different OS versions of real devices.
That's the problem Device Farm is built to find before your customers do.

## Cost and cleanup

- **Billing:** Device Farm bills per device minute.
  - A `make run` is about 3 devices × 1–2 minutes.
  - A remote session bills until you stop it.
- **Cleanup:** always run `make remote-stop` after a session.
- **After the demo:** delete everything with
  `aws devicefarm delete-project --region us-west-2 --arn "$(jq -r .project_arn .demo_state.json)"`.
  This also deletes its runs, uploads and artifacts, and can't be undone.

## Troubleshooting

| Symptom | Where to look |
|---------|---------------|
| Upload `FAILED` | `aws devicefarm get-upload --region us-west-2 --arn <arn> --query upload.metadata` |
| Run failed in Setup | `list-suites` message (e.g. APK install errors) |
| Tests failed | `results/<run>/<job>/file/Test_spec_output-*.txt`, then `appium.log` in Customer Artifacts, then screenshots |
| `Could not connect to devicefarm.us-east-1` | You ran `aws devicefarm` by hand with another region set; add `--region us-west-2` |
| Remote session shows no app | `make remote-launch` |
