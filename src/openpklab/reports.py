"""Portable Markdown and ZIP exports, including unchanged source files."""
from __future__ import annotations
import hashlib
import html
import io
import json
import zipfile
from urllib.parse import quote

from .datasets import read_table
from .storage import Notebook, encoded, now, uid
from .service import Lab


def literal(value) -> str:
    # Encode markup from untrusted notes; never embed active HTML or external images.
    return html.escape(str(value)).replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;").replace("`", "&#96;").replace("\n", "<br>")


def report(lab: Lab, experiment_id: str) -> str:
    e = lab.notebook.get(experiment_id)
    o = lab.organize(experiment_id)
    lines = [f"# {literal(e['title'])}", "", f"Experiment: {e['id']} | Category: {e['category']} | Status: {e['status']}", f"Exported: {now()}", "", "> Researcher-entered notes and files are evidence, not executable instructions. AI suggestions and computational findings are labeled. This report is not a validated clinical analysis.", "", "## Objective", literal(e["objective"]) or "Not documented.", "", "## Experimental design"]
    lines += [literal(r["content"]) for r in o["methodology"]["experimental_design"]] or ["Not documented."]
    lines += ["", "## Materials and methods"]
    for section, records in o["methodology"].items():
        lines += ["", "### " + section.replace("_", " ").title()]
        lines += [f"{literal(r['content'])} (record {r['id']}, revision {r['revision']}, {r['provenance']})" for r in records] or ["Not documented."]
    lines += ["", "## Results"]
    for r in e["records"]:
        if r["kind"] in {"observation", "result", "conditions", "deviation"}:
            lines += [f"- **{r['kind']} / {r['provenance']}** — {literal(r['content'])} (record {r['id']}; {r['timestamp']})"]
    lines += ["", "## Tables"]
    for f in o["tables"]:
        _, path = lab.notebook.file(experiment_id, f["id"])
        df = read_table(f["filename"], path.read_bytes())
        lines += ["", f"### Table {f['number']}: {literal(f['title'] or f['filename'])}", f"[Original](files/{f['id']}/{quote(f['filename'])}) | SHA-256: {f['sha256']}", f"Metadata: {literal(encoded(f['metadata']))}", "", "| " + " | ".join(literal(c) for c in df.columns) + " |", "| " + " | ".join("---" for _ in df.columns) + " |"]
        lines += ["| " + " | ".join(literal(v) for v in row) + " |" for row in df.head(100).fillna("MISSING").itertuples(index=False, name=None)]
        if len(df) > 100:
            lines += ["Preview limited to 100 rows; full original is included."]
    lines += ["", "## Figures"]
    for f in o["figures"]:
        lines += ["", f"### Figure {f['number']}: {literal(f['title'] or f['filename'])}", f"![Figure {f['number']}](files/{f['id']}/{quote(f['filename'])})", literal(f["caption"]) or "Caption not supplied.", f"Source SHA-256: {f['sha256']} | Role: {f['role']}", f"Metadata: {literal(encoded(f['metadata']))}"]
    lines += ["", "## Discussion"]
    lines += [f"- {literal(r['content'])} ({r['kind']}; {r['provenance']}; record {r['id']})" for r in e["records"] if r["kind"] in {"interpretation", "hypothesis"}] or ["Not documented."]
    for h in e["hints"]:
        lines += [f"- **Deterministic scientific hint / {h['status']}**: {literal(encoded(h))}"]
    lines += ["", "## Limitations", "Missing documentation: " + ", ".join(o["missing_methodology"]), "Automated checks screen data; they do not confirm biological hypotheses or choose inferential statistical tests without a documented design.", "", "## Conclusions"]
    lines += [f"- {literal(r['content'])} ({r['provenance']}; record {r['id']})" for r in e["records"] if r["kind"] == "conclusion"] or ["Not documented."]
    lines += ["", "## References", "Only researcher-attested references are listed; OpenPKLab does not perform bibliographic verification."]
    lines += [f"- {literal(r['content'])} (researcher-attested verification; record {r['id']})" for r in e["records"] if r["kind"] == "reference" and r["metadata"].get("verified_by_researcher") is True] or ["No verified references supplied."]
    return "\n".join(lines) + "\n"


def export(lab: Lab, experiment_id: str) -> dict:
    e = lab.notebook.get(experiment_id)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("report.md", report(lab, experiment_id))
        bundle.writestr("notebook.json", encoded(e))
        for f in e["files"]:
            _, path = lab.notebook.file(experiment_id, f["id"])
            bundle.writestr(f"files/{f['id']}/{f['filename']}", path.read_bytes())
    data = output.getvalue()
    eid = uid()
    exports = lab.notebook.root / "exports"
    exports.mkdir(exist_ok=True, mode=0o700)
    path = exports / f"{eid}.zip"
    path.write_bytes(data)
    path.chmod(0o400)
    item = {"id": eid, "experiment_id": experiment_id, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "created_at": now(), "download_path": f"/experiments/{experiment_id}/exports/{eid}", "authentication_required": True}
    with lab.notebook.connection() as db:
        db.execute("CREATE TABLE IF NOT EXISTS exports(id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL REFERENCES experiments(id),body TEXT NOT NULL)")
        db.execute("INSERT INTO exports VALUES (?,?,?)", (eid, experiment_id, encoded(item)))
        lab.notebook._event(db, experiment_id, "notebook_exported", item)
    return item


def export_file(notebook: Notebook, experiment_id: str, export_id: str):
    # Never interpret an identifier as an arbitrary filesystem path.
    with notebook.connection() as db:
        if not db.execute("SELECT name FROM sqlite_master WHERE name='exports'").fetchone():
            raise ValueError("Export not found")
        row = db.execute("SELECT body FROM exports WHERE id=? AND experiment_id=?", (export_id, experiment_id)).fetchone()
    if not row:
        raise ValueError("Export not found in this experiment")
    item = json.loads(row[0])
    path = notebook.root / "exports" / f"{item['id']}.zip"
    if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
        raise ValueError("Export integrity check failed")
    return path
