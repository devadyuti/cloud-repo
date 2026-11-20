#!/usr/bin/env bash
# The prebuilt sample APK targets SDK 22, which Android 14+ refuses to install
# (INSTALL_FAILED_DEPRECATED_SDK_VERSION). Rewrite targetSdkVersion to 24 and
# re-sign with a throwaway debug key. Demo use only.
# Needs: apktool (brew install apktool), JDK keytool + jarsigner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
SRC_APK="${1:-$BUILD/app-debug-original.apk}"
OUT_APK="$BUILD/app-debug.apk"
TARGET_SDK="${TARGET_SDK:-24}"
KEYSTORE="$BUILD/debug.keystore"
SAMPLE_APK_URL="https://github.com/aws-samples/aws-device-farm-sample-app-for-android/raw/master/prebuilt/app-debug.apk"

mkdir -p "$BUILD"
[[ -f "$SRC_APK" ]] || curl -sfL -o "$SRC_APK" "$SAMPLE_APK_URL"

rm -rf "$BUILD/apk-src"
apktool d -q -f "$SRC_APK" -o "$BUILD/apk-src"
sed -i '' -E "s/(targetSdkVersion: ).*/\1'$TARGET_SDK'/" "$BUILD/apk-src/apktool.yml"
apktool b -q "$BUILD/apk-src" -o "$BUILD/app-unsigned.apk"

if [[ ! -f "$KEYSTORE" ]]; then
  keytool -genkeypair -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias demo -keyalg RSA -keysize 2048 -validity 365 -dname "CN=Device Farm Demo" 2>/dev/null
fi
# v1 (JAR) signing is accepted for targetSdk < 30.
jarsigner -keystore "$KEYSTORE" -storepass android -keypass android \
  -sigalg SHA256withRSA -digestalg SHA-256 \
  -signedjar "$OUT_APK" "$BUILD/app-unsigned.apk" demo >/dev/null
rm -f "$BUILD/app-unsigned.apk"

jarsigner -verify "$OUT_APK" >/dev/null && echo "Built $OUT_APK (targetSdkVersion $TARGET_SDK)"
