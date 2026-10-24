# v0.1.0 validation report

Validated on 2026-10-24 using synthetic data only. No private laboratory data is bundled.

## Automated results

Final pytest run: **113 passed, 0 failed, 0 errors, 0 skipped, 0 expected failures** in 12.95 seconds. Python 3.12.14; official MCP SDK 1.30.0. The committed lockfile records exact scientific and transport dependencies. One Starlette warning notes deprecation of its httpx test-client adapter; it did not affect results or the real HTTP test.

| Area | Executed evidence |
| --- | --- |
| Unit/storage | 32 tests in `test_notebook.py`: all experiment categories, persistence, observations, explicit revisions, methodology sections, organization, figures, tables, metadata, file integrity, reports, ZIP exports, concurrent inserts and stable profiles. |
| Integration/MCP | 12 tests in `test_mcp.py`: complete tool workflow, official stdio client with restart, and the ten simulations below. Every advertised tool has an input/output schema; all required tools are invoked. |
| Scientific validation | 31 tests in `test_science.py`: known exponential/linear cases, units, missing/nonfinite/negative data, uncertainty, terminal-fit limits, grouped/individual plots on both scales, data-quality findings, plugin registration, traceability and human hint feedback. |
| Security | 37 tests in `test_security.py`: anonymous/wrong-token access, host rejection, path traversal/filenames/types, bounded upload, unsupported/ambiguous/formula workbooks, invalid CSV headers/encoding, prompt-injection text as inert evidence, experiment/file/record association isolation, JWT signature/issuer/audience/scope/owner/time validation and public resource metadata. |
| Real HTTP | 1 test in `test_http_protocol.py`: actual subprocess/TCP server and official Streamable HTTP client, initialization, authenticated calls, actual upload, analysis, protected ZIP retrieval and persistence. |

Requested test rounds are represented by these validation areas, rather than by invented independent runner counts. The first suite found two implementation defects: empty explicit experiment IDs were treated as generated IDs, and unparameterized dict return annotations did not advertise output schemas. Both were fixed; affected tests and the full suite were rerun. Subsequent tests added real HTTP and edge-case coverage.

## Ten complete experimental simulations

All simulations create an experiment via MCP, record methods/observations, upload and annotate a real synthetic table, analyze it, retrieve evidence-linked hints, export a ZIP, mark completion, and verify persistence.

1. In vitro metabolism: synthetic incubation time and parent remaining.
2. In vitro permeability: synthetic wells, Papp and treatment labels.
3. Protein binding: synthetic fraction-unbound replicates.
4. IV PK: concentration-time profile with NCA and derived plot.
5. Oral PK: zero predose concentration, absorption peak and post-peak elimination.
6. Multiple-dose PK: explicit single occasion/dose-interval subset; no unsupported steady-state analysis claimed.
7. Translational PK/PD: synthetic concentration and response context; only the supported PK subset is calculated.
8. Missing data: original missing value remains, quality/hint flags appear, and NCA refuses silent row deletion.
9. Conflicting observations: differing explicit endpoint values generate a potential-conflict hint with uncertainty about legitimate replicates.
10. In vivo multimedia/revisions: synthetic subject measurements, a blank synthetic photograph and three explicit protocol revisions remain traceable.

These are software simulations, not biological validation of metabolism/permeability/binding/PD models. The MVP calculates the documented NCA subset, quality screens and plots only.

## Additional executed checks

- Frozen dependency installation succeeded. Wheel and source distribution built successfully.
- Docker image built using Python 3.12.15, locked dependencies, a trusted platform CA supplied via BuildKit secret, and the provided proxy route. TLS and package checksum verification remained enabled. The cloud builder also required explicit resolution of the provided proxy hostname; this is host configuration, not an application dependency.
- Non-root/read-only-root Docker container: authenticated experiment creation, actual upload, NCA, derived figure, protected ZIP retrieval, unauthorized denial, then container restart with a persistent named volume and record/file recovery all passed. Test container and its synthetic volume were removed afterward.
- Docker Compose configuration validated. Public DNS, Caddy certificate issuance and an externally deployed OAuth provider were not provisioned or tested.
- Documented local CLI create/upload/export commands executed against a temporary synthetic notebook and passed. Existing export destinations are protected from overwrite.
- `detect-secrets` 1.5.0 scanned the Git candidate files: zero findings. `.env`, runtime databases, uploads, caches, build outputs and temporary notebooks are excluded from Git. This is a secret-pattern scan, not a comprehensive independent security audit.
- Git whitespace check and source parsing passed. GitHub Actions is configured to run the automated suite, package build and container smoke test; a hosted Actions execution is not claimed without its result.

## ChatGPT and publication boundaries

Official OpenAI MCP/authentication/connection documentation was consulted directly on the validation date. OAuth resource discovery, tool annotations/profile metadata and JWT resource-server policy were tested automatically. **An actual ChatGPT login/consent/conversation was not executed.** A researcher must configure their HTTPS endpoint and identity provider and complete the interactive flow in `CHATGPT_SETUP.md`.

Git read access and receive-pack dry-run succeeded. At this report's preparation, requests to `api.github.com` were denied by the environment egress proxy (CONNECT 403), preventing GitHub visibility inspection/change and release API operations. An unauthenticated repository page returned 404, so public visibility could not be established. The allowed-domain requirement was saved in the cloud configuration draft; saving that draft does not apply it to the current instance. No v0.1.0 release is claimed until the implementation is publicly accessible and the release API operation succeeds. See the delivery message for the actual commit/push outcome.

## Limits

Single-owner instances; no shared multi-user roles, encrypted storage, signed tamper-proof audit trail, clinical/regulatory validation, arbitrary document extraction, PDF export, bioequivalence, automatic literature verification, general inferential statistics, unsolicited ChatGPT notifications or automatic forwarding of chat attachments. Unit checks require documented units; exploratory last-three-point terminal fits require human scientific review. See the plugin method documentation for exact assumptions.
