# Architecture

One Python process, one SQLite database and a local object directory serve one researcher/workspace. The official MCP Python SDK exposes structured tools over stdio or stateless Streamable HTTP. Starlette custom routes support bounded binary uploads and protected file/export downloads. The local CLI shares the same service and storage implementation.

- `storage.py`: SQLite transactions, experiment state, append-only records/revisions/events, file metadata, feedback and stable profile identity. SQL uses bound parameters. Record/file lookups include the experiment ID.
- `datasets.py`: bounded CSV/XLSX/image parsing and deterministic quality screens. No URL fetcher, document interpreter, formula execution or arbitrary MCP path access.
- `plugins.py`: deterministic science and installed-package entry-point registry. Table copies isolate plugin input changes from original storage; installed plugin code remains trusted executable code.
- `service.py`: event-triggered findings, organization, provenance and reproducible calculation records.
- `reports.py`: escaped Markdown, JSON history, portable ZIP and checksummed exports.
- `auth.py`: constant-time private bearer comparison or external OAuth resource-server JWT verification, with mandatory single-owner subject and notebook scope.
- `server.py`: MCP schemas, annotations, OAuth discovery, host/origin protections and authentication around HTTP routes.
- `cli.py`: local owner operations and transport startup.

Original bytes are stored at `objects/SHA256`, written exclusively and made read-only. Downloads, analyses and exports rehash them. File annotations increment metadata revisions and retain their earlier values in events. Scientific record corrections append a new record referring to `revises`. Hints have a content fingerprint unique within an experiment, with separate human feedback. Computational records carry source hashes, options, plugin/runtime versions and outputs. The original database and filesystem remain under the researcher's control.

The application does not call an LLM. ChatGPT retrieves context and uses its own model to interpret, propose hypotheses or recommend next steps. AI-authored notes must explicitly use `ai_suggestion` provenance. Uploaded text is untrusted evidence and cannot authorize actions. A language model still needs to enforce its own prompt-injection defenses and human confirmation policies.

HTTP requires authentication for every data/tool route. OAuth discovery and the data-free health check are public. The configured owner is the only allowed JWT subject, so other identities cannot access this workspace even with a valid provider token. Separate researcher instances/volumes provide isolation; no shared multi-user tenancy, roles, collaboration, centrally hosted SaaS or push notification infrastructure exists.

Known boundaries: no encrypted database, signed audit log, clinical validation, guaranteed tamper resistance against the machine owner, automatic token revocation introspection, arbitrary document extraction, automatic statistics/model fitting beyond the documented subset, or public plugin-directory submission. Backup, HTTPS/provider configuration, rate limits and host hardening belong to the operator.
