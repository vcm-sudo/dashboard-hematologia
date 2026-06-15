# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Single-file HTML dashboard for managing hematology patients at Hospital 9 de Julho. Built with React 18 (via CDN + Babel standalone), TailwindCSS, and Recharts — no build step, no package.json.

## Running the dashboard

```bash
hema        # terminal alias — starts server and opens Chrome
```

Or manually:
```bash
cd "/Users/viniciuscamposdemolla/pCloud Drive/_/Claude/Dashboard Hemato"
python3 -m http.server 8741
# then open http://localhost:8741/dashboard-hematologia-v2.html in Chrome
```

**Chrome is required.** The pCloud sync uses the File System Access API (`showDirectoryPicker`), which is not supported in Safari.

## File locations

All project files live in one folder:

```
pCloud Drive/_/Claude/Dashboard Hemato/
├── dashboard-hematologia-v2.html   ← edit here
├── iniciar-dashboard.command        ← double-click to launch
├── pacientes.json                   ← auto-sync output (written by dashboard)
└── CLAUDE.md
```

## Architecture

Everything lives in one `<script type="text/babel">` block inside the HTML file. Key sections (marked with `// ───` comments):

- **Storage** — `localStorage` (`hema_v3`) for primary persistence; `loadKey`/`saveKey` for the Claude API key
- **IndexedDB** — persists the File System Access directory handle across page reloads (`hema_fs_v1` DB, `handles` store, key `sync_dir`)
- **File System Access** — `_dirHandle` (active, permission granted) and `_pendingHandle` (stored in IDB but needs a user gesture to re-authorize). `pickFolder()` stores the handle in IDB; `restoreFolder()` tries to recover it silently on mount
- **Auto-sync** — `useEffect` on `patients` state: 2-second debounce → `saveToFolder()` → writes `pacientes.json` in the selected folder. If `_dirHandle` is null but `_pendingHandle` exists, sets `syncPending=true` and waits for a user click
- **Claude Vision** — `extractPatientsFromImage()` calls `api.anthropic.com/v1/messages` directly from the browser (requires `anthropic-dangerous-direct-browser-access: true` header) using `claude-sonnet-4-6`
- **State** — all app state in `App()`: `patients`, `fsGranted`, `syncPending`, `lastSync`, `fsSaving`, `view` (list | patient), `tab` (lista | graficos)

## Patient data shape

```js
{
  id: string,           // uid()
  nome: string,
  prontuario: string,
  idade: number | null,
  diagnostico: string,
  convenio: string,
  tratamento: string,
  status: string,       // one of STATUS_OPTIONS keys
  consultas: [{
    id, data, hora, atendimento, diagnostico, tratamento, obs
  }],
  ultimaConsulta: string, // ISO date, derived from consultas
  createdAt: string
}
```

## Sync behaviour

- First use: user clicks the **pCloud Drive** button → `showDirectoryPicker` → handle stored in IDB → `fsGranted = true`
- Subsequent page loads: `restoreFolder()` reads IDB handle and calls `queryPermission`. If `granted` → auto-save works silently. If `prompt` → button turns yellow ("Clique p/ sincronizar") until user clicks
- Save target: always `pacientes.json` (overwritten, not dated backups)

## Valid status values (`STATUS_OPTIONS`)

```
Em tratamento · Em investigação · Primeira consulta · Seguimento
Remissão · Recidiva · Pré-TMO · Pós-TMO · Cuidados paliativos · Alta
```

Each maps to a colour pair in `SC` (background, text). Adding a new status requires an entry in `SC`.

## Git workflow

Repository: **https://github.com/vcm-sudo/dashboard-hematologia**

The `hema` alias is defined in `~/.zshrc`. On a new machine, add it manually:
```bash
echo 'alias hema='"'"'open "/Users/viniciuscamposdemolla/pCloud Drive/_/Claude/Dashboard Hemato/iniciar-dashboard.command"'"'"'' >> ~/.zshrc
```

After editing the HTML, commit and push:
```bash
git add dashboard-hematologia-v2.html
git commit -m "descrição da mudança"
git push
```

## Restoring data between browsers/machines

Use the **Restaurar** button in the header to load a `pacientes.json` or any exported `.json` file. This replaces the current localStorage contents.
