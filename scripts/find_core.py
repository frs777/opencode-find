#!/usr/bin/env python3
"""Core discovery/indexing logic for the find plugin. Standard library only."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


# Domyślne źródła skilli OpenCode (globalne + compatibility).
DEFAULT_ROOTS = [
    Path("~/.agents/skills"),
    Path("~/.config/opencode/skills"),
    Path("~/.claude/skills"),
]


def parse_skill_frontmatter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    front = text[3:end].strip("\n")
    lines = front.splitlines()
    name = None
    description = None
    collecting = False
    desc_lines: list[str] = []
    for line in lines:
        if collecting:
            if line.startswith((" ", "\t")):
                desc_lines.append(line.strip())
                continue
            collecting = False
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
        elif line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if value in (">-", ">", "|-", "|"):
                collecting = True
                desc_lines = []
            else:
                description = value.strip("'\"")
    if collecting:
        description = " ".join(x for x in desc_lines if x).strip()
    if not name:
        return None
    return {"name": name, "description": description or ""}


def _tokens(text: str) -> set[str]:
    return {
        t.lower() for t in re.findall(r"[\wąćęłńóśźż]+", text.lower()) if len(t) > 1
    }


_STOP = {
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
    "się",
    "oraz",
    "lub",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "use",
    "when",
    "this",
    "that",
}


def _stem(t: str) -> str:
    # proste rdzenie: 5 pierwszych znaków (polskie/angielskie odmiany)
    return t[:5] if len(t) >= 5 else t


def match_capabilities(
    query: str, items: Iterable[dict[str, str]], limit: int = 10
) -> list[dict[str, str]]:
    query_tokens = {t for t in _tokens(query) if t not in _STOP}
    if not query_tokens:
        query_tokens = _tokens(query)
    scored = []
    for item in items:
        name = item.get("name", "")
        haystack = f"{name} {item.get('description', '')}"
        tokens = {t for t in _tokens(haystack) if t not in _STOP}
        name_tokens = {t for t in _tokens(name) if t not in _STOP}
        overlap = query_tokens & tokens
        # dopasowanie rdzeniowe (polskie odmiany: python/pythonie, programowanie/programowaniu)
        related = 0
        for q in query_tokens - overlap:
            qstem = _stem(q)
            if any(_stem(t) == qstem for t in tokens):
                related += 2
            elif any(
                (len(q) >= 3 and (q.startswith(t[:4]) or t.startswith(q[:4])))
                for t in tokens
            ):
                related += 1
            elif any((len(q) >= 4 and (q in t or t in q)) for t in tokens):
                related += 1
        score = len(overlap) * 2 + related
        if query_tokens & name_tokens:
            score += 4
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].get("name", "").lower()))
    return [item for _, item in scored[:limit]]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_roots(root) -> list[Path]:
    if isinstance(root, (list, tuple)):
        roots = [Path(r).expanduser() for r in root]
    else:
        roots = [Path(root).expanduser()]
    out = []
    for r in roots:
        try:
            out.append(r.resolve())
        except OSError:
            continue
    return out


def build_index(root, db_path: Path, max_depth: int = 6) -> dict:
    roots = _normalize_roots(root)
    db_path = Path(db_path).expanduser().resolve()
    old = (
        json.loads(db_path.read_text(encoding="utf-8"))
        if db_path.exists()
        else {"skills": {}}
    )
    old_skills = old.get("skills", {})
    current: dict[str, dict] = {}
    added = changed = unchanged = invalid = 0
    invalid_files: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            try:
                if len(path.relative_to(root).parts) > max_depth:
                    continue
                stat = path.stat()
                rel = f"{root.name}/{path.relative_to(root)}"
                digest = _sha256(path)
                parsed = parse_skill_frontmatter(path)
                if not parsed:
                    invalid += 1
                    invalid_files.append(str(path))
                    continue
                current[rel] = {
                    **parsed,
                    "path": str(path),
                    "root": str(root),
                    "sha256": digest,
                    "mtime_ns": stat.st_mtime_ns,
                }
                if rel not in old_skills:
                    added += 1
                elif old_skills[rel].get("sha256") == digest:
                    unchanged += 1
                else:
                    changed += 1
            except OSError:
                invalid += 1
                invalid_files.append(str(path))
    removed = len(set(old_skills) - set(current))
    payload = {"version": 1, "roots": [str(r) for r in roots], "skills": current}
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "added": added,
        "changed": changed,
        "unchanged": unchanged,
        "removed": removed,
        "invalid": invalid,
        "invalid_files": invalid_files,
    }


def help_text() -> str:
    return """# find — pomoc

@find <zadanie> — analizuje zadanie i dobiera pasujące skille/wtyczki.
@find help — pokazuje dostępne funkcje find.
@find lista <temat> — listuje zainstalowane możliwości związane z tematem.
@find szukaj <temat> — wyszukuje możliwości bez wykonywania zadania.
@find użyj <nazwa> — wskazuje konkretny skill/wtyczkę do użycia.
@find status — pokazuje stan lokalnego indeksu.
@find rescan — wykonuje pełny skan i aktualizuje indeks zmian.
"""
