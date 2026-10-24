# Installation and operation

## Python

Use Python 3.12+; CI targets Python 3.12 on Linux. From the checkout root:

```bash
uv sync --frozen --extra dev --python 3.12
uv run --frozen --extra dev pytest -q
uv run --frozen openpklab --data-dir .data serve
```

An alternative non-locked installation is `python -m pip install .`; use the committed `uv.lock` for reproducible dependency resolution. Optional development dependencies include pytest and the wheel builder.

The stdio process is owned by the local MCP client and trusts the local filesystem owner. For private HTTP:

```bash
export OPENPKLAB_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uv run --frozen openpklab --data-dir .data serve --transport http --host 127.0.0.1 --port 8000
```

Retain the token in your own secret manager for subsequent requests. Never paste it into a ChatGPT conversation or commit it. Do not enable shell tracing. `GET /healthz` checks the service without disclosing research records. A functional check must also initialize MCP and create/retrieve a synthetic record, as the automated HTTP test does.

## Docker Compose

```bash
cp .env.example .env
# Edit .env securely: set OPENPKLAB_TOKEN to a generated random token for private-client mode.
docker compose up --build -d openpklab
docker compose ps
curl --fail http://127.0.0.1:8000/healthz
```

Named volume `notebook` retains SQLite, original objects, exports and the stable workspace profile ID. Processes run as UID 10001 with a read-only root filesystem, a writable `/data` volume and a temporary plotting cache. Only the loopback HTTP port is published by default. Restart with `docker compose up -d`; stop with `docker compose down`. Do not use `down -v` unless you intend to delete the notebook volume.

## Self-hosted HTTPS and OAuth

Use one instance per researcher. Configure a DNS hostname pointing to your host and permit inbound ports 80/443. In `.env`, set:

```dotenv
OPENPKLAB_DOMAIN=lab.example.org
OPENPKLAB_PUBLIC_URL=https://lab.example.org/mcp
OPENPKLAB_OAUTH_ISSUER=https://identity.example.org/
OPENPKLAB_OAUTH_AUDIENCE=https://lab.example.org/mcp
OPENPKLAB_OAUTH_JWKS_URL=https://identity.example.org/.well-known/jwks.json
OPENPKLAB_OWNER_SUB=the-owners-immutable-provider-subject
```

These are configuration examples, not provisioned services. Match issuer including its trailing slash exactly to token `iss`. Configure the provider to issue JWT access tokens for the exact MCP resource URL with scope `notebook`. OAuth mode takes precedence and disables private static-token access. The owner subject is mandatory; a valid token for another user is rejected.

```bash
docker compose --profile https up --build -d
```

Caddy obtains and renews TLS certificates and forwards to the authenticated server. Its volume retains certificates. Do not point `OPENPKLAB_PUBLIC_URL` at arbitrary hostnames just to suppress host validation. For an existing reverse proxy, preserve the Host header, use TLS, enforce request limits and reasonable rate limits, and keep the backend private. Only `/healthz` and OAuth resource metadata bypass bearer authentication. Configure provider/client registration as described in [ChatGPT setup](CHATGPT_SETUP.md).

## Storage, backup and limits

- SQLite uses WAL and foreign keys. One process/workspace is the supported deployment; separate databases and volumes isolate researchers. There is no organization-wide tenant or role system.
- Originals are content-addressed, written once, filesystem read-only, and rehashed before analysis/download/export. Metadata revisions and record revisions remain in event history. This detects accidental changes; it is not a signed, tamper-proof audit trail against the machine owner.
- Stop your process/container before copying the entire data directory (including database, WAL if present, `objects/`, `exports/`). Back up the profile ID in SQLite with the data. Secure backups with host-level encryption and access controls. SQLite and original files are not encrypted by this application.
- Upload maximum: 10 MiB per file, 20 megapixels per image, 10,000 rows, 1,000 columns, 100,000 cells. XLSX uncompressed contents are limited to 30 MiB and one worksheet; formula workbooks, macros and external links are rejected. CSV must be UTF-8 with unique headers. Original uploads may retain sensitive image metadata; OpenPKLab does not strip it.
- No arbitrary server path reads, URL fetching, automatic forwarding of chat attachments, PDF parsing, OCR or table extraction from documents.
- Host resource use, log retention, rate limits, quotas and secure disk disposal remain the operator's responsibility. Do not treat this MVP as a regulatory-compliant ELN.

Runtime environment: `OPENPKLAB_DATA_DIR` sets the default data location. `OPENPKLAB_TOKEN` enables private HTTP; the six OAuth/public URL settings above enable ChatGPT-compatible resource-server authentication. No external service or credentials are needed for local stdio or the synthetic tests.

## Builds behind an enterprise TLS proxy

Docker's isolated builder may need your organization's trusted public CA bundle and proxy route. The Dockerfile supports an optional BuildKit secret without placing the bundle in the image or repository:

```bash
docker build \
  --build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY \
  --secret id=custom_ca,src=/path/to/trusted-ca-bundle.pem \
  -t openpklab:0.1.0 .
```

The bundle must be obtained from your trusted platform administrator, not an unverified download. The CA is used only during dependency installation; configure runtime TLS trust separately if your identity provider requests traverse that proxy. Do not use insecure TLS flags or substitute artifact checksums. On platforms whose builder bridge cannot resolve required hosts, use the platform-supported builder network configuration; the cloud validation used `--network=host` with its provided proxy route and trusted CA.
