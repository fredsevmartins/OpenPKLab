"""Local-owner CLI: initialize, run, upload or export a notebook."""
import argparse
import json
import os
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="openpklab")
    parser.add_argument("--data-dir", default=os.getenv("OPENPKLAB_DATA_DIR", ".data"))
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("serve", help="Run MCP over stdio or authenticated HTTP")
    run.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8000)
    create = sub.add_parser("create", help="Create an experiment as the local filesystem owner")
    create.add_argument("title")
    create.add_argument("--category", default="pharmacokinetic")
    create.add_argument("--id")
    upload = sub.add_parser("upload", help="Attach a local file; run on the notebook machine")
    upload.add_argument("experiment_id")
    upload.add_argument("file", type=Path)
    exp = sub.add_parser("export", help="Export ZIP as the local filesystem owner")
    exp.add_argument("experiment_id")
    exp.add_argument("destination", type=Path)
    args = parser.parse_args()
    from .server import create_app, create_server
    if args.command == "serve":
        if args.transport == "stdio":
            mcp, _, _ = create_server(args.data_dir)
            mcp.run(transport="stdio")
        else:
            import uvicorn
            uvicorn.run(create_app(args.data_dir), host=args.host, port=args.port, access_log=False)
        return
    from .service import Lab
    from .storage import MAX_UPLOAD, Notebook
    lab = Lab(Notebook(args.data_dir))
    if args.command == "create":
        result = lab.notebook.create(args.title, args.category, experiment_id=args.id)
    elif args.command == "upload":
        if args.file.stat().st_size > MAX_UPLOAD:
            parser.error("Upload exceeds 10 MiB")
        result = lab.upload(args.experiment_id, args.file.name, args.file.read_bytes())
    else:
        from .reports import export, export_file
        if args.destination.exists():
            parser.error("Destination exists; choose a new filename")
        result = export(lab, args.experiment_id)
        # Exclusive creation protects an existing local export.
        with args.destination.open("xb") as dest, export_file(lab.notebook, args.experiment_id, result["id"]).open("rb") as source:
            shutil.copyfileobj(source, dest)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
