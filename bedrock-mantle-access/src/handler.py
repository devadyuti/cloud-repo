"""Lambda handler that invokes GPT-5.5 via the Amazon Bedrock Mantle endpoint.

The handler accepts a text prompt from the Lambda event, calls the model
through the OpenAI Responses API against the bedrock-mantle base URL, and
returns the generated text.
"""

import json
import os

import boto3
from openai import OpenAI

# Reused across warm invocations.
_secrets_client = boto3.client("secretsmanager")
_api_key_cache = None


def get_api_key():
    """Retrieve the Bedrock Mantle API key from Secrets Manager.

    The value is cached on the module scope so warm invocations avoid a
    second Secrets Manager call.
    """
    global _api_key_cache
    if _api_key_cache is not None:
        return _api_key_cache

    secret_id = os.environ["API_KEY_SECRET_ID"]
    secret_string = _secrets_client.get_secret_value(SecretId=secret_id)["SecretString"]

    # The secret is JSON with an "AWS_BEARER_TOKEN_BEDROCK" field holding the
    # API key. Fall back to treating the value as a raw plaintext key.
    api_key = secret_string.strip()
    try:
        parsed = json.loads(secret_string)
        if isinstance(parsed, dict):
            api_key = parsed.get("AWS_BEARER_TOKEN_BEDROCK", api_key)
    except (json.JSONDecodeError, ValueError):
        pass

    _api_key_cache = api_key
    return _api_key_cache


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _extract_prompt(event):
    """Get the prompt from a direct invoke or an API Gateway proxy request."""
    event = event or {}

    # API Gateway (REST / HTTP API) proxy integration puts the payload in "body".
    if "body" in event:
        body = event.get("body") or "{}"
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                body = {}
        return (body or {}).get("prompt", "")

    # Direct invocation: prompt is at the top level.
    return event.get("prompt", "Hello, what can you do?")


def lambda_handler(event, context):
    region = os.environ.get("BEDROCK_REGION", "us-east-1")

    prompt = _extract_prompt(event)
    if not isinstance(prompt, str) or not prompt.strip():
        return _response(400, {"error": "A non-empty 'prompt' string is required."})

    try:
        client = OpenAI(
            api_key=get_api_key(),
            base_url=f"https://bedrock-mantle.{region}.api.aws/openai/v1",
        )

        response = client.responses.create(
            model="openai.gpt-5.5",
            input=prompt,
        )

        return _response(
            200,
            {
                "response": response.output_text,
                "model": "openai.gpt-5.5",
                "region": region,
            },
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the caller
        # Avoid leaking secret material; log the type/message only.
        print(f"Inference failed: {type(exc).__name__}: {exc}")
        return _response(502, {"error": "Failed to invoke GPT-5.5 via Bedrock Mantle."})
