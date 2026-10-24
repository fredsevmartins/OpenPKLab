# OpenPKLab

**A digital research notebook that keeps your experiments, original data and scientific calculations together.**

OpenPKLab helps researchers document what they did, keep the supporting files, review data quality and export a traceable account of an experiment. It is open-source software under the MIT license, installed on a computer or server you control.

When connected, **ChatGPT can be your conversational interface**: you describe an experiment, ask for its recorded context, request supported analyses and review the findings. OpenPKLab stores the notebook and runs the scientific tools; ChatGPT helps you interact with them.

## What is this project for?

A research experiment produces several related things: an objective, a protocol, observations, spreadsheets, photographs, calculations and conclusions. OpenPKLab keeps those records associated with an experiment ID, so you can retrieve the evidence and understand how a result was obtained.

It supports notebook records for:

- **In vitro research:** experiments on cells, assays or other systems outside a living organism.
- **In vivo research:** experiments involving a living organism.
- **Pharmacokinetics (PK):** how drug concentrations change over time.
- **Pharmacodynamics (PD):** the relationship between drug exposure and effects.
- **Translational PK/PD:** research that connects findings across experimental contexts.

The notebook can document all these categories. Its current built-in calculations focus on basic PK summaries, concentration-time plots and data-quality screening. The available methods are described in [Scientific plugins](docs/SCIENTIFIC_PLUGINS.md).

## Why use OpenPKLab?

| Research need | What OpenPKLab provides |
| --- | --- |
| Keep the context of a result | Associate objectives, methods, conditions, observations and source files with one experiment. |
| Find previous work | Retrieve an experiment's complete history and search its recorded text. |
| Review a spreadsheet before analysis | Screen for missing values, duplicate rows, explicit unit conflicts and potentially invalid entries. |
| Understand where a calculation came from | Record the source file checksum, calculation options, method/plugin version and runtime versions. |
| Preserve evidence while correcting notes | Retain original files and append explicit record revisions with event history. |
| Prepare a research summary | Assemble recorded methods, results, tables, figures and limitations into a portable report. |
| Work through a conversation | Let a connected ChatGPT session use the notebook tools and explain their returned context. |

You control the storage location and backups. Each server instance supports one researcher/workspace. Original datasets stay intact; derived plots and computational results are stored separately and linked to their sources.

## A concrete example

Suppose you are reviewing a table of drug concentrations sampled over time. With OpenPKLab, you can:

1. Create a PK experiment and record its objective, sampling protocol and conditions.
2. Upload the original table and describe the time/concentration units.
3. Check for missing entries, duplicate rows and documented unit inconsistencies.
4. Generate a concentration-time plot and calculate the supported PK summaries: peak concentration (Cmax), time of that peak (Tmax), and area under the observed curve (AUClast). Terminal elimination and half-life estimates are available only when the documented exploratory criteria pass.
5. Review questions about missing methods or suspicious data and record your decision.
6. Export a ZIP containing the report, record history, original table and derived figure.

The result is an experimental notebook with its evidence and calculations connected. The report uses what you recorded; missing methodological information remains explicitly identified for you to complete.

The bundled example uses **synthetic data**, with Cmax 16 mg/L, Tmax 0 h and linear-trapezoidal AUClast 22.5 mg/L*h. It demonstrates the software workflow and calculation methods.

## How do I start?

### 1. Try the complete local example

Install [Git](https://git-scm.com/downloads), Python 3.12+ and [uv](https://docs.astral.sh/uv/). From a terminal, run:

```bash
git clone https://github.com/fredsevmartins/OpenPKLab.git
cd OpenPKLab
uv sync --frozen --extra dev --python 3.12
uv run --frozen python examples/mcp_workflow.py --data-dir .data
```

This runs a complete synthetic experiment: it creates records, uploads a real example CSV, checks the data, calculates PK summaries, creates a figure and exports the notebook. Each run creates a new experiment and preserves previous runs.

At the end, the terminal prints a JSON summary. Find **`archive_path`**, extract that ZIP and open **`report.md`** with a Markdown viewer. The `files/` folder contains the original CSV and generated PNG; `notebook.json` contains the recorded history. Keep the extracted folder together so the report's relative links work.

This local demonstration needs no ChatGPT login or API key after installation. It uses the official Model Context Protocol (MCP) client to call the server's tools. MCP is the connection protocol that lets a compatible assistant access those tools. The [illustrated quickstart](docs/QUICKSTART.md) explains the output and each step.

### 2. Connect ChatGPT for everyday notebook work

You or your administrator must run the OpenPKLab server and configure an authenticated connection that ChatGPT can reach. Follow [Installation](docs/INSTALLATION.md) and [ChatGPT setup](docs/CHATGPT_SETUP.md) for HTTPS, OAuth and the permitted researcher's account.

Once connected, you can ask:

> Create an experiment for my concentration-time study. Record the objective and protocol I provide, and ask me for missing methodological details.

Then upload your actual file using the documented local or authenticated upload workflow, give the returned file ID to the assistant, and ask:

> Associate this table with the experiment. The time unit is h and the concentration unit is mg/L. Review data quality, generate a concentration-time plot, run the supported NCA calculation, and explain the findings and uncertainty. Preserve the original values.

Finally:

> Show the pending scientific hints and the records behind them. Wait for my feedback, then generate the experiment report and export the notebook.

The example in step 1 verifies local MCP operation. **A real ChatGPT login, consent and conversation must be checked separately after configuring the connection.**

### 3. Use your own experimental data

Create the experiment through a connected client and note its ID. On the notebook machine, upload a file with the local-owner command:

```bash
uv run --frozen openpklab --data-dir .data upload YOUR_EXPERIMENT_ID path/to/your-data.csv
```

The command returns a file ID. Give that ID and the file's actual units/context to the connected assistant. It can then annotate the file, organize the experiment, run the supported checks and retrieve the results.

Supported files are CSV/XLSX tables and PNG/JPEG figures. Remote researchers can use the authenticated HTTP upload endpoint in [Experiment workflow](docs/EXPERIMENT_WORKFLOW.md). A file uploaded only into a ChatGPT message is not automatically available to OpenPKLab; it must be explicitly uploaded to the notebook server.

## Visual workflow

[![OpenPKLab workflow: install, connect, create an experiment, upload original data, organize and validate, run scientific plugins, review hints, export the notebook.](docs/assets/openpklab-workflow.png)](docs/QUICKSTART.md)

Open the [full-size image](docs/assets/openpklab-workflow.png) or follow the [eight-step illustrated guide](docs/QUICKSTART.md). The table and chart use only the bundled synthetic example.

## How the pieces work together

| Part | Responsibility |
| --- | --- |
| Researcher | Supplies methods and evidence, verifies units, reviews suggestions and controls scientific decisions. |
| ChatGPT or another compatible MCP client | Requests notebook operations, retrieves context and presents the returned information. ChatGPT may propose interpretations or next steps, which should be labeled as suggestions. |
| OpenPKLab server | Saves records and files, checks data, executes the supported calculations and prepares exports. |
| Your computer or server | Retains the database, original files and exports in persistent storage under your control. |

Records remain in the configured storage after a conversation or server process ends. You are responsible for retaining that storage and maintaining backups. The GitHub repository provides the source code and instructions; using the notebook requires a running local or self-hosted instance.

## Current scope

OpenPKLab **v0.1.0 is a research MVP**. It provides a notebook, deterministic data checks, three scientific plugins (`data_quality`, `pk_visualization`, `nca`) and Markdown/JSON/file ZIP export. Its interface is provided through MCP tools and a local command line.

Scientific hints generated by the server are rule-based screens with evidence links and explicit uncertainty. ChatGPT can help interpret the context; assistant-authored hypotheses and suggestions must remain distinguishable from measured results. Missing details and scientific references must be supplied and verified by the researcher.

The NCA subset and its terminal estimates are exploratory research calculations. The current version has no compartmental fitting, dose simulation, bioequivalence, PDF export, encrypted storage or shared multi-user roles. No clinical or regulatory validation is claimed. Read the [method assumptions](docs/SCIENTIFIC_PLUGINS.md) and [validation report](docs/TEST_REPORT.md) before analyzing research data.

## Documentation

| I want to… | Start here |
| --- | --- |
| Follow the eight steps and understand the example output | [Illustrated quickstart](docs/QUICKSTART.md) |
| Install Python/Docker, configure storage or deploy HTTPS | [Installation](docs/INSTALLATION.md) |
| Connect and test ChatGPT | [ChatGPT setup](docs/CHATGPT_SETUP.md) |
| Upload real files, revise records and export a notebook | [Experiment workflow](docs/EXPERIMENT_WORKFLOW.md) |
| Understand calculations or add a scientific plugin | [Scientific plugins](docs/SCIENTIFIC_PLUGINS.md) |
| Review tests and limitations | [Test report](docs/TEST_REPORT.md) |
| Understand storage, security or contribute | [Architecture](docs/ARCHITECTURE.md), [Security](SECURITY.md), [Contributing](CONTRIBUTING.md) |

## Development checks

From the checkout root:

```bash
uv run --frozen --extra dev pytest -q
uv build
```

All bundled examples and tests use synthetic data. Keep real research records, credentials and `.env` files out of Git. OpenPKLab makes no server-side LLM calls and requires no OpenAI API key for its local notebook tools.
