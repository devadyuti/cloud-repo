"""Tests for demo.run_agent module.

Covers configuration loading, dependency import error handling (including
the new SigV4 auth dependencies), and agent creation logic.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Import error handling — SigV4 dependencies
# ---------------------------------------------------------------------------


class TestSigV4ImportBlock:
    """Verify that missing SigV4 dependencies produce a clear error message."""

    def test_missing_httpx_exits_with_message(self, capsys):
        """When httpx is not installed, run_agent exits with install instructions."""
        import importlib
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("No module named 'httpx'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                # Force re-import to trigger the import block
                import importlib
                import sys
                # Remove cached module if present
                sys.modules.pop("demo.run_agent", None)
                importlib.import_module("demo.run_agent")

        assert exc_info.value.code == 1

    def test_missing_botocore_exits_with_message(self, capsys):
        """When botocore is not installed, run_agent exits with install instructions."""
        import builtins
        import sys
        import importlib

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "botocore.session" or name == "botocore":
                error = ImportError(f"No module named '{name}'")
                error.name = name
                raise error
            return real_import(name, *args, **kwargs)

        sys.modules.pop("demo.run_agent", None)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                importlib.import_module("demo.run_agent")

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# load_agent_config
# ---------------------------------------------------------------------------


class TestLoadAgentConfig:
    """Tests for load_agent_config() configuration resolution."""

    def test_loads_from_env_variable(self, tmp_path, monkeypatch):
        """AGENTCORE_GATEWAY_URL env var takes precedence over file."""
        monkeypatch.setenv("AGENTCORE_GATEWAY_URL", "https://gw.example.com/mcp")
        monkeypatch.setenv("AGENTCORE_AGENT_MODEL", "anthropic.claude-sonnet-4-20250514")
        monkeypatch.setenv("AGENTCORE_AGENT_NAME", "test-agent")

        from demo.run_agent import load_agent_config

        config = load_agent_config()

        assert config["gateway_url"] == "https://gw.example.com/mcp"
        assert config["model_id"] == "anthropic.claude-sonnet-4-20250514"
        assert config["agent_name"] == "test-agent"

    def test_loads_from_agent_file(self, tmp_path, monkeypatch):
        """Falls back to deploy/outputs/agent.json when env vars are unset."""
        monkeypatch.delenv("AGENTCORE_GATEWAY_URL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_MODEL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_NAME", raising=False)

        agent_file = tmp_path / "agent.json"
        agent_file.write_text(json.dumps({
            "gateway_url": "https://file-gw.example.com/mcp",
            "model_id": "anthropic.claude-sonnet-4-20250514",
            "agent_name": "file-agent",
        }))

        with patch("demo.run_agent.AGENT_FILE", agent_file):
            from demo.run_agent import load_agent_config
            config = load_agent_config()

        assert config["gateway_url"] == "https://file-gw.example.com/mcp"
        assert config["agent_name"] == "file-agent"

    def test_defaults_model_id_when_not_provided(self, monkeypatch):
        """model_id defaults to Claude Sonnet when not in env or file."""
        monkeypatch.setenv("AGENTCORE_GATEWAY_URL", "https://gw.example.com/mcp")
        monkeypatch.delenv("AGENTCORE_AGENT_MODEL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_NAME", raising=False)

        from demo.run_agent import load_agent_config

        config = load_agent_config()

        assert config["model_id"] == "anthropic.claude-sonnet-4-20250514"

    def test_defaults_agent_name_when_not_provided(self, monkeypatch):
        """agent_name defaults to da-analytics-agent."""
        monkeypatch.setenv("AGENTCORE_GATEWAY_URL", "https://gw.example.com/mcp")
        monkeypatch.delenv("AGENTCORE_AGENT_MODEL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_NAME", raising=False)

        from demo.run_agent import load_agent_config

        config = load_agent_config()

        assert config["agent_name"] == "da-analytics-agent"

    def test_exits_when_no_gateway_url(self, tmp_path, monkeypatch):
        """Exits with error when gateway URL not in env or file."""
        monkeypatch.delenv("AGENTCORE_GATEWAY_URL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_MODEL", raising=False)
        monkeypatch.delenv("AGENTCORE_AGENT_NAME", raising=False)

        agent_file = tmp_path / "agent.json"
        # File does not exist

        with patch("demo.run_agent.AGENT_FILE", agent_file):
            from demo.run_agent import load_agent_config

            with pytest.raises(SystemExit) as exc_info:
                load_agent_config()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleAttributes:
    """Verify expected module-level attributes exist after import."""

    def test_urlparse_is_imported(self):
        """urlparse is available (needed for SigV4 host extraction)."""
        from demo.run_agent import urlparse
        assert callable(urlparse)

    def test_sigv4_dependencies_available(self):
        """SigV4 auth dependencies are importable at module level."""
        import demo.run_agent as mod
        assert hasattr(mod, "httpx")
        assert hasattr(mod, "SigV4Auth")
        assert hasattr(mod, "AWSRequest")
        assert hasattr(mod, "BotocoreSession")
