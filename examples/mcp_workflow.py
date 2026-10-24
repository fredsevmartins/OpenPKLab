"""Run the visual workflow with a real local MCP client and synthetic data only.

From the repository root:
    uv run --frozen python examples/mcp_workflow.py --data-dir .data

Each run creates a fresh experiment; existing records and exports are preserved.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(data_dir: Path) -> dict:
    data_dir = data_dir.resolve()
    source = Path(__file__).with_name("synthetic_pk.csv").resolve()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "openpklab.cli", "--data-dir", str(data_dir), "serve"],
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            async def call(name: str, **arguments) -> dict:
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise RuntimeError(f"{name}: {result.content}")
                if result.structuredContent is None:
                    raise RuntimeError(f"{name} returned no structured result")
                return result.structuredContent

            created = await call(
                "create_experiment",
                title="Synthetic PK — visual workflow example",
                category="pharmacokinetic",
                objective="Demonstrate traceable notebook operations using synthetic data only",
                conditions={"data_origin": "synthetic", "time_unit": "h", "concentration_unit": "mg/L"},
            )
            experiment_id = created["experiment"]["id"]
            await call("update_experiment_status", experiment_id=experiment_id, status="active")
            await call(
                "add_methodology", experiment_id=experiment_id, section="protocol",
                content="Software example only: use the five bundled synthetic concentrations 16, 8, 4, 2, 1 mg/L at 0, 1, 2, 3, 4 h. No biological experiment was performed.",
            )
            observation = await call(
                "add_observation", experiment_id=experiment_id,
                content="The bundled table is an analytical synthetic profile, not measured research data.",
                metadata={"data_origin": "synthetic"},
            )
            # MCP cannot receive arbitrary chat files. The local owner explicitly
            # uploads the actual bytes using the documented CLI and the same data dir.
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "openpklab.cli", "--data-dir", str(data_dir),
                "upload", experiment_id, str(source), stdout=asyncio.subprocess.PIPE,
            )
            output, _ = await process.communicate()
            if process.returncode:
                raise RuntimeError("Local CLI upload failed")
            uploaded = json.loads(output)["file"]
            file_id = uploaded["id"]
            if uploaded["sha256"] != source_hash:
                raise RuntimeError("Uploaded bytes do not match the synthetic source")
            await call(
                "attach_file", experiment_id=experiment_id, file_id=file_id,
                title="Synthetic concentration-time profile",
                metadata={"units": {"time": "h", "concentration": "mg/L"},
                          "column_descriptions": {"time": "Elapsed synthetic time", "concentration": "Synthetic concentration"},
                          "observation_ids": [observation["record"]["id"]]},
            )
            organized = await call("organize_experiment", experiment_id=experiment_id)
            quality = await call("analyze_dataset", experiment_id=experiment_id, file_id=file_id)
            options = {"time_unit": "h", "concentration_unit": "mg/L"}
            calculation = await call("run_scientific_plugin", experiment_id=experiment_id, file_id=file_id, plugin="nca", options=options)
            values = calculation["findings"]
            expected = {"cmax": 16.0, "tmax": 0.0, "auclast": 22.5, "lambda_z": math.log(2), "half_life": 1.0}
            for parameter, expected_value in expected.items():
                if not math.isclose(values[parameter], expected_value, rel_tol=1e-10, abs_tol=1e-10):
                    raise RuntimeError(f"Synthetic analytical check failed for {parameter}")
            plot = await call("run_scientific_plugin", experiment_id=experiment_id, file_id=file_id, plugin="pk_visualization", options={**options, "scale": "linear"})
            hints = await call("generate_scientific_hints", experiment_id=experiment_id)
            # A demonstration must not automatically accept scientific suggestions.
            await call("update_experiment_status", experiment_id=experiment_id, status="completed")
            report = await call("generate_experiment_report", experiment_id=experiment_id)
            artifact = await call("export_notebook", experiment_id=experiment_id)
            final = await call("get_experiment", experiment_id=experiment_id)
            if quality["rows"] != 5 or len(final["files"]) != 2 or "## Limitations" not in report["markdown"]:
                raise RuntimeError("The expected table, derived figure or report is missing")
            # The caller owns this local data directory. Remote users instead use
            # the authenticated download_path returned by export_notebook.
            archive_path = data_dir / "exports" / f"{artifact['id']}.zip"
            if hashlib.sha256(archive_path.read_bytes()).hexdigest() != artifact["sha256"]:
                raise RuntimeError("Export integrity check failed")
            return {
                "experiment_id": experiment_id,
                "data_origin": "synthetic",
                "source_sha256": source_hash,
                "table_rows": quality["rows"],
                "nca": {key: values[key] for key in expected},
                "units": values["units"],
                "figure_id": plot["findings"]["figure"]["id"],
                "hint_count": len(hints["hints"]),
                "hint_feedback": "Not submitted; scientific suggestions require researcher review",
                "missing_methodology": organized["missing_methodology"],
                "status": final["status"],
                "archive_path": str(archive_path),
                "archive_sha256": artifact["sha256"],
                "actual_chatgpt_connection_test": "Not performed; this example uses a local MCP client",
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".data"))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.data_dir)), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
