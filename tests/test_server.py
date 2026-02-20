"""Tests for VA Claims MCP Server."""

import os

import pytest


@pytest.fixture(autouse=True)
def setup_env():
    """Set up test environment variables."""
    os.environ["VA_CLIENT_ID"] = "test_client_id"
    os.environ["VA_CLIENT_SECRET"] = "test_client_secret"
    os.environ["BASE_URL"] = "http://localhost:8000"
    yield


def test_config_loads():
    """Test that configuration loads correctly."""
    from src.va_claims.config import API_BASE, OAUTH_BASE

    assert API_BASE == "https://sandbox-api.va.gov/services/claims/v2"
    assert OAUTH_BASE == "https://sandbox-api.va.gov/oauth2"


def test_server_creates():
    """Test that server can be created."""
    from src.va_claims.server import create_server

    mcp = create_server()
    assert mcp is not None
    assert mcp.name == "VA Benefits Claims"


def test_health_endpoint():
    """Test health check endpoint exists."""
    from src.va_claims.server import app

    # The app should have routes defined
    assert app is not None
