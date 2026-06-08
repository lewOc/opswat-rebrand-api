# OPSWAT Rebrand Kit

Codebase-agnostic toolkit for rebranding a web app to OPSWAT design. Pair this with the
asset hub in `../opswat-brand/`. Nothing here touches a target codebase until you run the
playbook against one.

## The two "OPSWAT designs" (read first)

There are two distinct, non-identical OPSWAT design definitions. Pick deliberately:

| | **Product UI** (`opswat-ui` skill) | **Corporate brand** (`opswat-brand/`) |
|---|---|---|
| Use for | Apps, dashboards, tools | Marketing, decks, print, collateral |
| Font | **Inter** | **Simplon Norm** |
| Primary blue | `#1d6bfc` | `#2571FB` / `#2672FB` |
| Logo | text `OPSWAT.` (700) | real SVG lockups |

**For rebranding a codebase → use Product UI tokens (this kit) + real logos from the hub.**
That's the best of both: the app looks like a real OPSWAT product, with authentic logo assets.

## Files

| File | For | How |
|------|-----|-----|
| `opswat-theme.css` | Plain CSS / CSS-vars / styled-components apps | import at root; map app vars → `--opswat-*` |
| `tailwind.opswat.preset.js` | Tailwind apps | add to `presets:[]` in `tailwind.config.js` |
| (logos) | any | pull from `../opswat-brand/logos/opswat/` (SVG) |

## The rebrand playbook (what the tool does to a target)

Run on a **copy/branch** of the target, never the original.

1. **Detect** — read `package.json`, find styling approach (Tailwind config? global CSS? CSS-in-JS?),
   locate the color/font definitions and the logo/favicon.
2. **Inventory current tokens** — grep all hex colors + font-families; build a mapping table
   old→OPSWAT (brand blue→`#1d6bfc`, greys→`n-*` scale, success/warn/error→status colors).
3. **Inject the theme** — Tailwind: add the preset; CSS: import `opswat-theme.css` + add `opswat-theme`
   class at root. Load Inter.
4. **Apply token map (mechanical)** — find/replace old color/font tokens with OPSWAT ones.
   Deterministic; review the mapping table before applying.
5. **Swap assets** — replace logo with `../opswat-brand/logos/opswat/OPSWAT_logo_notag_blue.svg`
   (or `_white` on dark bg), favicon with the mark, optionally product icons from the hub.
6. **Component restyle (LLM + `opswat-ui`)** — bring buttons, inputs, cards, tables, nav, badges,
   modals into line with the component specs in the `opswat-ui` skill. This is the "full restyle" step.
7. **Verify** — install, build, run; screenshot before/after; check contrast + that nothing broke.

## Logo quick-pick (from `../opswat-brand/logos/opswat/`)

- On light bg: `OPSWAT_logo_notag_blue.svg` (wordmark) or `OPSWAT_logo_mark_blue.svg` (symbol)
- On dark bg/navbar: `OPSWAT_logo_notag_white.svg` / `OPSWAT_logo_mark_white.svg`
- Respect clearspace — see `../opswat-brand/logos/opswat/clearspace/`

## Notes
- ⚖️ Inter is open-licensed (OFL) — safe to ship. Simplon Norm is licensed; only use it if the
  rebrand specifically needs corporate fidelity and licensing is cleared.
- Status colors are non-negotiable: green=good, orange=warning, red=bad, blue=info.
- Keep radii small (≤8px) and stick to the 8px spacing grid.
