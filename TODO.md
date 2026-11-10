# TODO — opencode-find

## Pomysły na rozwój

### Opcja B — pełna wtyczka z real-time + cache
- [ ] Indeksowanie nie tylko skilli (SKILL.md), ale też:
  - wtyczki z `~/.config/opencode/plugins/` (index.mjs + package.json)
  - komendy z `~/.config/opencode/commands/*.md`
  - serwery MCP z `~/.config/opencode/opencode.json` (`mcp.servers`)
  - agenty z `~/.config/opencode/agents/` (jeśli istnieją)
- [ ] Cache na dysku z TTL (zamiast rebuild przy każdym wywołaniu)
- [ ] Deduplikacja po ID z rozwiązywaniem precedencji (projekt > global > compat)
- [ ] Narzędzie `find.use` wskazujące konkretny komponent (zamiast tylko search)
- [ ] Integracja z OpenCode `skill` tool (auto-load wybranego skillu)
- [ ] Testy E2E dla pluginów i MCP (obecne testy pokrywają tylko find_core)

### Drobne
- [ ] Lematyzacja/stemming dla polskich odmian (obecnie prefix 5 znaków)
- [ ] Fuzzy matching (literówki)
- [ ] Raport o przestarzałym indeksie w `status`
- [ ] Obsługa projektowych źródeł (`.opencode/skills`, `.agents/skills` w cwd)

## Zrobione (0.2.0)
- [x] Real-time discovery (tymczasowy indeks w pamięci)
- [x] Multi-source: 3 katalogi skilli + pluginy + komendy + MCP
- [x] Deduplikacja po ID (name)
- [ ] ~~Indeksowanie pluginów/MCP w głębi~~ → przeniesione do Opcji B
- [x] Komenda `/find` w OpenCode
- [x] 4 narzędzia: search, status, list (oraz use w CLI)
- [x] Testy E2E (search, status, list, CLI)