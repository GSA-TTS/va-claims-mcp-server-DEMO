import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy


class VAClaimsTokenVerifier(TokenVerifier):
    """
    Token verifier for VA Claims API.
    Validates tokens by calling the userinfo endpoint.
    """

    def __init__(self, oauth_base: str, base_url: str | None = None):
        super().__init__(
            base_url=base_url,
            required_scopes=[
                "openid",
                "profile",
                "offline_access",
                "claim.read",
                "claim.write",
            ],
        )
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

            return AccessToken(
                token=token,
                client_id=claims.get("sub", "unknown"),
                scopes=[
                    "openid",
                    "profile",
                    "offline_access",
                    "claim.read",
                    "claim.write",
                ],
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

        if "veteran_icn" in claims:
            return claims["veteran_icn"]

        if "patient" in claims:
            return claims["patient"]

        # preferred_username contains ICN in VA sandbox
        if "preferred_username" in claims:
            username = claims["preferred_username"]
            if "V" in username and len(username) == 17:
                return username

        # sub claim may contain ICN
        if "sub" in claims:
            sub = claims["sub"]
            if "V" in sub and len(sub) == 17:
                return sub

        if "profile" in claims and isinstance(claims["profile"], dict):
            if "icn" in claims["profile"]:
                return claims["profile"]["icn"]

        return None


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
        upstream_revocation_endpoint=f"{oauth_base}/revoke",
        token_verifier=token_verifier,
        base_url=base_url,
        # VA confidential clients use client_secret_basic (Authorization: Basic header),
        # not PKCE. PKCE is a separate VA flow for public clients without a secret.
        forward_pkce=False,
        token_endpoint_auth_method="client_secret_basic",
        valid_scopes=[],
    )
