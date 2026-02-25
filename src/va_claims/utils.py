import logging

import httpx
from fastmcp.server.auth import AccessToken
from fastmcp.server.dependencies import get_access_token

from src.va_claims.config import API_BASE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_representative_headers(
    veteran_ssn: str | None = None,
    veteran_first_name: str | None = None,
    veteran_last_name: str | None = None,
    veteran_birth_date: str | None = None,
) -> dict:
    """
    Build X-VA-* headers for representative mode.

    When a consumer is acting as an accredited representative (not the claimant
    themselves), they must pass the claimant's identity in these headers.
    Omitting them causes the API to treat the representative as the claimant.

    Args:
        veteran_ssn: Claimant SSN (X-VA-SSN)
        veteran_first_name: Claimant first name (X-VA-First-Name)
        veteran_last_name: Claimant last name (X-VA-Last-Name)
        veteran_birth_date: Claimant birth date in ISO 8601 format (X-VA-Birth-Date)
    """
    headers = {}
    if veteran_ssn:
        headers["X-VA-SSN"] = veteran_ssn
    if veteran_first_name:
        headers["X-VA-First-Name"] = veteran_first_name
    if veteran_last_name:
        headers["X-VA-Last-Name"] = veteran_last_name
    if veteran_birth_date:
        headers["X-VA-Birth-Date"] = veteran_birth_date
    return headers


async def call_api(
    token: str,
    endpoint: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None,
    extra_headers: dict | None = None,
) -> dict:
    """
    Make an authenticated request to the VA Benefits Claims API.

    Args:
        token: Bearer token for Authorization header.
        endpoint: API path relative to API_BASE (e.g. "claims", "forms/526").
        method: HTTP method — "GET", "POST", or "PUT".
        json_data: Request body for POST/PUT requests.
        params: Query string parameters for GET requests (e.g. {"type": "compensation"}).
        extra_headers: Additional headers, e.g. X-VA-* representative identity headers.
    """
    url = f"{API_BASE}/{endpoint}"
    logger.debug(f"Making {method} request to: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
            if extra_headers:
                headers.update(extra_headers)

            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method in ("POST", "PUT"):
                response = await getattr(client, method.lower())(
                    url,
                    headers={**headers, "Content-Type": "application/json"},
                    json=json_data,
                    params=params,
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


def get_token() -> AccessToken | None:
    """Get the access token for the authenticated user."""
    token = get_access_token()
    if not token:
        logger.error("No access token available")
        return None
    return token
