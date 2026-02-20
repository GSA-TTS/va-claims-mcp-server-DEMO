import logging

import httpx
from fastmcp.server.auth import AccessToken
from fastmcp.server.dependencies import get_access_token

from src.va_claims.config import API_BASE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def call_api(token: str, endpoint: str, method: str = "GET", json_data: dict | None = None) -> dict:
    """Make authenticated request to VA Claims API."""
    url = f"{API_BASE}/{endpoint}"
    logger.debug(f"Making {method} request to: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
            elif method == "POST":
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=json_data,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise


def get_veteran_icn_from_token() -> tuple[AccessToken, str] | tuple[None, dict]:
    """Get the access token and veteran ICN."""
    token = get_access_token()
    logger.debug(f"Token retrieved: {token is not None}")

    if not token:
        logger.error("No access token available")
        return None, {"error": "Not authenticated"}

    logger.debug(f"Token claims: {token.claims}")

    veteran_icn = token.claims.get("veteran_icn")
    if not veteran_icn:
        logger.error(f"No veteran ICN in token claims: {token.claims.keys()}")
        return None, {"error": "No veteran ICN in token"}

    logger.debug(f"Veteran ICN: {veteran_icn}")
    return token, veteran_icn
