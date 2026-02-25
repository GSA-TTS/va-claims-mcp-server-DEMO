import httpx

from src.va_claims.utils import build_representative_headers, call_api, get_token


def register_tools(mcp):
    @mcp.tool()
    async def list_claims(
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Find all VA benefits claims for a claimant (GET /claims).

        An authenticated veteran calling this without representative headers
        returns their own claims. An accredited representative must supply the
        claimant's identity via the veteran_* parameters.

        Args:
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(token.token, "claims", extra_headers=rep_headers)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def get_claim_status(
        claim_id: str,
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Find a specific VA benefits claim by ID (GET /claims/{id}).

        Works for all claim types including compensation, pension, and burial.

        Args:
            claim_id: The claim ID to retrieve (e.g. "600400703").
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(token.token, f"claims/{claim_id}", extra_headers=rep_headers)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_disability_claim(
        claim_data: dict,
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Submit a disability compensation claim — VA Form 21-526EZ (POST /forms/526).

        Establishes a Disability Compensation Claim directly in VBMS. A 200 response
        means the submission was accepted; use get_claim_status with the returned ID
        to track when the claim reaches "claim established" status.

        Original claims (a veteran's very first claim) must be submitted with
        autoCestPDFGenerationDisabled=true, then a signed PDF uploaded separately.
        Subsequent claims do not require a PDF upload.

        Fully Developed Claims (FDC): set standardClaim=false to certify the claim
        includes all information needed for processing (faster handling).

        NOTE: The VA recommends using disabilityActionType="NEW" instead of "INCREASE"
        for all disabilities submitted via this API, as "INCREASE" requires
        ratedDisabilityId and diagnosticCode which this API doesn't surface.
        Using "NEW" does not significantly impact claims processing.

        Args:
            claim_data: The 526EZ claim attributes. Required top-level fields:
                - veteran: object with currentMailingAddress and currentlyVAEmployee
                    - currentMailingAddress: addressLine1, city, country, zipFirstFive,
                      state (for DOMESTIC type)
                    - currentlyVAEmployee: boolean
                - serviceInformation: object with servicePeriods array, each entry
                  requiring serviceBranch, activeDutyBeginDate, activeDutyEndDate
                - disabilities: array of objects, each requiring disabilityActionType
                  ("NEW" recommended) and name
                - claimantCertification: true
                - standardClaim: false for FDC, true for standard
                - autoCestPDFGenerationDisabled: false (true only for original claims
                  requiring a wet-signature PDF upload)
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.

        Example claim_data:
        {
            "veteran": {
                "currentMailingAddress": {
                    "addressLine1": "1234 Couch Street",
                    "city": "Portland",
                    "state": "OR",
                    "country": "USA",
                    "zipFirstFive": "12345",
                    "type": "DOMESTIC"
                },
                "currentlyVAEmployee": false
            },
            "serviceInformation": {
                "servicePeriods": [
                    {
                        "serviceBranch": "Air Force",
                        "activeDutyBeginDate": "1980-02-05",
                        "activeDutyEndDate": "1990-01-02"
                    }
                ]
            },
            "disabilities": [
                {
                    "disabilityActionType": "NEW",
                    "name": "PTSD (post traumatic stress disorder)"
                }
            ],
            "claimantCertification": true,
            "standardClaim": false,
            "autoCestPDFGenerationDisabled": false
        }
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(
                token.token,
                "forms/526",
                method="POST",
                json_data={"data": {"type": "form/526", "attributes": claim_data}},
                extra_headers=rep_headers,
            )
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def get_intent_to_file(
        intent_type: str = "compensation",
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Return the last active Intent to File for a claimant (GET /forms/0966/active).

        An active Intent to File preserves the earliest possible effective date for
        any retroactive benefit payments. Returns 404 if no active ITF exists for
        the given type.

        Args:
            intent_type: The ITF type to look up. One of:
                "compensation" (default), "pension", or "burial".
                For burial/DIC (Survivors Pension), include claimant identity headers.
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(
                token.token,
                "forms/0966/active",
                params={"type": intent_type},
                extra_headers=rep_headers,
            )
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_intent_to_file(
        intent_type: str = "compensation",
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Submit an Intent to File — VA Form 21-0966 (POST /forms/0966).

        Establishes an intent to file for disability compensation, pension, or burial
        claims. Secures the earliest possible effective date for retroactive payments.
        Use get_intent_to_file afterwards to confirm the ITF is active.

        Veterans cannot file a "burial" ITF (403 Forbidden); burial ITFs are filed
        by surviving dependents acting through a representative.

        Args:
            intent_type: Type of ITF to file. One of:
                "compensation" (default) — disability compensation claim.
                "pension" — pension or survivors pension.
                "burial" — Survivor's Pension / DIC; include claimant identity headers
                    to identify the surviving dependent.
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(
                token.token,
                "forms/0966",
                method="POST",
                json_data={"data": {"type": "form/0966", "attributes": {"type": intent_type}}},
                extra_headers=rep_headers,
            )
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def get_active_poa(
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Return the current active Power of Attorney for a claimant (GET /forms/2122/active).

        Returns the representative (VSO or individual) currently appointed for the
        claimant. To check the status of a specific POA submission, use get_poa_status.

        Args:
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(token.token, "forms/2122/active", extra_headers=rep_headers)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def get_poa_status(
        poa_id: str,
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Check the status of a specific POA submission by ID (GET /forms/2122/{id}).

        Returns the 21-22 submission record and its current processing status.
        The ID is returned in the response of submit_poa.

        A 200 from submit_poa does not confirm POA has been appointed — use this
        tool to confirm the POA has been established.

        Args:
            poa_id: The UUID returned when the POA form was submitted.
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(token.token, f"forms/2122/{poa_id}", extra_headers=rep_headers)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}

    @mcp.tool()
    async def submit_poa(
        poa_data: dict,
        veteran_ssn: str | None = None,
        veteran_first_name: str | None = None,
        veteran_last_name: str | None = None,
        veteran_birth_date: str | None = None,
    ) -> dict:
        """
        Submit a Power of Attorney form — VA Form 21-22 or 21-22a (POST /forms/2122).

        Appoints an accredited VSO or individual as the claimant's representative.
        The API auto-establishes POA when both veteran and representative signature
        images are included. Without signatures, use get_poa_status with the returned
        ID to track when a signed PDF must be uploaded separately.

        POA codes are issued by the Office of General Counsel (OGC). A newly appointed
        representative may not be able to submit forms for a claimant until one day
        after their POA code is first associated with the OGC data set.

        When claimant information is included in poa_data, the dependent's relationship
        to the veteran is validated and the representative is appointed to the dependent,
        not the veteran.

        Args:
            poa_data: POA form attributes. Required field:
                - serviceOrganization.poaCode: The POA code of the VSO or individual.
              Optional fields:
                - veteran: address, phone, email, serviceBranch
                - claimant: firstName, lastName, address, relationship (for dependents)
                - serviceOrganization: organizationName, firstName, lastName, jobTitle,
                  address, email, appointmentDate
                - recordConsent: boolean (Section 7332 authorization)
                - consentLimits: array of "DRUG ABUSE", "ALCOHOLISM", "HIV", "SICKLE CELL"
                - consentAddressChange: boolean
                - signatures: {veteran: <base64 PNG>, representative: <base64 PNG>}
                  (include both to auto-establish POA without a PDF upload)
            veteran_ssn: Claimant SSN — required when acting as a representative.
            veteran_first_name: Claimant first name — required when acting as a representative.
            veteran_last_name: Claimant last name — required when acting as a representative.
            veteran_birth_date: Claimant birth date in ISO 8601 format (YYYY-MM-DD)
                — required when acting as a representative.

        Example poa_data (minimal):
        {
            "serviceOrganization": {
                "poaCode": "074"
            }
        }
        """
        token = get_token()
        if token is None:
            return {"error": "Not authenticated"}

        rep_headers = build_representative_headers(
            veteran_ssn, veteran_first_name, veteran_last_name, veteran_birth_date
        )
        try:
            return await call_api(
                token.token,
                "forms/2122",
                method="POST",
                json_data={"data": {"type": "form/2122", "attributes": poa_data}},
                extra_headers=rep_headers,
            )
        except httpx.HTTPStatusError as e:
            return {"error": f"API error: {e.response.status_code}", "detail": str(e)}
