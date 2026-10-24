# ChatGPT connection

OpenPKLab uses the official Python MCP SDK's Streamable HTTP transport at `/mcp`. It returns structured tool results without a separate web application. The server is an OAuth resource server; your identity provider owns login, consent, client registration and authorization-code/refresh-token flows.

## Supported authenticated flow

1. Deploy an instance with persistent storage at a reachable HTTPS endpoint; follow [Installation](INSTALLATION.md). A compatible private connection mechanism such as the officially documented Secure MCP Tunnel may also be available to your workspace; this repository does not provision or validate that service.
2. Configure an OAuth 2.1 provider (for example, a correctly configured Auth0 tenant). It must expose OAuth/OIDC discovery metadata, an authorization endpoint, a token endpoint, and `code_challenge_methods_supported: ["S256"]`. Use a supported predefined OAuth client, dynamic client registration (DCR), or Client ID Metadata Documents (CIMD). Follow your provider's current MCP documentation.
3. Configure a resource/API audience equal to the exact HTTPS MCP URL, e.g. `https://lab.example.org/mcp`. Ensure the OAuth `resource` parameter is honored and JWT access tokens carry that audience and the `notebook` scope. OpenPKLab accepts RS256/ES256 signatures using the configured JWKS endpoint; it validates issuer, audience, expiry, issued-at, not-before when present, scope and the single owner's immutable `sub`. Opaque access tokens are unsupported.
4. Set the server's OAuth environment variables and restart. Confirm unauthenticated MCP calls return 401 with `WWW-Authenticate` pointing to `/.well-known/oauth-protected-resource/mcp`; that public metadata advertises the issuer and `notebook` scope. Never expose notebook contents as an anonymous workaround.
5. In the current official ChatGPT flow, open **ChatGPT Plugins**, choose **+ → Add custom MCP server**, enter the `/mcp` URL, and configure OAuth. Account/workspace policies and rollout may affect availability and UI labels. Register the exact redirect URI displayed by ChatGPT at your provider; do not guess a universal callback URL. The provider must allow the advertised token endpoint authentication method and all requested OIDC scopes.
6. Complete authorization as the configured owner, create/install the plugin, review its discovered tools, and select it with `@` in a new conversation. If your account exposes the earlier Apps/developer-mode interface, use its custom MCP connection flow with the same endpoint and OAuth requirements.
7. Ask it to create a synthetic experiment, add a method and observation, retrieve them, run the example calculation after a supported file upload, and export. Verify the actual tool results. Refresh the connection's metadata after tool changes.

The `get_profile` tool returns a persisted opaque workspace ID and advertises `openai/profile`. The same workspace ID survives token refresh and restart. This server accepts only one configured owner; deploy separate instances for independently authorized researchers.

## Files and notifications

A chat attachment is not automatically a server attachment. Download your original file and upload it through the local CLI or authenticated HTTPS upload endpoint in [Experiment workflow](EXPERIMENT_WORKFLOW.md). Supply the returned file ID to ChatGPT. `attach_file` accepts only an existing file in the identified experiment, never a local path or URL. Do not put tokens in the conversation. Protected download paths require an authenticated client; ChatGPT may not render them as clickable downloads.

Pending scientific hints are saved when records/datasets/results change and returned on subsequent tool interactions. There is no promise of background ChatGPT execution, unsolicited messages or proactive notifications.

## Verification boundaries

Automated tests exercise the official SDK's initialization, schemas, tool calls, stdio restart persistence and authenticated Streamable HTTP, plus JWT verification and resource discovery. They do **not** perform a real ChatGPT login/consent/session or validate a user's identity provider, HTTPS DNS/certificate deployment, tunnel, or account entitlement. Complete step 7 interactively before relying on the connection.

Sources consulted on 2026-10-24:

- [OpenAI: build an MCP server](https://developers.openai.com/apps-sdk/build/mcp-server)
- [OpenAI: authentication](https://developers.openai.com/apps-sdk/build/auth)
- [OpenAI: connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt)
- [Official OpenAI Python authentication example](https://github.com/openai/openai-apps-sdk-examples/tree/main/authenticated_server_python)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

The private `OPENPKLAB_TOKEN` mode supports compatible private MCP/HTTP clients. ChatGPT does not accept arbitrary custom API keys in place of its OAuth user connection.
