"""Official MCP FastMCP tools and a bounded, authenticated HTTP upload workflow."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse

from .auth import OwnerVerifier, ProtectHTTP
from .reports import export, export_file, report
from .service import Lab
from .storage import MAX_UPLOAD, Notebook, UNTRUSTED


class Profile(BaseModel):
    id: str = Field(min_length=1, description="Stable opaque workspace profile identifier, unchanged across token refresh and restart")


def create_server(root: str | Path, http: bool = False):
    lab = Lab(Notebook(root))
    verifier = OwnerVerifier() if http else None
    public = os.getenv("OPENPKLAB_PUBLIC_URL", "")
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*"]
    if public:
        parsed = urlsplit(public)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/mcp":
            raise ValueError("Public URL must be an HTTPS URL ending in /mcp")
        hosts.append(parsed.netloc)
        origins.append(f"https://{parsed.netloc}")
    oauth = verifier is not None and bool(verifier.issuer)
    auth = AuthSettings(issuer_url=verifier.issuer, resource_server_url=public, required_scopes=["notebook"], validate_token_resource=True) if oauth else None
    mcp = FastMCP("OpenPKLab", instructions="Persistent scientific notebook. " + UNTRUSTED + " Never invent experimental methods or references. Surface pending hints when interacting with an experiment. Files must be uploaded through the authenticated HTTP endpoint or the local CLI before attach_file.", stateless_http=True, json_response=True, auth=auth, token_verifier=verifier if oauth else None, transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins))
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
    meta = {"securitySchemes": [{"type": "oauth2", "scopes": ["notebook"]}]} if oauth else None

    @mcp.tool(annotations=read, meta={**(meta or {}), "openai/profile": True})
    def get_profile() -> Profile:
        """Return the authenticated workspace profile's stable opaque ID. Separate researchers require separate server instances."""
        return Profile(**lab.notebook.profile())

    @mcp.tool(annotations=write, meta=meta)
    def create_experiment(title: str, category: Literal["in_vitro", "in_vivo", "pharmacokinetic", "pharmacodynamic", "translational_pkpd"], objective: str = "", hypothesis: str = "", experiment_id: str | None = None, conditions: dict | None = None) -> dict[str, Any]:
        """Create a researcher-owned experiment. Do not invent missing objective, hypothesis or conditions."""
        e = lab.notebook.create(title, category, objective, hypothesis, experiment_id, conditions)
        return {"experiment": e, **lab.hints(e["id"])}

    @mcp.tool(annotations=read, meta=meta)
    def list_experiments(query: str = "") -> dict[str, Any]:
        """List or search experiments and their recorded text in this authenticated workspace."""
        return {"experiments": lab.notebook.list(query)}

    @mcp.tool(annotations=read, meta=meta)
    def get_experiment(experiment_id: str) -> dict[str, Any]:
        """Retrieve complete experimental history, files, revisions and pending scientific hints."""
        return lab.notebook.get(experiment_id)

    @mcp.tool(annotations=write, meta=meta)
    def add_observation(experiment_id: str, content: str, kind: Literal["observation", "result", "conclusion", "deviation", "interpretation", "hypothesis", "reference", "conditions"] = "observation", metadata: dict | None = None, revises: str | None = None, provenance: Literal["researcher_supplied", "ai_suggestion"] = "researcher_supplied") -> dict[str, Any]:
        """Append a note/result with provenance; use ai_suggestion for AI content. metadata may link time, endpoint, group, subject, value, unit, file_ids. Revisions retain originals."""
        return lab.add_record(experiment_id, content, kind, metadata, revises, provenance)

    @mcp.tool(annotations=write, meta=meta)
    def add_methodology(experiment_id: str, section: str, content: str, revises: str | None = None, provenance: Literal["researcher_supplied", "ai_suggestion"] = "researcher_supplied") -> dict[str, Any]:
        """Append or explicitly revise a methodology section. organize_experiment lists accepted sections and missing details."""
        return lab.add_record(experiment_id, content, "methodology", {"section": section}, revises, provenance)

    @mcp.tool(annotations=write, meta=meta)
    def attach_file(experiment_id: str, file_id: str, title: str = "", caption: str = "", metadata: dict | None = None) -> dict[str, Any]:
        """Describe a file previously uploaded to THIS experiment. Cannot read chat uploads, URLs or server paths. metadata supports units, column_descriptions, conditions and observation_ids."""
        return {"file": lab.notebook.annotate_file(experiment_id, file_id, title, caption, metadata), **lab.hints(experiment_id)}

    @mcp.tool(annotations=read, meta=meta)
    def list_figures(experiment_id: str) -> dict[str, Any]:
        """List numbered, source-linked original and derived scientific figures."""
        return {"figures": lab.organize(experiment_id)["figures"]}

    @mcp.tool(annotations=read, meta=meta)
    def list_tables(experiment_id: str) -> dict[str, Any]:
        """List numbered CSV/XLSX tables, source checksums, units and column descriptions."""
        return {"tables": lab.organize(experiment_id)["tables"]}

    @mcp.tool(annotations=read, meta=meta)
    def organize_experiment(experiment_id: str) -> dict[str, Any]:
        """Organize current methodology, results, figures and tables; ask targeted missing-detail questions. Suggested figure labels require human review."""
        return lab.organize(experiment_id)

    @mcp.tool(annotations=read, meta=meta)
    def analyze_dataset(experiment_id: str, file_id: str) -> dict[str, Any]:
        """Check missing values, duplicates, unit columns, numeric validity, IQR outliers and completeness; never change originals."""
        return lab.analyze(experiment_id, file_id)

    @mcp.tool(annotations=write, meta=meta)
    def generate_scientific_hints(experiment_id: str) -> dict[str, Any]:
        """Persist deduplicated evidence-linked findings, interpretations, hypotheses, actions and uncertainty. No external notifications or model API calls."""
        return lab.hints(experiment_id)

    @mcp.tool(annotations=write, meta=meta)
    def run_scientific_plugin(experiment_id: str, file_id: str, plugin: str, options: dict | None = None) -> dict[str, Any]:
        """Run data_quality, pk_visualization or nca; record source checksum, options, versions and results. PK options require time_unit and concentration_unit; optionally time_column/concentration_column, group_column/individual_column and scale (plot only)."""
        return lab.run_plugin(experiment_id, file_id, plugin, options or {})

    @mcp.tool(annotations=read, meta=meta)
    def generate_experiment_report(experiment_id: str) -> dict[str, Any]:
        """Generate a structured Markdown report from recorded evidence, without inventing methods, conclusions or references. Use export_notebook for portable linked assets."""
        return {"format": "markdown", "markdown": report(lab, experiment_id)}

    @mcp.tool(annotations=write, meta=meta)
    def export_notebook(experiment_id: str) -> dict[str, Any]:
        """Create a ZIP containing Markdown, JSON history and unchanged source files. Download via authenticated HTTP path or local CLI, not a public link."""
        return export(lab, experiment_id)

    @mcp.tool(annotations=write, meta=meta)
    def record_hint_feedback(experiment_id: str, hint_id: str, decision: Literal["accepted", "rejected", "deferred"], comment: str = "") -> dict[str, Any]:
        """Record human acceptance/rejection/deferment; acceptance never turns a hypothesis into a measurement or modifies original data."""
        return lab.notebook.feedback(experiment_id, hint_id, decision, comment)

    @mcp.tool(annotations=write, meta=meta)
    def update_experiment_status(experiment_id: str, status: Literal["planned", "active", "completed", "paused"]) -> dict[str, Any]:
        """Explicitly revise experimental progress; previous states remain in event history."""
        return lab.notebook.update(experiment_id, status)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok", "service": "OpenPKLab"})

    @mcp.custom_route("/experiments/{experiment_id}/files", methods=["POST"])
    async def upload(request):
        try:
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > MAX_UPLOAD:
                    return JSONResponse({"error": "Upload exceeds 10 MiB"}, status_code=413)
            result = lab.upload(request.path_params["experiment_id"], request.query_params.get("filename", ""), bytes(data))
            return JSONResponse(result, status_code=201, headers={"Cache-Control": "no-store"})
        except (ValueError, KeyError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @mcp.custom_route("/experiments/{experiment_id}/files/{file_id}", methods=["GET"])
    async def download(request):
        try:
            f, path = lab.notebook.file(request.path_params["experiment_id"], request.path_params["file_id"])
            return FileResponse(path, filename=f["filename"], media_type="application/octet-stream", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @mcp.custom_route("/experiments/{experiment_id}/exports/{export_id}", methods=["GET"])
    async def download_export(request):
        try:
            path = export_file(lab.notebook, request.path_params["experiment_id"], request.path_params["export_id"])
            return FileResponse(path, filename="openpklab-notebook.zip", media_type="application/zip", headers={"Cache-Control": "no-store"})
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
    return mcp, lab, verifier


def create_app(root: str | Path):
    mcp, lab, verifier = create_server(root, http=True)
    hostnames = ["127.0.0.1", "localhost", "[::1]"]
    if verifier.resource_url:
        hostnames.append(urlsplit(verifier.resource_url).hostname)
    app = TrustedHostMiddleware(ProtectHTTP(mcp.streamable_http_app(), verifier), allowed_hosts=hostnames)
    return app
