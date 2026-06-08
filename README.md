# OPSWAT Rebrand API

Reusable service for rebranding web codebases into OPSWAT Product UI style.

This is app-agnostic. It is not tied to Flow Architect or any single OPSWAT demo.
Flow Architect is only a useful test case because it is a real app that needs an
OPSWAT redesign. The intended workflow is: build any internal web tool, zip the
repo, send it to this API, and receive an OPSWAT-branded version back.

V1 accepts a zipped web codebase, runs the deterministic OPSWAT rebrand engine, and returns:

- a rebranded ZIP,
- `REBRAND_REPORT.json`,
- optional `RESTYLE_WORKORDER.md` for full mode.

It does not execute uploaded code. It rewrites a copied source tree only.

## Boundary

This API is for design/codebase transformation.

It does not:

- generate account maps,
- generate diagrams,
- perform product-fit reasoning,
- export account-map decks,
- retrieve customer stories.

Future routes can add document transformation:

```text
/api/rebrands/codebases
/api/rebrands/documents
/api/rebrands/pdfs
/api/rebrands/presentations
```

For now, `/api/rebrands` is codebase ZIP only.

Suitable examples:

- a use-case generator,
- a partner account-mapping tool,
- an internal dashboard,
- a diagram helper UI,
- a proof-of-concept web app that needs OPSWAT styling.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Run:

```bash
.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8060 --reload
```

Open:

```text
http://127.0.0.1:8060/docs
```

## Endpoints

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

Depth options:

- `tokens` - color/font token rewrite only.
- `theme` - token rewrite plus OPSWAT baseline CSS and logo swap.
- `full` - theme plus `RESTYLE_WORKORDER.md` for agentic component restyle and visual QA.

Target theme options:

- `auto` - preserve the detected source polarity; dark apps stay dark, light apps stay light.
- `dark` - force OPSWAT dark product styling.
- `light` - force OPSWAT light product styling.

## Check Status

```bash
curl -s http://127.0.0.1:8060/api/rebrands/{job_id}
```

## Download Result

```bash
curl -L -o rebranded.zip http://127.0.0.1:8060/api/rebrands/{job_id}/download
```

## Safety Notes

- Uploaded ZIPs are extracted into controlled per-job folders.
- Absolute paths, `..` traversal, and symlinks are rejected.
- Common heavy folders such as `.git`, `node_modules`, `dist`, `build`, `.next`, and `vendor` are skipped by the rebrand engine.
- V1 does not run `npm install`, build scripts, or uploaded application code.

## Current Limits

- Plain CSS/HTML works best.
- Tailwind and CSS-in-JS are detected and reported, but not fully transformed yet.
- The deterministic pass does not perform full component layout redesign by itself.
- `full` mode emits a work order for the later AI/code-agent restyle stage.
