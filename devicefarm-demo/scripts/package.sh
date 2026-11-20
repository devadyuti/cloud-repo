#!/usr/bin/env bash
# Build build/test_bundle.zip in Device Farm Appium Python format:
#   tests/  requirements.txt  wheelhouse/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
STAGE="$BUILD/bundle"

rm -rf "$STAGE" "$BUILD/test_bundle.zip"
mkdir -p "$STAGE/wheelhouse"

# Download wheels for the Device Farm host (linux x86_64, CPython 3.11),
# independent of the machine we package on.
python3 -m pip download -q \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 --platform any \
  --python-version 3.11 --implementation cp \
  -d "$STAGE/wheelhouse" -r "$ROOT/requirements.txt"

cp "$ROOT/requirements.txt" "$STAGE/"
mkdir -p "$STAGE/tests"
cp "$ROOT"/tests/*.py "$STAGE/tests/"

(cd "$STAGE" && zip -qr "$BUILD/test_bundle.zip" tests requirements.txt wheelhouse)

echo "Built $BUILD/test_bundle.zip"
unzip -l "$BUILD/test_bundle.zip" | grep -E 'tests/|requirements.txt' || true
echo "Wheels: $(ls "$STAGE/wheelhouse" | wc -l | tr -d ' ')"
