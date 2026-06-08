# OPSWAT Brand Hub

Machine-readable OPSWAT brand asset library — the source library for the branding API/tool.

**Source of truth:** rebuilt from `Sales Content/Brand Corporate`, the design-team-maintained
asset pack (itself a local snapshot of the online OPSWAT Brand Hub). This supersedes the earlier
draft that was bootstrapped from `presentation_template.pptx`.

## Layout

| Path | What | Format | Count |
|------|------|--------|-------|
| `tokens/tokens.json` · `.css` | Colors + font definitions (with `@font-face`) | JSON / CSS | 15 colors |
| `fonts/` | **Simplon Norm** — the brand typeface | OTF | 8 weights |
| `logos/opswat/` | Full OPSWAT logo matrix | SVG + PNG | 64 |
| `logos/opswat/clearspace/` | Official clearspace usage guides | PNG | 10 |
| `logos/opswat-academy/` | OPSWAT Academy logo | SVG | 10 |
| `icons/line-art/` | Flat UI/marketing icons (recolorable) | SVG | 284 |
| `icons/product-3d/` | 3D isometric **product** icons | PNG | 66 |
| `icons/generic-3d/` | 3D isometric **generic** icons | PNG | 280 |
| `templates/` | Letterhead + Word doc templates | DOCX | 2 |
| `manifest.json` | Full structured index of everything below | JSON | — |

## Logo naming schema

`OPSWAT_logo_<lockup>_<color>.{svg,png}`

- **lockup:** `mark` (symbol only) · `notag` (wordmark) · `tag-center` / `tag-left` (1-line tagline) ·
  `tag-2line-center` / `tag-2line-left` (2-line tagline)
- **color:** `blue` · `navy` · `midnight` · `white` · `blue-navy` · `blue-white`

## Icon naming schema

- **Line art:** `[mar-]<category>-<name>.svg` — categories: `ui` (66), `device` (49), `files` (37),
  `technologies` (28), `threats` (26), `industries` (21), `software` (14), `benefits` (13),
  `process` (11), `network` (10), `cloud` (9). SVGs are single-color and **recolorable** to any token.
- **3D product:** `OPSWAT_T3_opswat-product-<name>-<left|right>-<color>.png`

## Key colors (see `tokens/`)

Blue `#2571FB` (logo `#2672FB`) · Navy `#0D2553` (logo `#07244A`) · Midnight `#040121` ·
Cyan `#03E7F5` · Green `#00FFB2` · Red `#FF003C` · Yellow `#FFD600` · Orange `#FF6B00`.
**`OPSWAT_Brand-Guidelines-2025.pdf` is the final arbiter** for exact palette + usage.

## Not copied here (referenced in source to keep this lean)

- **Print logos** (CMYK EPS/TIFF, ~30MB) → `Logos/OPSWAT/CMYK/` in source
- **Brand guidelines PDF** (~101MB) → `OPSWAT_Brand-Guidelines-2025.pdf` in source — parse for the
  API's do/don't rules engine (clearspace, min sizes, color-on-background)
- **Line-art PNG color sets** (Navy/White/Blue @500px) → in source; regenerate from the SVGs instead

## Notes
- ⚖️ **Font licensing:** Simplon Norm is commercially licensed (Lineto). Internal use is fine;
  embedding/redistributing via a public-facing API needs a license check.
- Simplon **Mono** is referenced in tokens but not in this pack — source separately if code-rendering needs it.
- All paths and exact source locations are in `manifest.json`.
