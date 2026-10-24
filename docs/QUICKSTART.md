# OpenPKLab visual quickstart

OpenPKLab is a digital laboratory notebook: it keeps an experiment's objective, methods, original files, observations and calculations together. A connected ChatGPT session can help you operate the notebook through a conversation. Your records are stored on the computer or server running OpenPKLab.

This guide walks through one complete example so you can see what the project produces before configuring a ChatGPT connection. For the project's purpose, benefits and supported research categories, read [What is OpenPKLab?](../README.md).

## Choose your starting point

| Your goal | What to do |
| --- | --- |
| See the software working on synthetic data | Run the complete local example below. No ChatGPT account or remote server is needed. |
| Use ChatGPT to manage your notebook | Try the example first, then follow step 2 and [ChatGPT setup](CHATGPT_SETUP.md). |
| Record your own research | Create an experiment through a connected MCP client, supply its methods/context and upload the actual files in steps 3–4. |

By the end of the local example, you will have a saved experiment, a checked CSV, a concentration-time figure, reproducible PK calculations and a ZIP report. The eight numbered steps explain how to carry out the same workflow with a connected assistant.

![OpenPKLab workflow: install, connect, create, upload, organize and validate, run science, review hints, export.](assets/openpklab-workflow.png)

[Open the full-size workflow image](assets/openpklab-workflow.png).

The table and concentration-time curve are synthetic illustrations based on `examples/synthetic_pk.csv`. They are not measurements or fitted compartmental models. This project is Python/MCP software, with the documented NCA subset; it does not implement the R project or the additional modeling capabilities in the inspiration image.

## Run the complete example first

Install Git, Python 3.12+ and [uv](https://docs.astral.sh/uv/), then run these commands in a terminal from a Unix-style shell (for Windows, use WSL):

```bash
git clone https://github.com/fredsevmartins/OpenPKLab.git
cd OpenPKLab
uv sync --frozen --extra dev --python 3.12
uv run --frozen python examples/mcp_workflow.py --data-dir .data
```

The example launches the real MCP server and communicates with it using the official SDK's stdio client. It creates a fresh experiment, saves a method and observation, explicitly uploads the bundled CSV through the local CLI, annotates it, checks data quality, runs NCA, generates a plot, retrieves hints and exports a complete ZIP. It checks the source/export hashes and analytical calculation results before printing the summary.

It requires no account, network service, API key or ChatGPT login after dependencies are installed. Each run creates a different experiment and export, preserving earlier runs. It does not automatically accept scientific suggestions. The final JSON prints the experiment ID and `archive_path`; extract that ZIP and open `report.md` alongside its relative `files/` assets. The report records missing methods explicitly.

### Understand what you receive

The terminal prints a JSON summary at the end. These fields tell you where the experiment and its outputs are:

| Output field | Meaning / next action |
| --- | --- |
| `experiment_id` | The saved notebook record to retrieve in a connected client. Copy it when asking about this particular run. |
| `data_origin` | `synthetic`: the demonstration contains no measured laboratory data. |
| `nca` and `units` | Calculated PK summaries and their units. Compare them with the expected values below. |
| `figure_id` | The saved concentration-time figure associated with this experiment. |
| `missing_methodology` | Details not documented in this software example. Real studies need researcher-supplied methods. |
| `archive_path` | The ZIP on your computer. Extract it and open `report.md` with a Markdown viewer. |
| `archive_sha256` | A checksum for checking the exported archive's integrity. |

After extracting the ZIP, keep `report.md`, `notebook.json` and the `files/` folder together. The report includes scientific sections and links to its figure/table sources. The CSV contains the unchanged source data; the PNG is a derived graph; the JSON contains the recorded history.

The command finishes after completing the example. For everyday use, a local MCP client launches the stdio server, or a running authenticated HTTP server handles requests from a configured remote client. Publishing the source to GitHub does not start that service or automatically connect ChatGPT.

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

## Practical notes for first use

**Trying the software locally.** The runnable example uses a local MCP client and performs the complete synthetic workflow after installation. ChatGPT is an optional conversational interface that needs its own configured connection.

**Finding your records.** With the commands in this guide, records live in the `.data` directory on the machine running the server. Original objects, database records and exports remain there after the example exits. Preserve that directory and follow the backup instructions in [Installation](INSTALLATION.md).

**Using a real table.** Explicitly upload it to the notebook server through the local CLI or authenticated endpoint. Then give the connected assistant its returned file ID and actual units. The notebook server cannot assume a chat attachment was forwarded to it.

**Understanding the assistant's role.** It can retrieve recorded context, request tools and explain findings or propose next steps. OpenPKLab's built-in hints screen recorded data and missing documentation. Researcher review is required before treating an interpretation or proposed action as scientifically justified.

**Recognizing a successful example.** The command exits successfully, prints the expected PK values and points to an existing ZIP containing the report, original CSV and generated PNG. The script checks the analytical results and file checksums itself; it fails if those checks do not match.

**Completing the scientific record.** Missing report sections remain identified as missing. Supply the actual protocol and conditions; suggestions do not establish that a procedure was performed.

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
