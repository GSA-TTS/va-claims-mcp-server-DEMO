# VA Claims MCP Server

An MCP (Model Context Protocol) server that provides secure access to VA.gov Benefits Claims API. This enables AI assistants to help veterans check claim status, submit claims, and manage their VA benefits.

## Features

- **OAuth 2.0 Authentication**: Secure access via VA.gov OAuth
- **Claim Status**: Check the status of existing claims
- **List Claims**: View all claims for a veteran
- **Submit Claims**: Submit disability compensation claims (21-526EZ)
- **Intent to File**: Manage intent to file to preserve effective dates
- **Power of Attorney**: Submit and manage POA appointments (21-22 / 21-22a)

## Tools Available

| Tool | Description | Scope Required |
|------|-------------|----------------|
| `list_claims` | List all claims for the veteran | claim.read |
| `get_claim_status` | Get status of a specific claim | claim.read |
| `submit_disability_claim` | Submit a new disability claim (21-526EZ) | claim.write |
| `get_intent_to_file` | Get current intent to file status | claim.read |
| `submit_intent_to_file` | Submit a new intent to file (21-0966) | claim.write |
| `get_active_poa` | Get the current active Power of Attorney | claim.read |
| `get_poa_status` | Check status of a specific POA submission | claim.read |
| `submit_poa` | Submit a Power of Attorney form (21-22 / 21-22a) | claim.write |

## Setup

### Prerequisites

1. Register for API access at [developer.va.gov](https://developer.va.gov)
2. Create an application and obtain OAuth credentials
3. Set your redirect URI to: `https://your-server-url/auth/callback`

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/va-claims-mcp-server.git
   cd va-claims-mcp-server
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your VA OAuth credentials
   ```

5. Run the development server:
   ```bash
   uvicorn src.va_claims.server:app --host 0.0.0.0 --port 8000 --reload
   ```

### Cloud.gov Deployment

1. Login to Cloud.gov:
   ```bash
   cf login -a api.fr.cloud.gov --sso
   ```

2. Set environment variables:
   ```bash
   cf set-env va-claims-mcp-server BASE_URL https://va-claims-mcp.app.cloud.gov
   cf set-env va-claims-mcp-server VA_CLIENT_ID <your-client-id>
   cf set-env va-claims-mcp-server VA_CLIENT_SECRET <your-client-secret>
   ```

3. Deploy:
   ```bash
   cf push
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VA_CLIENT_ID` | OAuth client ID from VA | Required |
| `VA_CLIENT_SECRET` | OAuth client secret from VA | Required |
| `BASE_URL` | Server's public URL | `http://localhost:8000` |
| `VA_API_BASE` | VA Claims API base URL | `https://sandbox-api.va.gov/services/claims/v2` |
| `VA_OAUTH_BASE` | VA OAuth base URL | `https://sandbox-api.va.gov/oauth2` |

## Production Configuration

For production deployment, update the environment variables:

```bash
cf set-env va-claims-mcp-server VA_API_BASE https://api.va.gov/services/claims/v2
cf set-env va-claims-mcp-server VA_OAUTH_BASE https://api.va.gov/oauth2
```

## API Reference

This server implements the [VA Benefits Claims API](https://developer.va.gov/explore/api/benefits-claims/docs).

### Claim Statuses

Claims can have the following statuses:
- Pending
- Claim received
- Initial review
- Evidence gathering, review, and decision
- Preparation for notification
- Complete
- Errored
- Canceled

## Security

- All API calls require OAuth 2.0 authentication
- Tokens are validated against VA's userinfo endpoint
- Veteran identity (ICN) is extracted from authenticated tokens
- Credentials should be stored securely (environment variables, not in code)

## License

See [LICENSE](LICENSE) for details.
