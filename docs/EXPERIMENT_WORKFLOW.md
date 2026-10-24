# Experimental workflow

## Create and document

Use `create_experiment` with a title, category and optional objective, hypothesis, conditions and researcher ID. Categories: `in_vitro`, `in_vivo`, `pharmacokinetic`, `pharmacodynamic`, `translational_pkpd`. IDs accept letters, digits, underscores and hyphens. Generated IDs are UUIDs.

Use `add_observation` for observations, results, conclusions, deviations, interpretations, hypotheses, verified references or conditions. Flexible `metadata` can include time, endpoint, treatment group, subject, value, unit and associated `file_ids`. Use `provenance: ai_suggestion` for ChatGPT-generated hypotheses, methods or interpretations; never present these as measured evidence.

`add_methodology` accepts one of: `objective`, `materials`, `equipment`, `biological_system`, `experimental_design`, `protocol`, `sampling_schedule`, `analytical_methodology`, `data_processing`, `statistical_analysis`, `deviations_and_limitations`. Add gradually. To correct a record, supply `revises` with its ID; old versions remain. AI suggestions are labeled and do not satisfy missing measured-method documentation.

## Attach actual data

For local ownership, run `openpklab --data-dir YOUR_DATA_DIR upload EXPERIMENT_ID path/to/file.csv` on the server machine. The CLI intentionally has the local filesystem owner's access. Remote users upload bytes over authenticated HTTPS:

```bash
# Replace the base URL and experiment ID; obtain the bearer token securely.
# In OAuth mode this must be an unexpired OAuth access token with scope notebook.
export OPENPKLAB_URL=https://lab.example.org
curl --fail-with-body --request POST \
  "$OPENPKLAB_URL/experiments/synthetic-pk/files?filename=synthetic_pk.csv" \
  --header "Authorization: Bearer $OPENPKLAB_ACCESS_TOKEN" \
  --header 'Content-Type: application/octet-stream' \
  --data-binary @examples/synthetic_pk.csv
```

Set `OPENPKLAB_ACCESS_TOKEN` using your secret manager/provider client. In private-client mode you can use your server's private token. Do not paste credentials into chat. Filenames are safe basenames, not paths; URL-encode a filename containing spaces. Use CSV/XLSX for tables or PNG/JPEG for figures. The response returns a file ID, checksum and findings. Upload is associated with an existing experiment immediately; `attach_file` then adds its human title, caption and metadata:

```json
{
  "experiment_id": "synthetic-pk",
  "file_id": "FILE_ID_FROM_UPLOAD",
  "title": "Synthetic concentration-time measurements",
  "metadata": {
    "units": {"time": "h", "concentration": "mg/L"},
    "column_descriptions": {"time": "Elapsed time", "concentration": "Synthetic concentration"},
    "conditions": {"data_origin": "synthetic"},
    "observation_ids": []
  }
}
```

No tool reads arbitrary server paths, downloads arbitrary URLs, or claims to receive files uploaded only to ChatGPT. Figures and tables are numbered independently per experiment. Minimal suggested figure labels use only the supplied filename; meaningful captions require recorded context and human review.

## Organize and analyze

`organize_experiment` returns current methodology revisions, targeted questions for missing details, results grouped by explicit time/endpoint/group metadata, tables, figures and suggested labels. `get_experiment` returns the full history including superseded revisions. `list_experiments(query)` searches titles/metadata and record contents.

`analyze_dataset` screens original table data. `run_scientific_plugin` stores reproducible calculations and derived plots. Examples for the bundled synthetic table:

```json
{"experiment_id":"synthetic-pk", "file_id":"FILE_ID_FROM_UPLOAD", "plugin":"nca", "options":{"time_unit":"h", "concentration_unit":"mg/L"}}
```

Change the plugin to `pk_visualization` to create a derived figure; add `"scale":"log"` for a log plot with strictly positive data. Original measurements are unchanged. See [Scientific methods](SCIENTIFIC_PLUGINS.md) for assumptions and limitations.

`generate_scientific_hints` returns evidence-linked checks and uncertainty. `record_hint_feedback` records explicit human decisions. Findings surface on interactions; there are no unsolicited ChatGPT notifications. `update_experiment_status` tracks planned/active/paused/completed states.

## Report and export

`generate_experiment_report` returns Markdown with the required scientific sections and labels unrecorded details. `export_notebook` writes a ZIP with `report.md`, complete `notebook.json`, and exact original and derived files under `files/FILE_ID/FILENAME`. Relative image/table links work after extraction. Full raw tables are included; Markdown previews show up to 100 rows.

The tool returns an authentication-required download path. Download using a compatible authenticated client:

```bash
curl --fail-with-body "$OPENPKLAB_URL/experiments/EXPERIMENT_ID/exports/EXPORT_ID" \
  --header "Authorization: Bearer $OPENPKLAB_ACCESS_TOKEN" \
  --output notebook.zip
```

Alternatively, the local owner runs `openpklab --data-dir YOUR_DATA_DIR export EXPERIMENT_ID notebook.zip`. Existing destination files are not overwritten. ZIP exports contain research data: protect them like the original notebook. No PDF renderer or automatic bibliography verification is included.
