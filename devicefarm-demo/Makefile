.PHONY: apk package lint run results why remote remote-launch remote-test remote-stop clean

apk:  ## Sample APK re-targeted to SDK 24 (installs on Android 14+)
	./scripts/patch_apk.sh

package:  ## Build build/test_bundle.zip
	./scripts/package.sh

lint:  ## ruff + bash syntax check
	ruff check tests
	ruff format --check tests
	for f in scripts/*.sh; do bash -n $$f || exit 1; done

run: apk package  ## Upload and run on Device Farm (us-west-2)
	./scripts/run_demo.sh

results:  ## Download artifacts for the last run
	./scripts/fetch_results.sh

why:  ## Explain failures of the last run per device (RUN=<arn> for another run)
	./scripts/explain_failures.sh $(RUN)

remote:  ## Start a remote access session (DEVICE_NAME="Pixel 9" to pick)
	./scripts/remote_session.sh start

remote-launch:  ## (Re)open the sample app in the remote session, e.g. after a crash
	APPIUM_URL="$$(jq -r .remote_driver_endpoint .demo_state.json)" .venv/bin/python scripts/remote_launch.py

remote-test:  ## Run pytest from this laptop against the remote session
	./scripts/remote_session.sh test

remote-stop:  ## Stop the remote session (stops billing)
	./scripts/remote_session.sh stop

clean:
	rm -rf build results screenshots .pytest_cache .venv
