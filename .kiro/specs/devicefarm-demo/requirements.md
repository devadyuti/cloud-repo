# Requirements: Device Farm demo kit

## R1 Sample Appium test package
As an SA, I want a minimal Appium Python test suite so I can run automated tests on real devices.
- WHEN the package is built THEN it SHALL produce `test_bundle.zip` in the Device Farm Appium Python format (tests/, requirements.txt, wheelhouse/ if needed).
- The suite SHALL contain 3 tests on the sample Android app: app launches, navigate a menu item, enter text in a form and assert result.
- Each test SHALL take a screenshot at key steps.

## R2 Custom test spec
- A `testspec.yml` SHALL run pytest with Appium on Device Farm custom environment and output JUnit results.

## R3 CLI automation script
As an SA, I want one script to demo CI/CD usage.
- `run_demo.sh` SHALL: create/reuse a project, create a device pool (max 3 devices, Android), upload app + test bundle + testspec, wait for uploads SUCCEEDED, schedule a run, poll status, print result summary and console URL.
- The script SHALL be idempotent and use us-west-2.
- A `fetch_results.sh` SHALL download artifacts (video, logs, screenshots) for a given run ARN.

## R4 CI/CD example
- Provide a sample `buildspec.yml` (CodeBuild) and a GitHub Actions workflow calling `run_demo.sh`.

## R5 Demo runbook
- `RUNBOOK.md` SHALL include: prerequisites, pre-demo dry run steps (tonight), live demo steps with timings (upload, run, results, remote access, CI/CD), talking points for banking (region/residency, VPC, root/jailbreak detection, cert pinning, private devices), and a backup plan if a live run is slow.

## R6 Quality
- Local validation: `make package` builds the zip; `make lint` passes (ruff); README explains everything in <1 page.
