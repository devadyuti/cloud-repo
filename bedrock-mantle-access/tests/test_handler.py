"""Unit tests for the Bedrock Mantle Lambda handler."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the module-level API key cache between tests."""
    import src.handler as handler_module

    handler_module._api_key_cache = None
    yield
    handler_module._api_key_cache = None


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv("API_KEY_SECRET_ID", "bedrock-mantle-api-key")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")


class TestResponse:
    """Tests for the _response helper."""

    def test_includes_content_type_header(self):
        from src.handler import _response

        result = _response(200, {"ok": True})

        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "application/json"
        assert json.loads(result["body"]) == {"ok": True}


class TestExtractPrompt:
    """Tests for _extract_prompt which handles both direct and API Gateway events."""

    def test_direct_invocation_with_prompt(self):
        from src.handler import _extract_prompt

        assert _extract_prompt({"prompt": "Hello"}) == "Hello"

    def test_direct_invocation_no_prompt_uses_default(self):
        from src.handler import _extract_prompt

        assert _extract_prompt({}) == "Hello, what can you do?"

    def test_none_event_uses_default(self):
        from src.handler import _extract_prompt

        assert _extract_prompt(None) == "Hello, what can you do?"

    def test_api_gateway_json_body_string(self):
        """API Gateway proxy passes body as a JSON string."""
        from src.handler import _extract_prompt

        event = {"body": json.dumps({"prompt": "Explain RAG"})}
        assert _extract_prompt(event) == "Explain RAG"

    def test_api_gateway_empty_body_returns_empty(self):
        from src.handler import _extract_prompt

        event = {"body": ""}
        assert _extract_prompt(event) == ""

    def test_api_gateway_null_body_returns_empty(self):
        from src.handler import _extract_prompt

        event = {"body": None}
        assert _extract_prompt(event) == ""

    def test_api_gateway_invalid_json_body_returns_empty(self):
        from src.handler import _extract_prompt

        event = {"body": "not-json"}
        assert _extract_prompt(event) == ""

    def test_api_gateway_body_missing_prompt_key_returns_empty(self):
        from src.handler import _extract_prompt

        event = {"body": json.dumps({"other": "value"})}
        assert _extract_prompt(event) == ""


class TestGetApiKey:
    """Tests for the get_api_key helper."""

    def test_extracts_api_key_from_json(self, env_vars):
        """When the secret is JSON with an 'AWS_BEARER_TOKEN_BEDROCK' field, that value is used."""
        secret_value = json.dumps({"AWS_BEARER_TOKEN_BEDROCK": "sk-test-key-123"})

        with patch("src.handler._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": secret_value}

            from src.handler import get_api_key

            key = get_api_key()

        assert key == "sk-test-key-123"
        mock_client.get_secret_value.assert_called_once_with(SecretId="bedrock-mantle-api-key")

    def test_uses_raw_plaintext_when_not_json(self, env_vars):
        """When the secret is a raw string (not JSON), use it directly as the key."""
        with patch("src.handler._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "sk-plaintext-key"}

            from src.handler import get_api_key

            key = get_api_key()

        assert key == "sk-plaintext-key"

    def test_falls_back_to_raw_when_json_missing_field(self, env_vars):
        """If JSON doesn't have AWS_BEARER_TOKEN_BEDROCK, the raw string is used as-is."""
        secret_value = json.dumps({"other_field": "some-value"})

        with patch("src.handler._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": secret_value}

            from src.handler import get_api_key

            key = get_api_key()

        # Falls back to the raw JSON string stripped
        assert key == secret_value.strip()

    def test_caches_key_across_calls(self, env_vars):
        """Warm invocations should reuse the cached key without calling Secrets Manager again."""
        secret_value = json.dumps({"AWS_BEARER_TOKEN_BEDROCK": "sk-cached"})

        with patch("src.handler._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": secret_value}

            from src.handler import get_api_key

            first = get_api_key()
            second = get_api_key()

        assert first == second == "sk-cached"
        assert mock_client.get_secret_value.call_count == 1


class TestLambdaHandler:
    """Tests for the lambda_handler entry point."""

    def test_returns_400_on_empty_prompt(self, env_vars):
        from src.handler import lambda_handler

        result = lambda_handler({"prompt": "   "}, None)

        assert result["statusCode"] == 400
        assert result["headers"]["Content-Type"] == "application/json"
        body = json.loads(result["body"])
        assert "error" in body

    def test_returns_400_on_non_string_prompt(self, env_vars):
        from src.handler import lambda_handler

        result = lambda_handler({"prompt": 123}, None)

        assert result["statusCode"] == 400

    def test_returns_400_on_api_gateway_empty_prompt(self, env_vars):
        """API Gateway event with empty prompt body returns 400."""
        from src.handler import lambda_handler

        event = {"body": json.dumps({"prompt": "  "})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400

    @patch("src.handler.OpenAI")
    @patch("src.handler.get_api_key", return_value="sk-test")
    def test_successful_invocation(self, mock_get_key, mock_openai_cls, env_vars):
        mock_response = MagicMock()
        mock_response.output_text = "RAG combines retrieval with generation."
        mock_openai_cls.return_value.responses.create.return_value = mock_response

        from src.handler import lambda_handler

        result = lambda_handler({"prompt": "Explain RAG"}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["response"] == "RAG combines retrieval with generation."
        assert body["model"] == "openai.gpt-5.5"
        assert body["region"] == "us-east-1"

        mock_openai_cls.assert_called_once_with(
            api_key="sk-test",
            base_url="https://bedrock-mantle.us-east-1.api.aws/openai/v1",
        )

    @patch("src.handler.OpenAI")
    @patch("src.handler.get_api_key", return_value="sk-test")
    def test_returns_502_on_inference_failure(self, mock_get_key, mock_openai_cls, env_vars):
        mock_openai_cls.return_value.responses.create.side_effect = RuntimeError("timeout")

        from src.handler import lambda_handler

        result = lambda_handler({"prompt": "Hello"}, None)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert "error" in body

    def test_default_prompt_when_event_is_none(self, env_vars):
        """When event is None, the handler should use the default prompt."""
        with patch("src.handler.OpenAI") as mock_openai_cls, \
             patch("src.handler.get_api_key", return_value="sk-test"):
            mock_response = MagicMock()
            mock_response.output_text = "I can help with many things."
            mock_openai_cls.return_value.responses.create.return_value = mock_response

            from src.handler import lambda_handler

            result = lambda_handler(None, None)

        assert result["statusCode"] == 200

    @patch("src.handler.OpenAI")
    @patch("src.handler.get_api_key", return_value="sk-test")
    def test_api_gateway_proxy_event(self, mock_get_key, mock_openai_cls, env_vars):
        """Handler extracts prompt from an API Gateway proxy event body."""
        mock_response = MagicMock()
        mock_response.output_text = "Answer from API GW"
        mock_openai_cls.return_value.responses.create.return_value = mock_response

        from src.handler import lambda_handler

        event = {"body": json.dumps({"prompt": "What is Lambda?"})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "application/json"
        body = json.loads(result["body"])
        assert body["response"] == "Answer from API GW"
