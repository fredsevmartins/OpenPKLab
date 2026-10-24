# OpenPKLab visual quickstart

From experimental data to a traceable scientific notebook. Follow the eight steps below; they correspond to the workflow image in the README.

![OpenPKLab workflow: install, connect, create, upload, organize and validate, run science, review hints, export.](assets/openpklab-workflow.png)

[Open the full-size workflow image](assets/openpklab-workflow.png).

The table and concentration-time curve are synthetic illustrations based on `examples/synthetic_pk.csv`. They are not measurements or fitted compartmental models. This project is Python/MCP software, with the documented NCA subset; it does not implement the R project or the additional modeling capabilities in the inspiration image.

## Run the complete example first

After installing Python 3.12+ and [uv](https://docs.astral.sh/uv/), run:

```bash
git clone https://github.com/fredsevmartins/OpenPKLab.git
cd OpenPKLab
uv sync --frozen --extra dev --python 3.12
uv run --frozen python examples/mcp_workflow.py --data-dir .data
```

The example launches the real MCP server and communicates with it using the official SDK's stdio client. It creates a fresh experiment, saves a method and observation, explicitly uploads the bundled CSV through the local CLI, annotates it, checks data quality, runs NCA, generates a plot, retrieves hints and exports a complete ZIP. It checks the source/export hashes and analytical calculation results before printing the summary.

It requires no account, network service, API key or ChatGPT login after dependencies are installed. Each run creates a different experiment and export, preserving earlier runs. It does not automatically accept scientific suggestions. The final JSON prints the experiment ID and `archive_path`; extract that ZIP and open `report.md` alongside its relative `files/` assets. The report records missing methods explicitly.

For the bundled synthetic data, expect:

| Parameter | Expected value | Unit |
| --- | --- | --- |
| Cmax | 16 | mg/L |
| First Tmax | 0 | h |
| Linear trapezoidal AUClast | 22.5 | mg/L*h |
| Exploratory lambda-z | approximately 0.693147 | 1/h |
| Exploratory terminal half-life | 1 | h |

Terminal values are exploratory estimates using the documented last-three-point criteria. These numbers validate a software example, not a biological study. Read [calculation methods](SCIENTIFIC_PLUGINS.md) before analyzing real data.

## 1. Install

The commands above use the committed dependency lockfile. Work from the repository root. For Docker, persistent volumes, TLS, secure backups and private HTTP, see [Installation](INSTALLATION.md).

## 2. Connect a client

For a compatible local MCP client, configure the executable as the absolute path to `.venv/bin/openpklab`, with arguments `--data-dir`, the absolute path to `.data`, and `serve`. The client launches and owns the stdio process. The runnable example performs this connection for you and stops its server when finished.

For **ChatGPT**, configure an authenticated reachable endpoint, normally HTTPS at `/mcp`, plus an OAuth 2.1 provider and the permitted owner's subject. Follow [ChatGPT setup](CHATGPT_SETUP.md). A local stdio process is not automatically available to ChatGPT, and private static API tokens do not replace its OAuth flow. A real ChatGPT login/consent/conversation remains a separate interactive check.

## 3. Create and document an experiment

In a connected ChatGPT conversation, ask:

> Create a pharmacokinetic experiment titled Synthetic PK with ID synthetic-pk. The objective is to validate a software example. Record that all data are synthetic and no biological experiment was performed. Add only the methodology I supply; ask for missing details.

This uses `create_experiment`, `add_methodology` and `add_observation`. Categories also cover in vitro, in vivo, pharmacodynamic and translational PK/PD studies. `get_experiment` retrieves history; `list_experiments` searches records. Record conditions, deviations, conclusions and evidence associations in flexible metadata. Corrections use explicit revisions, preserving previous records.

The automated example uses a fresh UUID instead of `synthetic-pk` so reruns cannot overwrite an existing experiment. To work with its records, use the ID printed by the example.

## 4. Upload original data

After creating `synthetic-pk` through MCP, explicitly upload from the notebook machine:

```bash
uv run --frozen openpklab --data-dir .data upload synthetic-pk examples/synthetic_pk.csv
```

Give the returned file ID to the assistant and ask it to call `attach_file` with a title, column descriptions and units: `time: h`, `concentration: mg/L`. Files are already associated with the experiment on upload; `attach_file` adds descriptive metadata. Supported formats: CSV/XLSX tables and PNG/JPEG figures. The source bytes and SHA-256 checksum are retained.

A file attached only to a ChatGPT message has not been uploaded to this server. Remote researchers use the authenticated binary upload endpoint described in [Experiment workflow](EXPERIMENT_WORKFLOW.md). Never put credentials in the conversation.

## 5. Organize and validate

Ask:

> Organize this experiment's methods, results, figures and tables. Analyze the uploaded table for missing values, duplicates, invalid numeric values and unit inconsistencies. Ask targeted questions about missing methodological details. Preserve the original values.

`organize_experiment`, `list_figures`, `list_tables` and `analyze_dataset` return recorded context and deterministic checks. A clean quality screen does not prove that undocumented units, protocol choices or biological conclusions are correct.

## 6. Run scientific plugins

Use the uploaded file ID and the correct experiment ID:

```json
{
  "experiment_id": "synthetic-pk",
  "file_id": "FILE_ID_FROM_UPLOAD",
  "plugin": "nca",
  "options": {"time_unit": "h", "concentration_unit": "mg/L"}
}
```

Call `run_scientific_plugin` with the payload above. Change `plugin` to `pk_visualization` for a derived PNG; add `"scale": "log"` only when every concentration is positive. `data_quality` is the third built-in plugin. Calculations store source checksums, options, plugin/runtime versions and computational results. These are not measured observations. No compartmental fitting, dosing simulator or bioequivalence module is included.

## 7. Review scientific hints

Ask:

> Retrieve pending scientific hints. Separate observed evidence, computational findings, interpretation, hypotheses, recommended actions and uncertainty. Explain which records support each finding. Wait for my decision before recording feedback.

`generate_scientific_hints` retrieves stored, deduplicated findings; `record_hint_feedback` records the researcher's accepted/rejected/deferred decision. Acceptance does not confirm a hypothesis or rewrite original data. Label assistant-authored notes with `provenance: ai_suggestion`. There are no unsolicited ChatGPT notifications.

## 8. Export the notebook

Ask for `generate_experiment_report` and `export_notebook`. The export contains:

```text
report.md
notebook.json
files/
  FILE_ID/
    original-or-derived-file
```

For local ownership, export to a new filename:

```bash
uv run --frozen openpklab --data-dir .data export synthetic-pk synthetic-pk.zip
```

The example already prints a ready ZIP's local `archive_path`; no second export is needed. Remote download paths require authentication and are not public share links. Protect exported notebooks like the original research data.

## Find more detail

| Task | Documentation |
| --- | --- |
| Python, Docker, HTTPS, persistence and backups | [Installation](INSTALLATION.md) |
| OAuth and actual ChatGPT connection | [ChatGPT setup](CHATGPT_SETUP.md) |
| Data upload, revisions and MCP payloads | [Experiment workflow](EXPERIMENT_WORKFLOW.md) |
| Scientific assumptions and new plugins | [Scientific plugins](SCIENTIFIC_PLUGINS.md) |
| Verified tests and remaining limitations | [Test report](TEST_REPORT.md) |
| Threat model and private data | [Security](../SECURITY.md) |

The workflow image is included under the repository's MIT license. Its UI illustrations are explanatory; the underlying notebook is accessed through MCP tools and the CLI. Product names/logos identify compatible technologies and do not imply endorsement.
