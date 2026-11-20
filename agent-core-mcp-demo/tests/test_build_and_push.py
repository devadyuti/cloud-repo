"""Tests for deploy/build_and_push.sh script structure.

Validates the shell script contains the expected steps, including the
AgentCore wrapper image builds (Step 2b) that override base image tags.
"""

import os
import stat

import pytest

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "deploy", "build_and_push.sh"
)


@pytest.fixture
def script_content():
    """Load the build_and_push.sh script content."""
    with open(SCRIPT_PATH, "r") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Script Basics
# ---------------------------------------------------------------------------


class TestScriptBasics:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH)

    def test_script_is_executable(self):
        mode = os.stat(SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "Script should be executable by owner"

    def test_script_has_bash_shebang(self, script_content):
        assert script_content.startswith("#!/usr/bin/env bash")

    def test_script_uses_strict_mode(self, script_content):
        assert "set -euo pipefail" in script_content


# ---------------------------------------------------------------------------
# Step 2: Base Image Builds
# ---------------------------------------------------------------------------


class TestBaseImageBuilds:
    def test_builds_s3_tables_base_image(self, script_content):
        """Step 2 builds the S3 Tables MCP server from awslabs/mcp repo."""
        assert "src/s3-tables-mcp-server/Dockerfile" in script_content

    def test_builds_redshift_base_image(self, script_content):
        """Step 2 builds the Redshift MCP server from awslabs/mcp repo."""
        assert "src/redshift-mcp-server/Dockerfile" in script_content


# ---------------------------------------------------------------------------
# Step 2b: AgentCore Wrapper Image Builds
# ---------------------------------------------------------------------------


class TestWrapperImageBuilds:
    def test_step_2b_section_exists(self, script_content):
        """Step 2b header is present in the script."""
        assert "Step 2b" in script_content

    def test_wrapper_builds_use_containers_dir(self, script_content):
        """Wrapper builds reference the containers/ directory."""
        assert 'CONTAINERS_DIR="${PROJECT_ROOT}/containers"' in script_content

    def test_builds_s3_tables_wrapper(self, script_content):
        """Builds S3 Tables wrapper from containers/s3-tables/Dockerfile."""
        assert '${CONTAINERS_DIR}/s3-tables/Dockerfile' in script_content
        assert '${CONTAINERS_DIR}/s3-tables"' in script_content

    def test_builds_redshift_wrapper(self, script_content):
        """Builds Redshift wrapper from containers/redshift/Dockerfile."""
        assert '${CONTAINERS_DIR}/redshift/Dockerfile' in script_content
        assert '${CONTAINERS_DIR}/redshift"' in script_content

    def test_wrapper_overrides_base_tags(self, script_content):
        """Wrapper images use the same repo name:tag as base, overriding them."""
        # Both wrapper docker build commands tag with the same repo names
        # used by the base builds, effectively overriding the base images.
        lines = script_content.split("\n")
        wrapper_section = False
        s3_tables_tag_found = False
        redshift_tag_found = False

        for line in lines:
            if "Step 2b" in line:
                wrapper_section = True
            if "Step 3" in line:
                break
            if wrapper_section:
                if '${S3_TABLES_REPO_NAME}:${IMAGE_TAG}' in line and "-t" in line:
                    s3_tables_tag_found = True
                if '${REDSHIFT_REPO_NAME}:${IMAGE_TAG}' in line and "-t" in line:
                    redshift_tag_found = True

        assert s3_tables_tag_found, "S3 Tables wrapper should tag with same repo name as base"
        assert redshift_tag_found, "Redshift wrapper should tag with same repo name as base"

    def test_wrapper_builds_after_base_builds(self, script_content):
        """Step 2b (wrappers) comes after Step 2 (base) so it overrides tags."""
        step2_pos = script_content.find("Step 2:")
        step2b_pos = script_content.find("Step 2b:")
        step3_pos = script_content.find("Step 3:")

        assert step2_pos < step2b_pos < step3_pos, (
            "Build order must be: Step 2 (base) → Step 2b (wrapper) → Step 3 (ECR auth)"
        )


# ---------------------------------------------------------------------------
# Containers Directory Structure
# ---------------------------------------------------------------------------


class TestContainersDirectory:
    """Validate the containers/ directory that wrapper builds depend on."""

    CONTAINERS_DIR = os.path.join(
        os.path.dirname(__file__), "..", "containers"
    )

    def test_s3_tables_dockerfile_exists(self):
        path = os.path.join(self.CONTAINERS_DIR, "s3-tables", "Dockerfile")
        assert os.path.isfile(path)

    def test_s3_tables_entrypoint_exists(self):
        path = os.path.join(self.CONTAINERS_DIR, "s3-tables", "entrypoint.py")
        assert os.path.isfile(path)

    def test_redshift_dockerfile_exists(self):
        path = os.path.join(self.CONTAINERS_DIR, "redshift", "Dockerfile")
        assert os.path.isfile(path)

    def test_redshift_entrypoint_exists(self):
        path = os.path.join(self.CONTAINERS_DIR, "redshift", "entrypoint.py")
        assert os.path.isfile(path)

    def test_s3_tables_dockerfile_extends_base(self):
        path = os.path.join(self.CONTAINERS_DIR, "s3-tables", "Dockerfile")
        with open(path) as f:
            content = f.read()
        assert "FROM s3-tables-mcp-server:latest" in content

    def test_redshift_dockerfile_extends_base(self):
        path = os.path.join(self.CONTAINERS_DIR, "redshift", "Dockerfile")
        with open(path) as f:
            content = f.read()
        assert "FROM redshift-mcp-server:latest" in content
