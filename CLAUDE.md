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
cd "/Users/viniciuscamposdemolla/pCloud Drive/_/Claude/Pacientes"
python3 -m http.server 8741
# then open http://localhost:8741/dashboard-hematologia-v2.html in Chrome
```

**Chrome is required.** The pCloud sync uses the File System Access API (`showDirectoryPicker`), which is not supported in Safari.

## File locations

| File | Purpose |
|------|---------|
| `Downloads/ClaudeCode/dashboard-hematologia-v2.html` | Working copy (edit here) |
| `pCloud Drive/_/Claude/Pacientes/dashboard-hematologia-v2.html` | Served copy (must be kept in sync) |
| `pCloud Drive/_/Claude/Pacientes/iniciar-dashboard.command` | Launch script |
| `pCloud Drive/_/Claude/Pacientes/pacientes.json` | Auto-sync file written by the dashboard |

After editing the HTML, copy it to pCloud:
```bash
cp ~/Downloads/ClaudeCode/dashboard-hematologia-v2.html "/Users/viniciuscamposdemolla/pCloud Drive/_/Claude/Pacientes/"
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

## Restoring data between browsers/machines

Use the **Restaurar** button in the header to load a `pacientes.json` or any exported `.json` file. This replaces the current localStorage contents.
