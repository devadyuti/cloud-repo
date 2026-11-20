---
inclusion: always
---
# Project: AWS Device Farm demo for Example Bank (mobile banking)
- Purpose: one-off customer demo, Wed 11 Nov 2026. Keep it simple, runnable tonight.
- Region: us-west-2 only (Device Farm constraint).
- Stack: Python 3.11, Appium Python client, pytest, AWS CLI v2, bash.
- Sample app: AWS Device Farm Android reference app (public GitHub: aws-samples/aws-device-farm-sample-app-for-android). iOS optional.
- No real customer data or PII anywhere. Synthetic data only.
- Keep cost low: device pool of max 3 devices, short tests (<5 min).
- Never hardcode credentials; use the default AWS CLI profile / env vars.
