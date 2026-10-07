"""Tests for VA Claims MCP Server."""

import logging
import os

import httpx
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

    assert API_BASE == "https://sandbox-api.va.gov/services/claims/v1"
    assert OAUTH_BASE == "https://sandbox-api.va.gov/oauth2/claims/v1"


def test_server_creates():
    """Test that server can be created."""
    from src.va_claims.server import create_server

    mcp = create_server()
    assert mcp is not None
    assert mcp.name == "VA Benefits Claims"


def test_health_endpoint():
    """Test health check endpoint exists."""
    from src.va_claims.server import mcp

    assert mcp is not None


@pytest.mark.asyncio
async def test_api_error_does_not_log_response_body(monkeypatch, caplog):
    """VA error bodies can contain PII and must never enter application logs."""
    from src.va_claims import utils

    sensitive_body = (
        "SSN 123-45-6789, DOB 1945-01-02, address 123 Main St, "
        "diagnosis PTSD, bearer secret-token"
    )
    request = httpx.Request("GET", "https://sandbox-api.va.gov/services/claims/v1/claims")
    response = httpx.Response(422, text=sensitive_body, request=request)

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            pass

        async def get(self, *args, **kwargs):
            return response

    monkeypatch.setattr(utils.httpx, "AsyncClient", FakeAsyncClient)

    with caplog.at_level(logging.ERROR, logger=utils.logger.name):
        with pytest.raises(httpx.HTTPStatusError):
            await utils.call_api("secret-token", "claims")

    assert "status 422" in caplog.text
    for sensitive_value in (
        sensitive_body,
        "123-45-6789",
        "1945-01-02",
        "123 Main St",
        "PTSD",
        "secret-token",
    ):
        assert sensitive_value not in caplog.text


@pytest.mark.parametrize(
    "content, content_type",
    [
        ('{"errors":[{"detail":"SSN 123-45-6789 at 123 Main St"}]}', "application/json"),
        ("SSN 123-45-6789 at 123 Main St", "text/plain"),
    ],
)
def test_formatted_api_error_does_not_return_response_body(content, content_type):
    """MCP callers receive status metadata, not arbitrary upstream content."""
    from src.va_claims.utils import format_api_error

    request = httpx.Request("GET", "https://sandbox-api.va.gov/services/claims/v1/claims")
    response = httpx.Response(
        422,
        content=content,
        headers={"Content-Type": content_type},
        request=request,
    )
    error = httpx.HTTPStatusError("request failed", request=request, response=response)

    result = format_api_error(error)
    assert result == {"error": "VA API request failed", "status": 422}
    assert "123-45-6789" not in str(result)
    assert "123 Main St" not in str(result)
