# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this project is

Single-file HTML dashboard for managing hematology patients at Hospital 9 de Julho. Built with React 18 (via CDN + Babel standalone), TailwindCSS, and Recharts — no build step, no package.json.

The entire app is transpiled in-browser by Babel standalone on every load, so **any edit requires a hard reload (Cmd+Shift+R) to take effect** — a normal reload reuses the cached, already-transpiled bundle.

### Dependencies — self-hosted in `vendor/` (NOT loaded from CDNs)

All runtime scripts are vendored locally and loaded with relative `./vendor/...` paths from `<head>`: React 18 + ReactDOM, prop-types 15, Recharts 2.12.7, `@babel/standalone@7.29.7`, `heic-to@1.5.2` (IIFE build, global `HeicTo`), and the Tailwind play-CDN runtime (`tailwind.js`). The app therefore runs fully offline and does not depend on unpkg/jsdelivr/`cdn.tailwindcss.com` being up or serving the expected bytes. `heic-to` replaced `heic2any`, which failed on modern iPhone HEIC files with `ERR_LIBHEIF format not supported`.

**Why vendored (do not revert to CDNs):** the scripts used to load from unpkg/jsdelivr unversioned. When unpkg's `@babel/standalone` `latest` rolled to **Babel 8**, `@babel/preset-react` switched to the automatic JSX runtime and emitted `import { jsx } from "react/jsx-runtime"` — an `import` can't run inside a classic `<script>`, so the whole page rendered blank with `Uncaught SyntaxError: Cannot use import statement outside a module`. (Misleading symptom: the console points the error at a `<style>`/CSS line, because Babel reports the injected script's position, not the real source.) `cdn.tailwindcss.com` carried the same latent risk. Vendoring eliminates this entire failure class. **To update a dependency, re-download that single file into `vendor/`** — keep React and ReactDOM on the same major, and re-check JSX still transpiles if bumping Babel across a major.

Only the Google Fonts `<link>` remains external; it degrades gracefully to system fonts (`Inter`/`Instrument Serif`/`JetBrains Mono` → `system-ui`/`Georgia`/`monospace`) and never blanks the page.

**Blank-page guard:** a plain (non-Babel) `<script>` at the end of `<body>` checks 4s after `load` whether `#root` is still empty; if so it replaces the white screen with an on-page diagnostic (which scripts failed to load, hard-reload hint, console hint) instead of a silent blank — important because a blank page in a clinical tool could be misread as "no patients" rather than "broken."

## Running the dashboard

```bash
hema        # terminal alias — starts server and opens Chrome
```

Or manually:
```bash
cd "/Users/viniciuscamposdemolla/pCloud Drive/_/Codex/Dashboard Hemato"
python3 servidor.py
# then open http://localhost:8741/dashboard-hematologia-v2.html in Chrome
```

`servidor.py` replaces the plain `python3 -m http.server`: it still serves the static
files, **and** exposes `POST /extrair-agenda`, the endpoint the dashboard calls to OCR an
agenda screenshot. That endpoint shells out to the **Codex CLI (`codex`) on the
subscription** — the API-per-token path was removed. So the agenda-import feature now only
works with `servidor.py` running on the Mac (where the CLI is installed and logged in);
the CLI must be authenticated.

**Chrome is required.** The pCloud sync uses the File System Access API (`showDirectoryPicker`), which is not supported in Safari.

## File locations

All project files live in one folder:

```
pCloud Drive/_/Codex/Dashboard Hemato/
├── dashboard-hematologia-v2.html   ← edit here
├── servidor.py                      ← local server: static files + /extrair-agenda (Codex CLI)
├── vendor/                          ← self-hosted JS libs (react, babel, recharts, tailwind, heic-to…)
├── iniciar-dashboard.command        ← double-click to launch
├── pacientes.json                   ← auto-sync output (written by dashboard)
└── AGENTS.md
```

## Architecture

Everything lives in one `<script type="text/babel">` block inside the HTML file. Key sections (marked with `// ───` comments):

- **Storage** — `localStorage` (`hema_v3`) for primary persistence (no API key is stored anymore)
- **IndexedDB** — persists the File System Access directory handle across page reloads (`hema_fs_v1` DB, `handles` store, key `sync_dir`)
- **File System Access** — `_dirHandle` (active, permission granted) and `_pendingHandle` (stored in IDB but needs a user gesture to re-authorize). `pickFolder()` stores the handle in IDB; `restoreFolder()` tries to recover it silently on mount
- **Auto-sync** — `useEffect` on `patients` state: 2-second debounce → `saveToFolder()` → writes `pacientes.json` in the selected folder. If `_dirHandle` is null but `_pendingHandle` exists, sets `syncPending=true` and waits for a user click
- **Image import** — `ImportModal.processFiles()` → `convertToJpeg()`. HEIC/HEIF files are decoded with `HeicTo({blob, type:'image/jpeg'})` **before** being drawn to a canvas (Chrome can't decode HEIC via `<img>`); all images are then downscaled (max 2400px) and re-encoded as JPEG. The browser-side resize is what keeps the base64 payload small enough for the API
- **Codex Vision** — `extractPatientsFromImage()` POSTs the JPEG (base64) to the local `POST /extrair-agenda` endpoint in `servidor.py`, which writes it to a temp file and runs the Codex CLI (`codex -p … --allowedTools Read --model Codex-sonnet-4-6`) with `ANTHROPIC_API_KEY` stripped from the env, so the OCR runs on the **subscription**, not the per-token API. Same headless-vs-CLI pattern as `../Transcrição exames/lab_transcribe.py`. The old direct `api.anthropic.com` call and the in-browser API-key modal were removed.
- **State** — all app state in `App()`: `patients`, `fsGranted`, `syncPending`, `lastSync`, `fsSaving`, `view` (list | patient), `tab` (lista | graficos), `sort` (`{key, dir}` for the patient table), `filters` (`diagnostico`/`convenio`/`tratamento`/`terapia`/`status`, each `'todos'` by default — `terapia` matches against the `terapias` array via `includes`), `consultaPeriod` (`mes` | `semana` toggle on the consultations chart), `hiddenDx` (diagnoses hidden from the donut via its clickable legend)
- **Charts** (`charts` useMemo, derived from `filtered`) — `dx`/`conv`/`trat` tallies, `ter` (terapias-celulares count, summed across each patient's `terapias` array), plus `mes` and `semana` (consultas grouped by ISO-week Monday). The diagnoses donut colours are keyed to the full `charts.dx` index so hiding a slice doesn't reshuffle colours
- **Agenda import date** — `ImportModal` preview stage has a single `batchDate` date picker (defaults to `today()`) that overwrites `data` on every extracted row at once; per-row date inputs remain for mixed-day screenshots. `upsertFromAgenda` still falls back to `today()` for any row left without a date

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
  terapias: string[],   // subset of TERAPIAS_OPTIONS; a patient may have several. Legacy records omit it — always read as `p.terapias||[]`
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
- **Stale-handle recovery**: pCloud is a virtual drive that remounts, which can leave the stored handle pointing at a path that no longer exists. `saveToFS()` catches `NotFoundError` and, when triggered by a user click (not the silent auto-save), clears the handle and re-opens `showDirectoryPicker` so the user can re-select the folder. localStorage remains the source of truth, so a sync failure never loses data

## Valid status values (`STATUS_OPTIONS`)

```
Em tratamento · Em investigação · Primeira consulta · Seguimento
Remissão · Recidiva · Pré-TMO · Pós-TMO · Cuidados paliativos · Alta
```

Each maps to a colour pair in `SC` (background, text). Adding a new status requires an entry in `SC`.

## Cellular therapies / transplant (`TERAPIAS_OPTIONS`)

```
TCTH auto · TCTH alo · CART
```

A multi-select flag on each patient (the `terapias` array) — a patient can have more than one. Mirrors the status mechanism: each value maps to a colour pair in `TC` (background, text), exposed via `terapiaPill()`. Adding a therapy requires an entry in `TC`. Shown as pills on the patient detail/list, charted in `charts.ter`, filterable, and exported in the CSV (joined by `; `).

## Git workflow

Repository: **https://github.com/vcm-sudo/dashboard-hematologia**

The `hema` alias is defined in `~/.zshrc`. On a new machine, add it manually:
```bash
echo 'alias hema='"'"'open "/Users/viniciuscamposdemolla/pCloud Drive/_/Codex/Dashboard Hemato/iniciar-dashboard.command"'"'"'' >> ~/.zshrc
```

After editing the HTML, commit and push:
```bash
git add dashboard-hematologia-v2.html
git commit -m "descrição da mudança"
git push
```

**Never stage `pacientes.json`.** It is the auto-sync output and contains real patient data (PHI). The HTML, `vendor/`, and `AGENTS.md` are the tracked source. `.DS_Store` and `pacientes.json` were already committed in earlier history; if the repo is public this is a privacy exposure worth flagging.

## Restoring data between browsers/machines

Use the **Restaurar** button in the header to load a `pacientes.json` or any exported `.json` file. This replaces the current localStorage contents.
