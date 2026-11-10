#!/usr/bin/env python3
"""CLI for the local find capability index."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from find_core import build_index, help_text, match_capabilities, DEFAULT_ROOTS


def load_items(db: Path):
    if not db.exists():
        return []
    return list(json.loads(db.read_text(encoding="utf-8")).get("skills", {}).values())


def main() -> int:
    p = argparse.ArgumentParser(
        prog="find", description="Local capability discovery index"
    )
    p.add_argument("--index", default="~/.cache/find/index.json")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("help")
    for name in ("lista", "szukaj"):
        cmd = sub.add_parser(name)
        cmd.add_argument("query", nargs="+")
    use = sub.add_parser("użyj")
    use.add_argument("name")
    sub.add_parser("status")
    scan = sub.add_parser("rescan")
    scan.add_argument(
        "--root",
        nargs="*",
        default=None,
        help="Katalogi źródłowe (domyślnie: wszystkie źródła OpenCode)",
    )
    args = p.parse_args()
    db = Path(args.index).expanduser()
    if args.command in (None, "help"):
        print(help_text())
        return 0
    if args.command == "rescan":
        roots = args.root if args.root else [str(r) for r in DEFAULT_ROOTS]
        result = build_index(roots, db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("invalid_files"):
            print("\n# Pominięte (brak name w frontmatter):")
            for f in result["invalid_files"]:
                print(f"  - {f}")
        return 0
    items = load_items(db)
    if args.command in ("lista", "szukaj"):
        query = " ".join(args.query)
        print(
            json.dumps(match_capabilities(query, items), ensure_ascii=False, indent=2)
        )
        return 0
    if args.command == "użyj":
        needle = args.name.lower()
        found = [
            x
            for x in items
            if x.get("name", "").lower() == needle
            or needle in x.get("name", "").lower()
            or needle in x.get("path", "").lower()
        ]
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return 0
    if args.command == "status":
        info = {"index": str(db), "count": len(items)}
        if db.exists():
            import os

            info["mtime"] = os.path.getmtime(db)
            data = json.loads(db.read_text(encoding="utf-8"))
            info["roots"] = data.get("roots", data.get("root"))
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
PY
