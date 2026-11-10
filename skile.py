#!/usr/bin/env python3
"""Discovery wszystkich możliwości OpenCode: skille, wtyczki, komendy, MCP.

Działa w trybie real-time: buduje tymczasowy indeks w pamięci (bez zapisu na dysk)
i zwraca dopasowania. Obsługuje też tryb listy Markdown (jak oryginalny skile.py).
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_SKILL_ROOTS = [
    "~/.claude/skills",
    "~/.agents/skills",
    "~/.config/opencode/skills",
]
DEFAULT_PLUGIN_DIRS = [
    "~/.config/opencode/plugins",
]
DEFAULT_COMMAND_DIRS = [
    "~/.config/opencode/commands",
]
DEFAULT_CONFIGS = [
    "~/.config/opencode/opencode.json",
]

STOP = {
    "w",
    "i",
    "a",
    "o",
    "u",
    "z",
    "do",
    "na",
    "za",
    "od",
    "po",
    "przez",
    "dla",
    "jak",
    "co",
    "to",
    "jest",
    "czy",
    "nie",
    "sie",
    "oraz",
    "lub",
    "the",
    "an",
    "and",
    "or",
    "of",
    "in",
    "on",
    "for",
    "with",
    "use",
    "when",
    "this",
    "that",
    "are",
    "is",
}


def _tokens(text: str) -> set[str]:
    return {
        t.lower() for t in re.findall(r"[\wąćęłńóśźż]+", text.lower()) if len(t) > 1
    }


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    front = text[3:end].strip("\n")
    # prosty parser YAML (bez zależności od PyYAML)
    data = {}
    collecting = None
    buf = []
    for line in front.splitlines():
        if collecting:
            if line.startswith((" ", "\t")):
                buf.append(line.strip())
                continue
            data[collecting] = " ".join(x for x in buf if x).strip()
            collecting = None
            buf = []
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if v in (">-", ">", "|-", "|"):
                collecting = k
                buf = []
            else:
                data[k] = v.strip("'\"")
    if collecting:
        data[collecting] = " ".join(x for x in buf if x).strip()
    return data if data else None


def scan_skills(roots):
    out = []
    for root in roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for p in sorted(root.rglob("SKILL.md")):
            try:
                if len(p.relative_to(root).parts) > 6:
                    continue
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            if not fm or not fm.get("name"):
                continue
            out.append(
                {
                    "type": "skill",
                    "name": str(fm["name"]).strip(),
                    "description": str(fm.get("description", "")).strip(),
                    "path": str(p),
                }
            )
    return out


def scan_plugins(dirs):
    out = []
    for d in dirs:
        d = Path(d).expanduser()
        if not d.exists():
            continue
        for entry in sorted(d.iterdir()):
            if not entry.is_dir():
                continue
            idx = entry / "index.mjs"
            if not idx.exists():
                idx = entry / "index.js"
            if not idx.exists():
                continue
            name = entry.name
            desc = ""
            try:
                head = idx.read_text(encoding="utf-8")[:800]
                m = re.search(r'description:\s*["\'](.+?)["\']', head, re.S)
                if m:
                    desc = m.group(1).replace("\n", " ").strip()
                m = re.search(r'name:\s*["\'](.+?)["\']', head)
                if m:
                    name = m.group(1).strip()
                # fallback: pierwszy komentarz // ...
                if not desc:
                    m = re.search(r"//\s*(.+)", head)
                    if m:
                        desc = m.group(1).strip()
            except OSError:
                pass
            out.append(
                {
                    "type": "plugin",
                    "name": name,
                    "description": desc,
                    "path": str(idx),
                }
            )
    return out


def scan_commands(dirs):
    out = []
    for d in dirs:
        d = Path(d).expanduser()
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            name = p.stem
            desc = ""
            if fm:
                name = str(fm.get("name", name)).strip()
                desc = str(fm.get("description", "")).strip()
            out.append(
                {
                    "type": "command",
                    "name": name,
                    "description": desc,
                    "path": str(p),
                }
            )
    return out


def scan_mcp(configs):
    out = []
    for c in configs:
        c = Path(c).expanduser()
        if not c.exists():
            continue
        try:
            data = json.loads(c.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        servers = data.get("mcp", {}).get("servers", {})
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            desc = cfg.get("description", "")
            typ = cfg.get("type", "local")
            url = cfg.get("url", "")
            cmd = cfg.get("command", [])
            cmd = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if not desc:
                desc = f"{typ}: {url or cmd}".strip()
            out.append(
                {
                    "type": "mcp",
                    "name": name,
                    "description": desc,
                    "path": str(c),
                    "disabled": bool(cfg.get("disabled", False)),
                }
            )
    return out


def build_temp_index(
    skill_roots=None, plugin_dirs=None, command_dirs=None, configs=None
):
    """Buduje tymczasowy indeks w pamięci (bez zapisu na dysk)."""
    skill_roots = skill_roots or DEFAULT_SKILL_ROOTS
    plugin_dirs = plugin_dirs or DEFAULT_PLUGIN_DIRS
    command_dirs = command_dirs or DEFAULT_COMMAND_DIRS
    configs = configs or DEFAULT_CONFIGS
    items = []
    items.extend(scan_skills(skill_roots))
    items.extend(scan_plugins(plugin_dirs))
    items.extend(scan_commands(command_dirs))
    items.extend(scan_mcp(configs))
    # deduplikacja po name (ID): późniejsze źródło (wyższa precedencja) wygrywa
    seen = {}
    for it in items:
        key = it.get("name")
        seen[key] = it
    return list(seen.values())


def _stem(t: str) -> str:
    return t[:5] if len(t) >= 5 else t


def match(items, query, limit=10):
    qtokens = {t for t in _tokens(query) if t not in STOP}
    if not qtokens:
        qtokens = _tokens(query)
    scored = []
    for it in items:
        name = it.get("name", "")
        haystack = f"{name} {it.get('description', '')}"
        tokens = {t for t in _tokens(haystack) if t not in STOP}
        name_tokens = {t for t in _tokens(name) if t not in STOP}
        overlap = qtokens & tokens
        related = 0
        for q in qtokens - overlap:
            qstem = _stem(q)
            if any(_stem(t) == qstem for t in tokens):
                related += 2
            elif any(
                len(q) >= 3 and (q.startswith(t[:4]) or t.startswith(q[:4]))
                for t in tokens
            ):
                related += 1
            elif any(len(q) >= 4 and (q in t or t in q) for t in tokens):
                related += 1
        score = len(overlap) * 2 + related
        if qtokens & name_tokens:
            score += 4
        if score:
            scored.append((score, it))
    scored.sort(key=lambda x: (-x[0], x[1].get("name", "").lower()))
    return [it for _, it in scored[:limit]]


def main():
    parser = argparse.ArgumentParser(
        prog="skile", description="Discovery skilli/wtyczek/komend/MCP (real-time)"
    )
    parser.add_argument(
        "--query", "-q", help="Zapytanie (real-time, tymczasowy indeks, bez zapisu)"
    )
    parser.add_argument("--status", action="store_true", help="Tylko podsumowanie indeksu (JSON)")
    parser.add_argument("--limit", type=int, default=10, help="Maks. wyników")
    parser.add_argument("--skill-roots", nargs="*", default=None)
    parser.add_argument("--plugin-dirs", nargs="*", default=None)
    parser.add_argument("--command-dirs", nargs="*", default=None)
    parser.add_argument("--configs", nargs="*", default=None)
    parser.add_argument(
        "--output", "-o", default=None, help="Plik wyjściowy Markdown (lista)"
    )
    parser.add_argument("--json", action="store_true", help="Wyjście JSON")
    args = parser.parse_args()

    roots = args.skill_roots or DEFAULT_SKILL_ROOTS
    pdirs = args.plugin_dirs or DEFAULT_PLUGIN_DIRS
    cdirs = args.command_dirs or DEFAULT_COMMAND_DIRS
    cfgs = args.configs or DEFAULT_CONFIGS

    items = build_temp_index(roots, pdirs, cdirs, cfgs)

    if args.status:
        from collections import Counter
        c = Counter(it["type"] for it in items)
        print(json.dumps({"count": len(items), "types": dict(c), "roots": roots,
                          "plugin_dirs": pdirs, "command_dirs": cdirs, "configs": cfgs},
                        ensure_ascii=False, indent=2))
        return 0

    if args.query:
        res = match(items, args.query, args.limit)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"# Wyniki dla: {args.query}\n")
            for it in res:
                print(f"- **{it['name']}** ({it['type']})")
                if it.get("description"):
                    print(f"  {it['description'][:120]}")
                print(f"  `{it['path']}`")
        return 0

    if args.output:
        # tryb listy Markdown (jak oryginalny skile.py) — tylko skille
        skille = [it for it in items if it["type"] == "skill"]
        skille.sort(key=lambda s: s["name"].lower())
        linie = ["# Lista skilli\n"]
        for s in skille:
            linie.append(f"# `{s['name']}`\n")
            linie.append(f"{s['description']}\n")
        Path(args.output).expanduser().write_text("\n".join(linie), encoding="utf-8")
        print(f"Zapisano {len(skille)} skilli do '{args.output}'")
        return 0

    # domyślnie: podsumowanie
    from collections import Counter

    c = Counter(it["type"] for it in items)
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(f"Zindeksowano {len(items)} komponentów: {dict(c)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
