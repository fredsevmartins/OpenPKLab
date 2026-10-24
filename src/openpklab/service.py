"""Notebook workflows shared by the MCP, CLI and upload transport."""
from __future__ import annotations
from .datasets import quality, read_table
from .plugins import Registry
from .storage import Notebook, SECTIONS, UNTRUSTED


class Lab:
    def __init__(self, notebook: Notebook, registry: Registry | None = None):
        self.notebook = notebook
        self.registry = registry or Registry()

    def organize(self, experiment_id: str):
        e = self.notebook.get(experiment_id)
        superseded = {r["revises"] for r in e["records"] if r["revises"]}
        current = [r for r in e["records"] if r["id"] not in superseded]
        methods = {s: [r for r in current if r["kind"] == "methodology" and r["metadata"].get("section") == s] for s in SECTIONS}
        missing = [s for s, values in methods.items() if not any(r["provenance"] == "researcher_supplied" for r in values) and not (s == "objective" and e["objective"])]
        figures = [f for f in e["files"] if f["kind"] == "figure"]
        tables = [f for f in e["files"] if f["kind"] == "table"]
        groups = {}
        for r in current:
            if r["kind"] == "result":
                key = " / ".join(f"{k}={r['metadata'][k]}" for k in ("time", "endpoint", "group") if k in r["metadata"]) or "unspecified"
                groups.setdefault(key, []).append(r)
        return {"experiment_id": experiment_id, "methodology": methods, "missing_methodology": missing, "targeted_questions": [f"What is the {s.replace('_', ' ')} for this experiment?" for s in missing], "results": groups, "figures": figures, "tables": tables, "suggested_figure_labels": [{"file_id": f["id"], "classification": "ai_suggestion", "title": f"Figure {f['number']}: {f['filename']}", "caption": "Source: " + f["filename"] + ". Experimental interpretation and conditions require researcher input."} for f in figures if not f["title"]], "content_policy": UNTRUSTED}

    def analyze(self, experiment_id: str, file_id: str):
        f, path = self.notebook.file(experiment_id, file_id)
        if f["kind"] != "table":
            raise ValueError("Data analysis requires a table")
        return {"source_file_id": f["id"], "source_sha256": f["sha256"], **quality(read_table(f["filename"], path.read_bytes()))}

    def hints(self, experiment_id: str):
        e = self.notebook.get(experiment_id)
        organized = self.organize(experiment_id)
        findings = []
        def add(code, evidence, finding, action, uncertainty, sources, priority="medium", hypothesis="Not established by these records"):
            findings.append({"code": code, "priority": priority, "observed_evidence": evidence, "computational_finding": finding, "scientific_interpretation": "Review required; no causal or mechanistic conclusion is established", "hypothesis": hypothesis, "recommended_action": action, "uncertainty": uncertainty, "sources": {"experiment_id": experiment_id, "record_ids": sources}})
        if organized["missing_methodology"]:
            add("incomplete_methodology", "Methodological sections are absent from the notebook", organized["missing_methodology"], organized["targeted_questions"], "Missing documentation does not prove the procedure was omitted", [])
        for f in e["files"]:
            if f["kind"] == "table":
                for finding in self.analyze(experiment_id, f["id"])["findings"]:
                    add(finding["code"], {"file_id": f["id"], "sha256": f["sha256"]}, finding, "Verify against instrument output and protocol; retain originals and document any corrected derivative", "Automated screening does not establish that a measurement is incorrect", [f["id"]], finding["priority"])
        # Conflicts require an explicit shared endpoint/time/group and recorded values.
        current = [r for r in e["records"] if r["id"] not in {x["revises"] for x in e["records"]}]
        endpoints = {}
        for r in current:
            if r["kind"] in {"observation", "result"} and r["provenance"] == "researcher_supplied" and "endpoint" in r["metadata"] and "value" in r["metadata"]:
                key = tuple(str(r["metadata"].get(k, "")) for k in ("endpoint", "time", "group", "subject", "unit"))
                endpoints.setdefault(key, []).append(r)
        for key, values in endpoints.items():
            if len({str(r["metadata"]["value"]) for r in values}) > 1:
                add("potential_conflict", [r["metadata"] for r in values], "Different values recorded for the same explicit endpoint/time/group/subject/unit", "Clarify whether these are replicates, a correction, or conflicting records", "Differences may reflect legitimate replicate measurements", [r["id"] for r in values], "high")
        for f in findings:
            self.notebook.hint(experiment_id, f)
        return {"experiment_id": experiment_id, "hints": self.notebook.get(experiment_id)["hints"], "delivery": "Stored findings surface on tool interactions; no unsolicited notification"}

    def add_record(self, experiment_id: str, content: str, kind="observation", metadata=None, revises=None, provenance="researcher_supplied"):
        r = self.notebook.add_record(experiment_id, content, kind, metadata, revises, provenance)
        return {"record": r, **self.hints(experiment_id)}

    def upload(self, experiment_id: str, filename: str, data: bytes):
        f = self.notebook.store_file(experiment_id, filename, data)
        return {"file": f, **self.hints(experiment_id)}

    def run_plugin(self, experiment_id: str, file_id: str, plugin: str, options: dict):
        f, path = self.notebook.file(experiment_id, file_id)
        if f["kind"] != "table":
            raise ValueError("Plugin input must be a table")
        result = self.registry.run(plugin, read_table(f["filename"], path.read_bytes()), options)
        findings = result["findings"]
        if "image_bytes" in findings:
            data = findings.pop("image_bytes")
            derived = self.notebook.store_file(experiment_id, "concentration-time.png", data, role="derived", metadata={"source_file_id": file_id, "source_sha256": f["sha256"], "plugin": plugin, "options": options})
            findings["figure"] = derived
        result.update(source_file_id=file_id, source_sha256=f["sha256"])
        from .storage import encoded
        record = self.notebook.add_record(experiment_id, encoded(result), kind="result", metadata={"plugin": plugin, "source_file_id": file_id}, provenance="computational")
        return {"calculation_record_id": record["id"], **result, **self.hints(experiment_id)}
