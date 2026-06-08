"""Orchestrates the rebrand: copy → detect → transform → report → (full) work order."""
import os, re, json, shutil
from . import engine as E
from . import palette as P

CSS_EXT = ('.css',)
HTML_EXT = ('.html', '.htm')
SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', '.next', 'vendor', '_archive'}

# OPSWAT brand hub (real fonts/logos), located relative to this package
BRAND_DIR = os.environ.get(
    "OPSWAT_BRAND_DIR",
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "opswat-brand")))
LOGO_RE = re.compile(r'(?i)(logo|favicon|brandmark|wordmark)')

def _walk(root, exts):
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(exts):
                yield os.path.join(dp, f)

def swap_assets(out):
    """Replace the app's own logo/favicon image files with the authentic OPSWAT logo
    (matching extension). Returns list of replaced relpaths."""
    src_logo = {
        "logo": os.path.join(BRAND_DIR, "logos", "opswat", "OPSWAT_logo_notag_navy.%s"),
        "mark": os.path.join(BRAND_DIR, "logos", "opswat", "OPSWAT_logo_mark_navy.%s"),
    }
    replaced = []
    for dp, dirs, files in os.walk(out):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = f.rsplit('.', 1)[-1].lower()
            if ext not in ('svg', 'png') or not LOGO_RE.search(f):
                continue
            kind = "mark" if re.search(r'(?i)(favicon|mark)', f) else "logo"
            cand = src_logo[kind] % ext
            if os.path.exists(cand):
                shutil.copy(cand, os.path.join(dp, f))
                replaced.append(os.path.relpath(os.path.join(dp, f), out))
    return replaced

def detect_stack(src):
    has = lambda p: os.path.exists(os.path.join(src, p))
    info = {"styling": [], "framework": None, "build": None}
    pkg = os.path.join(src, 'package.json')
    if os.path.exists(pkg):
        try:
            d = json.load(open(pkg))
            deps = {**d.get('dependencies', {}), **d.get('devDependencies', {})}
            for fw in ('react', 'vue', 'svelte', 'next', '@angular/core'):
                if fw in deps: info['framework'] = fw; break
            for b in ('vite', 'next', 'webpack', 'parcel'):
                if b in deps: info['build'] = b; break
            if 'tailwindcss' in deps: info['styling'].append('tailwind')
            if 'styled-components' in deps: info['styling'].append('styled-components')
        except Exception:
            pass
    if any(_walk(src, CSS_EXT)): info['styling'].append('css')
    if not info['framework'] and any(_walk(src, HTML_EXT)): info['framework'] = 'static'
    return info

def run(src, out, depth="full", target_theme="auto", verbose=True):
    if os.path.abspath(src) == os.path.abspath(out):
        raise SystemExit("Refusing to write over the source. Choose a different --out.")
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(*SKIP_DIRS))

    stack = detect_stack(out)

    # ---- inventory across all CSS to detect polarity + accent ----
    agg = {}
    for css_path in _walk(out, CSS_EXT):
        css = open(css_path, encoding='utf-8', errors='ignore').read()
        for k, rec in E.inventory(css).items():
            a = agg.setdefault(k, {'count': 0, 'roles': {}, 'alpha': rec['alpha']})
            a['count'] += rec['count']
            for r, n in rec['roles'].items():
                a['roles'][r] = a['roles'].get(r, 0) + n
    polarity, accent = E.detect_polarity_accent(agg)
    target_polarity = polarity if target_theme == "auto" else target_theme
    mapper = P.Mapper(polarity, accent, target_polarity=target_polarity)

    # ---- transform CSS (declaration-aware colour + font remap) ----
    css_files = []
    for css_path in _walk(out, CSS_EXT):
        css = open(css_path, encoding='utf-8', errors='ignore').read()
        new = E.rewrite_css(css, mapper)
        if depth in ('theme', 'full'):
            new += E.baseline_override(target_polarity)
        if new != css:
            open(css_path, 'w', encoding='utf-8').write(new)
            css_files.append(os.path.relpath(css_path, out))

    # ---- transform HTML (inject Inter) ----
    html_files = []
    for h_path in _walk(out, HTML_EXT):
        html = open(h_path, encoding='utf-8', errors='ignore').read()
        new, changed = E.inject_fonts_html(html)
        if changed:
            open(h_path, 'w', encoding='utf-8').write(new)
            html_files.append(os.path.relpath(h_path, out))

    # ---- swap logo/favicon assets for the real OPSWAT logo (theme+/full) ----
    logos_swapped = []
    if depth in ('theme', 'full'):
        logos_swapped = swap_assets(out)

    color_map = E.build_color_map(agg, mapper)
    report = {
        "stack": stack,
        "source_theme": {"polarity": polarity,
                          "accent": ("#%02x%02x%02x" % accent) if accent else None},
        "target_theme": {"polarity": target_polarity, "requested": target_theme},
        "depth": depth,
        "files_changed": {"css": css_files, "html": html_files, "logos": logos_swapped},
        "color_map": color_map,
        "fonts": {"sans": "Inter", "mono": "Simplon Mono Light"},
        "warnings": _warnings(stack, depth),
        "next_stage": ("LLM component-restyle + visual-verify — see RESTYLE_WORKORDER.md"
                       if depth == "full" else None),
    }
    json.dump(report, open(os.path.join(out, "REBRAND_REPORT.json"), 'w'), indent=2)
    if depth == "full":
        open(os.path.join(out, "RESTYLE_WORKORDER.md"), 'w').write(_workorder(report))

    if verbose:
        _print_summary(report, out)
    return report

def _warnings(stack, depth):
    w = []
    if 'tailwind' in stack['styling']:
        w.append("Tailwind detected — colours may live in tailwind.config; "
                 "apply the OPSWAT preset (rebrand-kit/tailwind.opswat.preset.js) too.")
    if 'styled-components' in stack['styling']:
        w.append("CSS-in-JS detected — colours in .js/.ts template literals are NOT yet "
                 "remapped by the deterministic pass; handle in the restyle stage.")
    if depth != 'full':
        w.append("Component shapes (buttons/cards/menus) are only restyled at depth=full.")
    return w

def _workorder(report):
    cm = "\n".join("- `%s` → `%s`  (%s, %dx)" % (r['from'], r['to'], r['role'], r['count'])
                   for r in report['color_map'][:20])
    return """# OPSWAT Restyle Work Order

The deterministic pass remapped colours/fonts. Now restyle components to the OPSWAT
product-UI design system using the `opswat-ui` skill, then verify visually.

## Context
- Source theme polarity: **%s**, brand accent: **%s**
- Target theme polarity: **%s** (requested: `%s`)
- Token map applied (top 20):
%s

## Tasks (per opswat-ui specs)
1. **Buttons** — primary solid `#1d6bfc` (hover `#154fba`), 4px radius, no glow, sentence case;
   secondary white + `#d2d4d6` border; ghost transparent.
2. **Cards / panels / menus** — white bg, `1px #e9eaeb` border, 6px radius, subtle shadow.
   Watch for dark fills using a hex that is *also* a text colour (render to confirm).
3. **Inputs** — 36px, `1px #d2d4d6`, focus ring `0 0 0 2px #7eaafd`.
4. **Nav / header** — clean; place a real OPSWAT logo (../opswat-brand/logos/opswat/).
5. **Canvas/empty areas** — light `#f4f4f5`, optional subtle dot grid.

## Verify loop (REQUIRED)
Serve the app, screenshot at 1440×900, compare against opswat-ui, fix issues, repeat until
clean. Use computed styles (getComputedStyle) to confirm exact token values.
""" % (
        report['source_theme']['polarity'],
        report['source_theme']['accent'],
        report.get('target_theme', {}).get('polarity', 'light'),
        report.get('target_theme', {}).get('requested', 'auto'),
        cm,
    )

def _print_summary(r, out):
    print("OPSWAT rebrand complete → %s" % out)
    print("  stack:      %s / %s" % (r['stack']['framework'], ", ".join(r['stack']['styling']) or "—"))
    print("  source:     %s theme, accent %s" % (r['source_theme']['polarity'], r['source_theme']['accent']))
    print("  changed:    %d CSS, %d HTML, %d logo(s)" % (
        len(r['files_changed']['css']), len(r['files_changed']['html']),
        len(r['files_changed'].get('logos', []))))
    print("  colours:    %d distinct remapped" % len(r['color_map']))
    for w in r['warnings']:
        print("  ! " + w)
    print("  report:     REBRAND_REPORT.json" + ("  + RESTYLE_WORKORDER.md" if r['depth'] == 'full' else ""))
