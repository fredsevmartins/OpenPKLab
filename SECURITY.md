# Security

Use one instance and volume per researcher. HTTP fails closed without an adequate private token or complete OAuth configuration. OAuth JWTs require a verified signature, expected issuer/audience, expiry, issued-at, valid not-before where present, notebook scope and the configured owner subject. Static tokens are intended for compatible private clients, not ChatGPT's OAuth flow.

Upload basenames, types, byte limits, image dimensions and workbook expansion are checked. Formula workbooks, macros and external workbook links are rejected. Source file reads are experiment-scoped and checksum-verified. HTML in reports is escaped. There is no arbitrary URL fetch, server-path attachment, shell execution tool or public download route. Originals in exported CSV/XLSX remain original data; inspect untrusted content before opening it with third-party spreadsheet software.

Research notes, filenames and table cells may contain adversarial instructions. OpenPKLab labels them as untrusted evidence and never executes them or lets them change access policy. A connected model must continue to apply its own instruction hierarchy and user authorization checks; text labeling is not a proof that an LLM is immune to prompt injection.

The machine owner can modify local data; this is not a cryptographically signed audit trail. Data/exports are not encrypted by the application. Plugins execute trusted Python code. JWTs are locally verified until expiration; provider-side revocation may require short lifetimes or external controls. Deploy behind HTTPS with rate limits, secure file permissions, encrypted disks/backups where required, and appropriate research governance. No regulatory compliance is claimed.

Do not publish vulnerabilities containing private records or credentials. Use the repository's private vulnerability reporting facility if enabled; otherwise contact the maintainer through a private channel identified on their GitHub profile. If no private channel exists, open a minimal issue requesting private contact without exploit details or sensitive data.
