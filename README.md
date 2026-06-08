# OPSWAT Rebrand API

Reusable API for applying OPSWAT product design treatment to internal tools and web codebases.

This project is app-agnostic. It is not tied to Flow Architect or any single demo. Flow Architect is only a useful test case because it is a real web app that needs an OPSWAT redesign. The intended workflow is:

1. Build an internal tool or proof of concept.
2. Zip the codebase.
3. Send the ZIP to this API.
4. Receive an OPSWAT-branded version, a machine-readable report, and a restyle work order for anything that needs deeper design attention.

V1 is focused on web codebases. Later phases will add reusable document rebranding routes for DOCX, PDF, PPTX, and other sales/SE collateral.

## What It Does Today

The API accepts a zipped web codebase and runs a deterministic OPSWAT rebrand pass.

Current output:

- rebranded ZIP artifact,
- `REBRAND_REPORT.json`,
- `RESTYLE_WORKORDER.md` in `full` mode,
- swapped OPSWAT logo assets where matching app logo files are found,
- OPSWAT product UI baseline CSS,
- source-theme detection and target-theme selection.

Current target:

- static HTML/CSS apps,
- simple JavaScript apps,
- lightweight internal dashboards,
- proof-of-concept UIs,
- apps with conventional CSS files and local assets.

Suitable examples:

- use-case generator,
- partner account-mapping tool,
- diagram helper UI,
- internal dashboard,
- sales/SE utility,
- prototype that needs to look like an OPSWAT product.

## What It Does Not Do

This API is only for design/codebase transformation.

It does not:

- generate account maps,
- generate diagrams,
- retrieve customer stories,
- perform product-fit reasoning,
- export account-map decks,
- run or build uploaded applications,
- execute arbitrary uploaded code.

Those capabilities live in separate APIs so each component stays reusable and cleanly bounded.

## Included OPSWAT Assets

This repository includes the brand assets required by the rebrand engine under:

```text
opswat-brand/
```

Included asset groups:

- OPSWAT logos in SVG/PNG variants,
- OPSWAT logo marks and wordmarks,
- OPSWAT Simplon Norm font files,
- OPSWAT product and generic 3D icons,
- OPSWAT line-art icons,
- design token files,
- document template references for future roadmap work.

The API sets `OPSWAT_BRAND_DIR` to this local `opswat-brand` folder by default, so a fresh clone has the assets it needs.

## API Boundary

Current route:

```text
/api/rebrands
```

This route accepts codebase ZIPs only.

Planned future route shape:

```text
/api/rebrands/codebases
/api/rebrands/documents
/api/rebrands/pdfs
/api/rebrands/presentations
```

The current `/api/rebrands` route can remain as the codebase default, while the more explicit route names can be introduced when document/PDF/PPTX support is added.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Run locally:

```bash
.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8060 --reload
```

Open the API docs:

```text
http://127.0.0.1:8060/docs
```

## Environment

`.env.example`:

```text
REBRAND_JOBS_DIR=outputs/jobs
MAX_UPLOAD_MB=75
JOB_WORKERS=2
JOB_RETENTION_SECONDS=86400
OPSWAT_BRAND_DIR=opswat-brand
```

Notes:

- `REBRAND_JOBS_DIR` stores uploads, extracted source, output folders, reports, and ZIP artifacts.
- `MAX_UPLOAD_MB` protects the API from oversized uploads.
- `JOB_WORKERS` controls concurrent background rebrand jobs.
- `JOB_RETENTION_SECONDS` controls how long completed/failed jobs remain in memory before pruning.
- `OPSWAT_BRAND_DIR` can point to a centrally managed brand asset folder in production.

## Endpoints

- `GET /`
- `GET /api/health`
- `POST /api/rebrands`
- `GET /api/rebrands`
- `GET /api/rebrands/{job_id}`
- `GET /api/rebrands/{job_id}/report`
- `GET /api/rebrands/{job_id}/workorder`
- `GET /api/rebrands/{job_id}/download`

## Create A Rebrand Job

```bash
curl -s -X POST http://127.0.0.1:8060/api/rebrands \
  -F "file=@my-app.zip" \
  -F "depth=full" \
  -F "design_mode=product_ui" \
  -F "target_theme=auto"
```

Response:

```json
{
  "id": "my-app-20260608T120000Z-abcd1234",
  "status": "queued",
  "message": "Queued",
  "depth": "full",
  "design_mode": "product_ui",
  "target_theme": "auto"
}
```

## Options

Depth options:

- `tokens` - color/font token rewrite only.
- `theme` - token rewrite plus OPSWAT baseline CSS and logo swap.
- `full` - theme plus `RESTYLE_WORKORDER.md` for agentic component restyle and visual QA.

Target theme options:

- `auto` - preserve the detected source polarity; dark apps stay dark, light apps stay light.
- `dark` - force OPSWAT dark product styling.
- `light` - force OPSWAT light product styling.

Design mode options:

- `product_ui` - OPSWAT product UI treatment. This is the only design mode in v1.

## Check Status

```bash
curl -s http://127.0.0.1:8060/api/rebrands/{job_id}
```

Statuses:

- `queued`
- `running`
- `complete`
- `failed`

## Get Report

```bash
curl -s http://127.0.0.1:8060/api/rebrands/{job_id}/report
```

The report includes:

- detected framework/build hints,
- detected styling approach,
- source theme polarity,
- requested and resolved target theme polarity,
- changed CSS/HTML/logo files,
- color mapping table,
- warnings,
- pointer to next-stage work.

## Download Result

```bash
curl -L -o rebranded.zip http://127.0.0.1:8060/api/rebrands/{job_id}/download
```

The downloaded ZIP includes the transformed codebase plus:

```text
REBRAND_REPORT.json
RESTYLE_WORKORDER.md
```

## Get Work Order

```bash
curl -L -o RESTYLE_WORKORDER.md http://127.0.0.1:8060/api/rebrands/{job_id}/workorder
```

The work order is intended for the next layer of the system: a code/design agent that can inspect components, run the app, take screenshots, and make deeper UI changes.

## How The Rebrand Pass Works

The current engine is deterministic:

1. Extract the uploaded ZIP into a controlled job folder.
2. Skip heavy or unsafe directories such as `.git`, `node_modules`, `dist`, `build`, `.next`, and `vendor`.
3. Detect the app shape from files such as `package.json`, CSS files, and HTML files.
4. Inventory CSS colors and infer their roles: background, foreground, border, shadow, or unknown.
5. Detect source theme polarity and accent color.
6. Resolve the requested target theme: `auto`, `light`, or `dark`.
7. Rewrite CSS colors and fonts using OPSWAT tokens.
8. Add an OPSWAT baseline CSS layer.
9. Swap matching logo/favicon files with appropriate OPSWAT assets.
10. Inject web font references where needed.
11. Write the report and work order.
12. Package the transformed codebase.

## Safety Notes

- Uploaded ZIPs are extracted into controlled per-job folders.
- Absolute paths, `..` traversal, and symlinks are rejected.
- Common heavy folders are skipped.
- V1 does not run `npm install`.
- V1 does not run uploaded build scripts.
- V1 does not execute uploaded application code.
- Output is produced from a copied source tree, not by mutating the uploaded archive.

## Current Limits

- Plain CSS/HTML works best.
- Tailwind is detected, but config-level transformation is not yet complete.
- CSS-in-JS is detected, but template literal transformation is not yet complete.
- The deterministic pass does not perform full component layout redesign by itself.
- The API does not currently run a browser visual QA loop.
- `full` mode emits a work order for the later AI/code-agent restyle stage.

## Roadmap

### Phase 1 - Codebase Rebrand API

Status: in progress.

Goals:

- accept zipped web codebases,
- safely extract and process source files,
- apply OPSWAT tokens and theme treatment,
- support `auto`, `light`, and `dark` theme output,
- swap appropriate OPSWAT logos/assets,
- emit report and work order,
- return downloadable transformed ZIP.

### Phase 2 - Smarter Frontend Transformations

Goals:

- stronger Tailwind support,
- stronger CSS-in-JS support,
- component-aware transformations for React/Vue/Svelte,
- detection of common layout regions such as top bars, sidebars, panels, cards, forms, tables, canvases, and toolbars,
- automatic replacement of generic icons with OPSWAT/lucide-style equivalents where appropriate,
- preservation of application behavior while changing visual presentation.

### Phase 3 - Visual QA Agent Layer

Goals:

- run the transformed app in a sandbox,
- capture desktop and mobile screenshots,
- compare against OPSWAT design expectations,
- detect unreadable text, missing logos, broken contrast, overflow, and layout collapse,
- iterate code changes until the UI is visibly acceptable,
- attach before/after screenshots to the job report.

### Phase 4 - DOCX Rebrand Route

Potential route:

```text
POST /api/rebrands/documents
```

Goals:

- accept `.docx` files,
- apply OPSWAT document styling,
- use OPSWAT fonts and heading hierarchy,
- apply correct logo/header/footer treatment,
- normalize colors, tables, callouts, captions, and page structure,
- return a branded `.docx` plus a report.

Later enhancement:

- support batch document uploads,
- support template selection,
- support tracked changes or review notes.

### Phase 5 - PDF Rebrand Route

Potential route:

```text
POST /api/rebrands/pdfs
```

Goals:

- accept PDFs for visual restyling or conversion workflows,
- extract text/images/layout where feasible,
- classify document type,
- rebuild content into OPSWAT-branded output where reliable,
- return a branded PDF plus a report.

Important note:

PDFs are harder than DOCX because many PDFs are final-layout artifacts rather than editable source. The likely best route is to extract content, rebuild in a controlled template, then render a new PDF.

### Phase 6 - PPTX / Presentation Rebrand Route

Potential route:

```text
POST /api/rebrands/presentations
```

Goals:

- accept `.pptx`,
- apply OPSWAT presentation theme,
- normalize titles, spacing, typography, color, footers, and logo usage,
- optionally re-layout messy slides,
- return a branded `.pptx` plus a report.

This can share useful logic with the existing export/deck work.

### Phase 7 - Central Brand Service Integration

Goals:

- consume brand assets from a central internal asset registry,
- version design tokens,
- expose supported design systems through `/api/health`,
- allow teams to pin a design version for reproducible output.

## Production Notes

Before wider internal use:

- put the API behind authentication,
- set upload size and job retention limits,
- store jobs on durable disk or object storage,
- add structured logs,
- add per-job audit metadata,
- add basic malware/file type scanning for uploaded archives,
- separate uploaded source from public web roots,
- run workers with least privilege,
- consider a queue if large jobs become common.

## Development

Compile check:

```bash
PYTHONPYCACHEPREFIX=/tmp/opswat-rebrand-pycache python -m py_compile api.py opswat_rebrand/*.py
```

Run API:

```bash
.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8060 --reload
```

Run CLI:

```bash
python -m opswat_rebrand ./my-app -o ./my-app-opswat --depth full --target-theme auto
```
