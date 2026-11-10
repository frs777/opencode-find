# find — OpenCode V2 plugin

Meta-plugin do wyszukiwania i dobierania zainstalowanych skilli, wtyczek, komend i MCP na podstawie naturalnego opisu zadania.

## Instalacja

Skopiuj katalog `opencode-find` do `~/.config/opencode/plugins/` (lub użyj `opencode plugin add`).

## Użycie

- Narzędzia: `find.search`, `find.status`, `find.list`
- Komenda: `/find <zapytanie>`
- Skill: `find` (ładowany automatycznie)

## Wymagania

- Python 3 (skrypt `scripts/skile.py`)
- OpenCode V2

## Źródła

Skile: `~/.agents/skills`, `~/.config/opencode/skills`, `~/.claude/skills`
Wtyczki: `~/.config/opencode/plugins`
Komendy: `~/.config/opencode/commands`
MCP: `~/.config/opencode/opencode.json`

## Licencja

MIT
