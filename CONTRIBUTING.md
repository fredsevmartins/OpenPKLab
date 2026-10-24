# Contributing

Use English for code, documentation, labels and examples. Keep changes small and use synthetic research data only.

```bash
uv sync --frozen --extra dev --python 3.12
uv run --frozen --extra dev pytest -q
uv build
```

When changing dependencies, run `uv lock` and include the lockfile. Preserve original data, traceable revisions and explicit scientific uncertainty. Add analytical expected-value tests for scientific methods and protocol/security tests for transport changes. Do not remove failing assertions to make a change pass. Third-party science extensions should use the entry-point interface in `docs/SCIENTIFIC_PLUGINS.md`.

Open a pull request explaining the problem, behavior, scientific assumptions and executed validation. Never attach private laboratory records, credentials or `.env` files. MIT licensing applies to contributions.
