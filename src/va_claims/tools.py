import httpx

from src.va_claims.utils import call_api, get_veteran_icn_from_token


def register_tools(mcp):
    @mcp.tool()
    async def get_claim_status(claim_id: str) -> dict:
        """
        Get the status of a specific VA benefits claim.
        Returns claim information including current status, phase, and details.
        Requires claim.read scope.

        Args:
            claim_id: The claim ID to retrieve (e.g., "600400703")
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(token.token, f"veterans/{veteran_icn}/claims/{claim_id}")
            return {"veteran_icn": veteran_icn, "claim": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def list_claims() -> dict:
        """
        List all VA benefits claims for the authenticated veteran.
        Returns a list of claims with their IDs, types, and statuses.
        Requires claim.read scope.
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(token.token, f"veterans/{veteran_icn}/claims")
            return {"veteran_icn": veteran_icn, "claims": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_5103_waiver(claim_id: str, tracked_item_ids: list[int]) -> dict:
        """
        Submit an Evidence Waiver 5103 for a specific claim.
        This waives the requirement for specific tracked items.
        Requires claim.write scope.

        Args:
            claim_id: The claim ID to submit the waiver for
            tracked_item_ids: List of tracked item IDs to waive (integers)
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(
                token.token,
                f"veterans/{veteran_icn}/claims/{claim_id}/5103",
                method="POST",
                json_data={"trackedItemIds": tracked_item_ids},
            )
            return {"veteran_icn": veteran_icn, "claim_id": claim_id, "result": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_disability_claim(
        claim_data: dict,
    ) -> dict:
        """
        Submit a disability compensation claim (21-526EZ form).
        This creates a new disability claim in VBMS.
        Requires claim.write scope.

        Args:
            claim_data: The claim data following the 526EZ schema. Must include:
                - veteranIdentification: address and currentVaEmployee flag
                - disabilities: list of disabilities with name, disabilityActionType, serviceRelevance
                - serviceInformation: service periods with branch, component, and dates
                - claimantCertification: boolean confirming authorization

        Example claim_data structure:
        {
            "veteranIdentification": {
                "mailingAddress": {
                    "addressLine1": "123 Main St",
                    "city": "Portland",
                    "state": "OR",
                    "country": "USA",
                    "zipFirstFive": "97201"
                },
                "currentVaEmployee": false
            },
            "disabilities": [
                {
                    "name": "Tinnitus",
                    "disabilityActionType": "NEW",
                    "serviceRelevance": "Caused by acoustic trauma during service"
                }
            ],
            "serviceInformation": {
                "servicePeriods": [
                    {
                        "serviceBranch": "Army",
                        "serviceComponent": "Active",
                        "activeDutyBeginDate": "2010-01-01",
                        "activeDutyEndDate": "2014-12-31"
                    }
                ]
            },
            "claimantCertification": true
        }
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(
                token.token,
                f"veterans/{veteran_icn}/526/synchronous",
                method="POST",
                json_data=claim_data,
            )
            return {"veteran_icn": veteran_icn, "submitted_claim": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def get_intent_to_file() -> dict:
        """
        Get the veteran's current Intent to File status.
        Intent to File preserves the effective date for benefits.
        Requires claim.read scope.
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(token.token, f"veterans/{veteran_icn}/intent-to-file")
            return {"veteran_icn": veteran_icn, "intent_to_file": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_intent_to_file(intent_type: str = "compensation") -> dict:
        """
        Submit an Intent to File for the veteran.
        This preserves the effective date for future benefits claims.
        Requires claim.write scope.

        Args:
            intent_type: Type of intent to file. Options: "compensation", "pension", "survivor"
        """
        result = get_veteran_icn_from_token()
        if result[0] is None:
            return result[1]
        token, veteran_icn = result

        try:
            data = await call_api(
                token.token,
                f"veterans/{veteran_icn}/intent-to-file",
                method="POST",
                json_data={"type": intent_type},
            )
            return {"veteran_icn": veteran_icn, "intent_to_file": data}
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}
