import httpx

from src.va_claims.utils import build_representative_headers, call_api, format_api_error, get_token


def validate_526_claim(claim_data: dict) -> list[str]:
    """
    Pre-flight validation of a 526EZ claim payload against the VA schema's
    required fields. Returns a list of human-readable problems (empty if valid).

    This mirrors the "required" constraints in the POST /forms/526 request
    schema so the caller gets an actionable message instead of a raw VA 422.
    It intentionally checks presence/shape only — the VA remains the source of
    truth for full validation (patterns, enums, dates).
    """
    problems: list[str] = []

    if not isinstance(claim_data, dict):
        return ["claim_data must be a JSON object (the 526 'attributes')."]

    # Keys the VA 526 schema allows on currentMailingAddress. The schema uses
    # additionalProperties: false, so any other key (e.g. the common mistake
    # "addressType" — the correct field is "type") triggers a 422.
    allowed_address_keys = {
        "addressLine1",
        "addressLine2",
        "addressLine3",
        "city",
        "country",
        "zipFirstFive",
        "zipLastFour",
        "internationalPostalCode",
        "type",
        "state",
        "militaryStateCode",
        "militaryPostOfficeTypeCode",
    }

    # Top-level required keys (schema: required veteran, serviceInformation,
    # disabilities, standardClaim, autoCestPDFGenerationDisabled).
    for key in (
        "veteran",
        "serviceInformation",
        "disabilities",
        "standardClaim",
        "autoCestPDFGenerationDisabled",
    ):
        if key not in claim_data:
            problems.append(f"Missing required field: {key}")

    # veteran: required currentMailingAddress + currentlyVAEmployee.
    veteran = claim_data.get("veteran")
    if isinstance(veteran, dict):
        if "currentlyVAEmployee" not in veteran:
            problems.append("Missing required field: veteran.currentlyVAEmployee (boolean)")
        addr = veteran.get("currentMailingAddress")
        if not isinstance(addr, dict):
            problems.append("Missing required field: veteran.currentMailingAddress")
        else:
            # Reject unknown keys up front (schema is additionalProperties: false).
            for key in addr:
                if key not in allowed_address_keys:
                    hint = ""
                    if key == "addressType":
                        hint = ' (use "type" instead of "addressType")'
                    problems.append(
                        f"Unknown field veteran.currentMailingAddress.{key} is not "
                        f"allowed by the VA schema{hint}"
                    )
            addr_type = addr.get("type", "DOMESTIC")
            if addr_type == "DOMESTIC":
                required_addr = ["addressLine1", "city", "country", "zipFirstFive", "state"]
            elif addr_type == "INTERNATIONAL":
                required_addr = ["addressLine1", "city", "country", "internationalPostalCode"]
            elif addr_type == "MILITARY":
                required_addr = [
                    "addressLine1",
                    "country",
                    "zipFirstFive",
                    "militaryStateCode",
                    "militaryPostOfficeTypeCode",
                ]
            else:
                required_addr = []
                problems.append(
                    f"veteran.currentMailingAddress.type must be DOMESTIC, "
                    f"INTERNATIONAL, or MILITARY (got {addr_type!r})"
                )
            for field in required_addr:
                if not addr.get(field):
                    problems.append(
                        f"Missing required field: veteran.currentMailingAddress.{field} "
                        f"(required for {addr_type} address)"
                    )
    elif veteran is not None:
        problems.append("veteran must be a JSON object")

    # serviceInformation: required servicePeriods (>=1), each with branch + dates.
    service_info = claim_data.get("serviceInformation")
    if isinstance(service_info, dict):
        periods = service_info.get("servicePeriods")
        if not isinstance(periods, list) or not periods:
            problems.append(
                "serviceInformation.servicePeriods must be a non-empty array"
            )
        else:
            for i, period in enumerate(periods):
                if not isinstance(period, dict):
                    problems.append(f"serviceInformation.servicePeriods[{i}] must be an object")
                    continue
                for field in ("serviceBranch", "activeDutyBeginDate", "activeDutyEndDate"):
                    if not period.get(field):
                        problems.append(
                            f"Missing required field: "
                            f"serviceInformation.servicePeriods[{i}].{field}"
                        )
    elif service_info is not None:
        problems.append("serviceInformation must be a JSON object")

    # disabilities: required array (>=1), each with disabilityActionType + name.
    disabilities = claim_data.get("disabilities")
    if isinstance(disabilities, list):
        if not disabilities:
            problems.append("disabilities must be a non-empty array")
        for i, disability in enumerate(disabilities):
            if not isinstance(disability, dict):
                problems.append(f"disabilities[{i}] must be an object")
                continue
            for field in ("disabilityActionType", "name"):
                if not disability.get(field):
                    problems.append(f"Missing required field: disabilities[{i}].{field}")
    elif disabilities is not None:
        problems.append("disabilities must be a non-empty array")

    return problems


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
            return format_api_error(e)

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
            return format_api_error(e)

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
                      state (for DOMESTIC type). The residence type field is named
                      "type" (NOT "addressType") with values DOMESTIC / INTERNATIONAL
                      / MILITARY.
                    - currentlyVAEmployee: boolean
                IMPORTANT: The VA 526 schema is strict (additionalProperties: false).
                Do NOT invent or rename fields — any key not defined in the schema
                (e.g. "addressType") causes a 422 rejection.
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

        # Pre-flight validation against the 526 schema's required fields so the
        # caller gets an actionable message instead of a raw VA 422.
        problems = validate_526_claim(claim_data)
        if problems:
            return {
                "error": "Invalid claim_data",
                "detail": problems,
                "hint": "Fix the listed fields and resubmit. See the tool "
                "description for the full 526EZ claim_data shape.",
            }

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
            return format_api_error(e)

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
            return format_api_error(e)

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
            return format_api_error(e)

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
            return format_api_error(e)

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
            return format_api_error(e)

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
            return format_api_error(e)
