"""Rebrand engine: detect → inventory → map → transform → report.

Deterministic stages only. The component-restyle + visual-verify loop (the LLM stage)
is emitted as a work order for a Claude agent to execute (see RESTYLE_WORKORDER.md).
"""
import os, re, json, shutil
from . import palette as P

BLOCK_RE = re.compile(r'\{([^{}]*)\}')
DECL_RE  = re.compile(r'^(\s*)(--[-A-Za-z0-9]+|[-A-Za-z]+)\s*:(.*)$', re.S)

# ---- role inference -----------------------------------------------------------
def role_of(prop):
    p = prop.lower()
    if p.startswith('--'):
        if re.search(r'(bg|background|surface|panel|elevat|fill|canvas)', p): return 'bg'
        if re.search(r'(text|fg|foreground|ink|content|muted|label|heading)', p): return 'fg'
        if re.search(r'(border|stroke|divider|outline|line)', p): return 'border'
        if re.search(r'(shadow|glow)', p): return 'shadow'
        return 'unknown'
    if p in ('background', 'background-color', 'background-image'): return 'bg'
    if p in ('color', 'fill'): return 'fg'
    if 'border' in p or p.startswith('outline') or p == 'stroke': return 'border'
    if p in ('box-shadow', 'text-shadow'): return 'shadow'
    return 'unknown'

# ---- iterate declarations inside every rule block -----------------------------
def _each_block(css):
    for m in BLOCK_RE.finditer(css):
        yield m

def _split_decls(body):
    # split on ';' but keep data: URIs intact (rejoined verbatim)
    return body.split(';')

# ---- INVENTORY ----------------------------------------------------------------
def inventory(css):
    """Returns {(r,g,b): {'count':n,'roles':Counter,'sample':a}} and bg stats."""
    colors = {}
    for blk in _each_block(css):
        for piece in _split_decls(blk.group(1)):
            m = DECL_RE.match(piece)
            if not m:
                continue
            prop, val = m.group(2), m.group(3)
            role = role_of(prop)
            for cm in P.COLOR_RE.finditer(val):
                rgba = P.parse(cm.group(0))
                if not rgba:
                    continue
                key = rgba[:3]
                rec = colors.setdefault(key, {'count': 0, 'roles': {}, 'alpha': rgba[3]})
                rec['count'] += 1
                rec['roles'][role] = rec['roles'].get(role, 0) + 1
    return colors

def detect_polarity_accent(colors):
    # polarity: weigh dark vs light background instances (a var()-referenced base bg
    # has a low literal count, so vote across all bg-role usages instead of picking one).
    dark_bg = light_bg = 0
    for k, v in colors.items():
        if not v['roles'].get('bg', 0):
            continue
        if v['alpha'] is not None and v['alpha'] <= 0.4:
            continue  # faint overlays aren't the base surface
        L = P.luminance(k)
        n = v['roles']['bg']
        if L < 0.3:   dark_bg += n
        elif L > 0.7: light_bg += n
    polarity = 'dark' if dark_bg > light_bg else 'light'
    # accent: most-used saturated colour
    sat = [(k, v) for k, v in colors.items()
           if P.hsv(k)[1] > 0.4 and P.hsv(k)[2] > 0.3 and P.hue_family(k) != 'grey']
    accent = max(sat, key=lambda kv: kv[1]['count'])[0] if sat else None
    return polarity, accent

# ---- TRANSFORM ----------------------------------------------------------------
def _colors_in(val):
    out = []
    for m in P.COLOR_RE.finditer(val):
        c = P.parse(m.group(0))
        if c:
            out.append(c)
    return out

def _is_vivid(c):
    h, s, v = P.hsv(c[:3])
    return s > 0.45 and v > 0.45

def flatten_bg(val, mapper):
    """Decorative gradient → a flat OPSWAT surface (OPSWAT is flat). A solid accent
    fill (e.g. a button) keeps its colour; a decorative wash becomes a light surface."""
    cols = _colors_in(val)
    if not cols:
        return "#ffffff"
    decorative = ('transparent' in val.lower()
                  or any((c[3] is not None and c[3] < 0.85) for c in cols))
    if not decorative:
        for c in cols:
            if _is_vivid(c):
                return mapper.map((c[0], c[1], c[2], 1.0), "bg")  # vivid → primary/status
    return "#ffffff"

def deglow_shadow(val, mapper):
    """Neon glow (saturated-colour shadow) → OPSWAT subtle shadow; else None (map normally)."""
    if any(_is_vivid(c) for c in _colors_in(val)):
        return "0 2px 8px rgba(27, 39, 60, 0.10)"
    return None

def rewrite_css(css, mapper):
    def color_sub(val, role, tile=False):
        def one(cm):
            r = P.parse(cm.group(0))
            if not r:
                return cm.group(0)
            return mapper.map_tile(r) if (tile and role == 'bg') else mapper.map(r, role)
        return P.COLOR_RE.sub(one, val)

    def fix_block(m):
        out = []
        body = m.group(1)
        # icon chip = holds a bg image (url) or positions one (size/repeat/position) → keep tile polarity
        is_chip = ('url(' in body) or bool(re.search(r'background-(size|repeat|position)\s*:', body))
        for piece in _split_decls(m.group(1)):
            dm = DECL_RE.match(piece)
            if not dm:
                out.append(piece); continue
            ws, prop, val = dm.group(1), dm.group(2), dm.group(3)
            pl = prop.lower()
            role = role_of(prop)
            if pl == 'font-family':
                low = val.lower()
                newval = val if any(k in low for k in ('inherit', 'initial', 'unset')) \
                    else ' ' + (P.FONT_MONO if 'mono' in low else P.FONT_SANS)
            elif 'gradient(' in val and pl in ('background', 'background-image', 'background-color'):
                newval = ' none' if pl == 'background-image' else ' ' + flatten_bg(val, mapper)
            elif role == 'shadow':
                dg = deglow_shadow(val, mapper)
                newval = ' ' + dg if dg else color_sub(val, role)
            else:
                newval = color_sub(val, role, tile=is_chip)
            out.append(ws + prop + ':' + newval)
        return '{' + ';'.join(out) + '}'
    return BLOCK_RE.sub(fix_block, css)

INTER_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
              '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />')

def inject_fonts_html(html):
    if 'fonts.googleapis.com/css2?family=Inter' in html:
        return html, False
    m = re.search(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', html, re.I)
    if m:
        return html[:m.start()] + INTER_LINK + '\n    ' + html[m.start():], True
    m = re.search(r'</head>', html, re.I)
    if m:
        return html[:m.start()] + '    ' + INTER_LINK + '\n  ' + html[m.start():], True
    return html, False

BASELINE_OVERRIDE = """
/* ===== OPSWAT baseline (opswat-rebrand, depth>=theme) — app-agnostic ===== */
body { font-family: %s; }
a { color: %s; }
:focus-visible { outline: none; box-shadow: 0 0 0 2px #7eaafd; }

/* De-neon + flatten all button-like controls to OPSWAT spec */
button, input[type="button"], input[type="submit"], input[type="reset"],
[role="button"], .btn, [class*="btn"], [class*="Btn"], [class*="button"], [class*="Button"] {
  text-transform: none !important;
  letter-spacing: normal !important;
  border-radius: 4px !important;
  box-shadow: none !important;
  background-image: none !important;
}
/* Primary / submit / CTA controls → solid OPSWAT blue */
input[type="submit"],
[class*="primary"], [class*="Primary"], [class*="cta"], [class*="Cta"], [class*="CTA"] {
  background-color: %s !important;
  border-color: %s !important;
  color: #ffffff !important;
}
[class*="primary"]:hover, [class*="Primary"]:hover,
input[type="submit"]:hover { background-color: %s !important; border-color: %s !important; }
/* Inputs → OPSWAT */
input:not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]),
select, textarea {
  border-radius: 4px !important;
}
""" % (P.FONT_SANS, P.PRIMARY, P.PRIMARY, P.PRIMARY, P.PRIMARY_HOVER, P.PRIMARY_HOVER)

# ---- REPORT -------------------------------------------------------------------
def build_color_map(colors, mapper):
    rows = []
    for key, rec in sorted(colors.items(), key=lambda kv: -kv[1]['count']):
        role = max(rec['roles'], key=rec['roles'].get)
        src = "#%02x%02x%02x" % key
        rows.append({"from": src, "to": mapper.map((key[0], key[1], key[2], 1.0), role),
                     "role": role, "count": rec['count']})
    return rows
