# Runbook: Device Farm demo for Example Bank (Wed 11 Nov 2026)

## Prerequisites
- AWS CLI v2 profile with Device Farm access; `aws sts get-caller-identity` works.
- Python 3.11, `jq`, `zip`, `curl`, `ruff`.
- Browser logged into the console at Device Farm, region **us-west-2**.

## Tonight: dry run (~20 min)
1. `make lint && make package` and check zip lists `tests/`, `requirements.txt`, `wheelhouse/`.
2. `make run`. Expect upload ~1 min, queue + run ~5-10 min, result `PASSED`.
3. `make results`. Confirm video, `junit.xml`, `appium.log` and screenshots exist.
4. Keep the passed run open in a browser tab (backup) and note the console URL.
5. Open a remote access session once (Device Farm > project > Remote access) so
   you know the device picker; stop it after 1 min to save cost.
6. If a test fails: check `appium.log` / test spec output in the job's Files tab.

## Live demo (~25 min)
| Time | Step | What to show |
|------|------|--------------|
| 0-3 | Intro | Real devices, not emulators; managed fleet; pay per device minute |
| 3-7 | Upload | `NO_WAIT=1 make run`: project, pool (3 Android), app + bundle + spec uploads |
| 7-10 | Test spec | `testspec.yml`: custom env, Appium 2, pytest, JUnit output |
| 10-15 | Results | Open the pre-run tab: per-device pass/fail, video, screenshots, logs, perf |
| 15-20 | Remote access | Session started before the demo (`make remote`): tap through the app live, then `make remote-test` to drive the same phone from the laptop; `make remote-stop` |
| 20-25 | CI/CD | `ci/buildspec.yml` and `ci/github-actions.yml`: same script on every PR |
| end | Live run | Back to the run started at minute 3, should be done or close |

## Banking talking points
- **Region / data residency:** Device Farm public fleet runs in us-west-2 only.
  Use synthetic test data; no customer PII in test builds. Artifacts are stored
  in the service and can be deleted; downloaded results go to your own S3/CI.
- **VPC connectivity:** VPC-ENI config lets devices reach private test
  backends (internal APIs, staging) without exposing them publicly.
- **Root / jailbreak detection:** public devices are not rooted; test that your
  app's detection does not false-positive. Use private devices for controlled cases.
- **Certificate pinning:** pinning works on real devices; for test builds use a
  debug network config or pinned staging certs rather than disabling pinning in prod.
- **Private devices:** dedicated devices for your account, device instance
  profiles, device clean-up between sessions, custom OS/carrier needs.
- **Cleanup:** devices are wiped after each session; no data left behind.
- **Real-OS behaviour:** our dry run found Android 14+ refusing to install an
  app targeting SDK 22, and Android 15 showing an "older version of Android"
  warning over the app, while Android 13 didn't. Emulators and single-device
  testing miss this kind of OS-version difference.

Check the latest Device Farm docs before quoting specifics on VPC-ENI and private devices.

## Showing a failure (run 14:16, Pixel 9 Pro, Android 15)
1. Console: the run shows Galaxy S23 (Android 13) passed, both Pixels (Android 15) failed.
   Same app, same tests; only the OS differs.
2. Open Pixel 9 Pro > Tests suite > Files: `Test_spec_output` shows `NoSuchElementException`
   for all 3 tests. The menu button couldn't be found.
3. Screenshots tab: the launch screenshot shows Android 15's "This app was built for an
   older version of Android" dialog covering the app.
4. Video tab: the dialog stays up while each test times out.
5. Terminal: `make why RUN=<run-arn>` gives the same story in one screen.
6. The fix: `conftest.py` dismisses the dialog. Message: Device Farm found an OS-specific
   problem that a single Android 13 test phone would never show.

## Likely questions
- **Can we choose exact devices?** Yes. Device pool rules can pin exact devices
  (`ARN IN [...]`) or filter by model, OS version or manufacturer. Rules can also be set
  per run with `schedule-run --device-selection-configuration`. The demo pool is dynamic
  on purpose ("any 3 highly available Android"). For release testing, pin your top
  devices from app analytics. Private devices give dedicated hardware. Caveat: a pinned
  device that's busy makes the run wait in the queue.

## Remote access tips
- Run `make remote-launch` right after `make remote` so the app is open before you share the screen.
- The app's "Crashes/Bugs" menu item crashes the app on purpose. You can avoid it, or use it
  to show that the crash is recorded in the session's device logs. Then `make remote-launch`.
- The app is in the app drawer (swipe up), not on the home screen.

## Backup plan
- Run slow or stuck in queue: show the dry-run tab from tonight, then return.
- Upload fails: `aws devicefarm get-upload --arn <arn>` metadata shows the reason;
  fall back to the dry-run results.
- Network issues: walk through `results/` downloaded tonight (video + screenshots).
- Remote access unavailable: show recorded video from the dry run.
