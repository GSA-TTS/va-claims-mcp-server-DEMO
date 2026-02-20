"""Configuration and constants for VA Claims MCP Server."""

import os

from dotenv import load_dotenv

load_dotenv()

# VA API base URL - defaults to sandbox for development
API_BASE = os.environ.get("VA_API_BASE", "https://sandbox-api.va.gov/services/claims/v2")

# OAuth endpoints
OAUTH_BASE = os.environ.get("VA_OAUTH_BASE", "https://sandbox-api.va.gov/oauth2")
