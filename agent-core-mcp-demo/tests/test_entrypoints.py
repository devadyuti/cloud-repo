"""Tests for container entrypoint scripts (S3 Tables and Redshift).

Validates that entrypoints:
1. Configure app.settings (host, port, stateless_http) before calling app.run()
2. Call app.run() with only transport="streamable-http"
3. Set app.allow_write = True when ALLOW_WRITE env var is set
4. Do not set allow_write when env var is absent or falsy

The awslabs MCP server packages are not installed in the test environment,
so we inject mock modules into sys.modules before loading the entrypoints.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures — stub the awslabs namespace packages
# ---------------------------------------------------------------------------

CONTAINERS_DIR = Path(__file__).parent.parent / "containers"


@pytest.fixture
def mock_s3_tables_app():
    """Create a mock app and inject it as awslabs.s3_tables_mcp_server.server.app."""
    mock_app = MagicMock()
    mock_app.allow_write = False
    mock_app.run = MagicMock()
    # Use a simple namespace for settings so attribute assignments are trackable
    mock_app.settings = MagicMock()

    mock_server_module = MagicMock()
    mock_server_module.app = mock_app

    modules = {
        "awslabs": MagicMock(),
        "awslabs.s3_tables_mcp_server": MagicMock(),
        "awslabs.s3_tables_mcp_server.server": mock_server_module,
    }

    with patch.dict(sys.modules, modules):
        yield mock_app


@pytest.fixture
def mock_redshift_app():
    """Create a mock app and inject it as awslabs.redshift_mcp_server.server.app."""
    mock_app = MagicMock()
    mock_app.allow_write = False
    mock_app.run = MagicMock()
    # Use a simple namespace for settings so attribute assignments are trackable
    mock_app.settings = MagicMock()

    mock_server_module = MagicMock()
    mock_server_module.app = mock_app

    modules = {
        "awslabs": MagicMock(),
        "awslabs.redshift_mcp_server": MagicMock(),
        "awslabs.redshift_mcp_server.server": mock_server_module,
    }

    with patch.dict(sys.modules, modules):
        yield mock_app


def _load_entrypoint(file_path: Path, module_name: str):
    """Load an entrypoint module from file, executing its top-level code."""
    # Remove from sys.modules if previously loaded
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# S3 Tables entrypoint
# ---------------------------------------------------------------------------


class TestS3TablesEntrypoint:
    """Tests for containers/s3-tables/entrypoint.py."""

    ENTRYPOINT = CONTAINERS_DIR / "s3-tables" / "entrypoint.py"

    def test_calls_app_run_with_streamable_http(self, mock_s3_tables_app):
        """Entrypoint calls app.run with only transport arg (host/port via settings)."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        mock_s3_tables_app.run.assert_called_once_with(
            transport="streamable-http"
        )

    def test_configures_app_settings(self, mock_s3_tables_app):
        """Entrypoint sets host, port, and stateless_http on app.settings."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.settings.host == "0.0.0.0"
        assert mock_s3_tables_app.settings.port == 8000
        assert mock_s3_tables_app.settings.stateless_http is True

    def test_enables_write_mode_when_env_true(self, mock_s3_tables_app):
        """Sets app.allow_write = True when ALLOW_WRITE=true."""
        with patch.dict("os.environ", {"ALLOW_WRITE": "true"}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.allow_write is True

    def test_enables_write_mode_when_env_1(self, mock_s3_tables_app):
        """Sets app.allow_write = True when ALLOW_WRITE=1."""
        with patch.dict("os.environ", {"ALLOW_WRITE": "1"}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.allow_write is True

    def test_enables_write_mode_when_env_yes(self, mock_s3_tables_app):
        """Sets app.allow_write = True when ALLOW_WRITE=YES (case-insensitive)."""
        with patch.dict("os.environ", {"ALLOW_WRITE": "YES"}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.allow_write is True

    def test_does_not_enable_write_mode_when_env_falsy(self, mock_s3_tables_app):
        """Does not set allow_write when ALLOW_WRITE is a non-truthy value."""
        with patch.dict("os.environ", {"ALLOW_WRITE": "false"}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.allow_write is False

    def test_does_not_enable_write_mode_when_env_absent(self, mock_s3_tables_app):
        """Does not set allow_write when ALLOW_WRITE is not in environment."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "s3_tables_entrypoint")

        assert mock_s3_tables_app.allow_write is False

    def test_does_not_import_uvicorn_or_transport_security(self, mock_s3_tables_app):
        """Entrypoint no longer uses uvicorn or TransportSecuritySettings."""
        source = self.ENTRYPOINT.read_text()
        assert "uvicorn" not in source
        assert "TransportSecuritySettings" not in source
        assert "streamable_http_app" not in source


# ---------------------------------------------------------------------------
# Redshift entrypoint
# ---------------------------------------------------------------------------


class TestRedshiftEntrypoint:
    """Tests for containers/redshift/entrypoint.py."""

    ENTRYPOINT = CONTAINERS_DIR / "redshift" / "entrypoint.py"

    def test_calls_app_run_with_streamable_http(self, mock_redshift_app):
        """Entrypoint calls app.run with only transport arg (host/port via settings)."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "redshift_entrypoint")

        mock_redshift_app.run.assert_called_once_with(
            transport="streamable-http"
        )

    def test_configures_app_settings(self, mock_redshift_app):
        """Entrypoint sets host, port, and stateless_http on app.settings."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "redshift_entrypoint")

        assert mock_redshift_app.settings.host == "0.0.0.0"
        assert mock_redshift_app.settings.port == 8000
        assert mock_redshift_app.settings.stateless_http is True

    def test_enables_write_mode_when_env_set(self, mock_redshift_app):
        """Sets app.allow_write = True when ALLOW_WRITE=true."""
        with patch.dict("os.environ", {"ALLOW_WRITE": "true"}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "redshift_entrypoint")

        assert mock_redshift_app.allow_write is True

    def test_does_not_enable_write_mode_when_env_absent(self, mock_redshift_app):
        """Does not set allow_write when ALLOW_WRITE is not in environment."""
        with patch.dict("os.environ", {}, clear=True):
            _load_entrypoint(self.ENTRYPOINT, "redshift_entrypoint")

        assert mock_redshift_app.allow_write is False

    def test_does_not_import_uvicorn_or_transport_security(self, mock_redshift_app):
        """Entrypoint does not use uvicorn or TransportSecuritySettings."""
        source = self.ENTRYPOINT.read_text()
        assert "uvicorn" not in source
        assert "TransportSecuritySettings" not in source
        assert "streamable_http_app" not in source
