import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy


class VAClaimsTokenVerifier(TokenVerifier):
    """
    Token verifier for VA Claims API.
    Validates tokens by calling the userinfo endpoint.
    """

    def __init__(self, oauth_base: str, base_url: str | None = None):
        super().__init__(base_url=base_url)
        self.oauth_base = oauth_base

    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Validate the access token by making a request to VA OAuth userinfo endpoint.
        Returns AccessToken with claims about the authenticated user.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.oauth_base}/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                claims = response.json()

            # Extract veteran ICN from token claims
            veteran_icn = self._extract_veteran_icn(claims)
            if veteran_icn:
                claims["veteran_icn"] = veteran_icn

            # Extract scopes
            scopes = self._extract_scopes(claims)

            return AccessToken(
                token=token,
                client_id=claims.get("sub", "unknown"),
                scopes=scopes,
                expires_at=None,
                claims=claims,
            )

        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

    def _extract_veteran_icn(self, claims: dict) -> str | None:
        """Extract veteran ICN from various possible claim formats."""
        # Direct ICN claim
        if "icn" in claims:
            return claims["icn"]

        # VA-specific claims
        if "veteran_icn" in claims:
            return claims["veteran_icn"]

        # sub claim may contain ICN in some formats
        if "sub" in claims:
            sub = claims["sub"]
            # ICN format: 10 digits + V + 6 digits (e.g., 1012667145V762142)
            if "V" in sub and len(sub) == 17:
                return sub

        # Profile claim may contain ICN
        if "profile" in claims and isinstance(claims["profile"], dict):
            if "icn" in claims["profile"]:
                return claims["profile"]["icn"]

        return None

    def _extract_scopes(self, claims: dict) -> list[str]:
        """Extract scopes from claims."""
        if "scope" not in claims:
            return []
        if isinstance(claims["scope"], str):
            return claims["scope"].split()
        if isinstance(claims["scope"], list):
            return claims["scope"]
        return []


def create_oauth_provider(
    client_id: str,
    client_secret: str,
    base_url: str,
    oauth_base: str,
) -> OAuthProxy:
    """
    Create an OAuth provider for VA Claims API.

    VA requires manual app registration (no DCR support),
    so we use OAuthProxy to bridge between MCP's DCR expectations
    and VA's fixed OAuth flow.
    """
    token_verifier = VAClaimsTokenVerifier(oauth_base=oauth_base, base_url=base_url)

    return OAuthProxy(
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,
        upstream_authorization_endpoint=f"{oauth_base}/authorization",
        upstream_token_endpoint=f"{oauth_base}/token",
        token_verifier=token_verifier,
        base_url=base_url,
        valid_scopes=[
            "openid",
            "profile",
            "offline_access",
            "claim.read",
            "claim.write",
        ],
    )
