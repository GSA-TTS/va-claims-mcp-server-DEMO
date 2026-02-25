"""
VA Claims API MCP Server with OAuth Authentication

Provides secure access to VA benefits claims data via Model Context Protocol.
Uses the VA.gov Benefits Claims API (https://developer.va.gov/explore/api/benefits-claims)
to retrieve and submit claims information.
"""

import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.va_claims.auth import create_oauth_provider
from src.va_claims.config import OAUTH_BASE
from src.va_claims.tools import register_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    client_id = os.environ.get("VA_CLIENT_ID")
    client_secret = os.environ.get("VA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing required environment variables: VA_CLIENT_ID and VA_CLIENT_SECRET"
        )

    auth = create_oauth_provider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=os.environ.get("BASE_URL", "http://localhost:8000"),
        oauth_base=OAUTH_BASE,
    )

    mcp = FastMCP(name="VA Benefits Claims", auth=auth)

    register_tools(mcp)

    return mcp


mcp = create_server()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring and load balancers."""
    return JSONResponse({"status": "healthy", "service": "va-claims-mcp"})


app = mcp.http_app()
