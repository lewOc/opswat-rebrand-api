"""OPSWAT token sets + colour maths + classification/mapping.

The target is the OPSWAT product-UI design system (opswat-ui): Inter, #1d6bfc, light
content areas. Mapping is role-aware: the same source colour maps differently depending
on whether it is used as a background, foreground (text), border or shadow.
"""
import re

# ---- OPSWAT product-UI tokens -------------------------------------------------
PRIMARY        = "#1d6bfc"
PRIMARY_HOVER  = "#154fba"
PRIMARY_LIGHT  = "#eff4ff"
# neutral ramp, light → dark
NEUTRALS = ["#ffffff", "#f4f4f5", "#e9eaeb", "#d2d4d6", "#bcbfc3",
            "#a4a8ae", "#707682", "#485161", "#1b273c", "#080f21"]
BG_NEUTRALS     = ["#ffffff", "#f4f4f5", "#e9eaeb", "#d2d4d6"]   # light → less light
FG_NEUTRALS     = ["#1b273c", "#485161", "#707682", "#a4a8ae"]   # dark → less dark
BORDER_NEUTRALS = ["#e9eaeb", "#d2d4d6"]
DARK_BG_NEUTRALS = ["#050916", "#080f21", "#0b1424", "#132346"]
DARK_FG_NEUTRALS = ["#ffffff", "#d7e1fc", "#a9bee6", "#707682"]
DARK_BORDER = "#284678"
SHADOW_RGB      = (27, 39, 60)
STATUS = {"error": "#d00300", "success": "#008a00", "warning": "#ed6706",
          "purple": "#7e32dd", "teal": "#178594", "info": "#1d6bfc"}
FONT_SANS = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
FONT_MONO = '"Simplon Mono Light", "SF Mono", Consolas, monospace'

HEX_RE  = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b')
RGB_RE  = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9.]+)\s*)?\)')
COLOR_RE = re.compile(HEX_RE.pattern + '|' + RGB_RE.pattern)

# ---- colour maths -------------------------------------------------------------
def parse(s):
    """'#rrggbb' / rgba(...) → (r,g,b,a) or None."""
    s = s.strip()
    m = HEX_RE.fullmatch(s) or HEX_RE.match(s)
    if m and s.startswith('#'):
        h = m.group(1)
        if len(h) in (3, 4):
            h = ''.join(c*2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b, a)
    m = RGB_RE.match(s)
    if m:
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), a)
    return None

def luminance(rgb):
    def lin(c):
        c /= 255.0
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b)

def hsv(rgb):
    r, g, b = [c/255.0 for c in rgb[:3]]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/d) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/d) + 120) % 360
    else:
        h = (60 * ((r-g)/d) + 240) % 360
    s = 0 if mx == 0 else d/mx
    return h, s, mx

def hue_family(rgb):
    h, s, v = hsv(rgb)
    if s < 0.18 or v < 0.08:
        return "grey"
    if h < 18 or h >= 330:  return "red"
    if h < 45:   return "orange"
    if h < 70:   return "yellow"
    if h < 160:  return "green"
    if h < 200:  return "teal"
    if h < 255:  return "blue"      # includes cyan-blue + blue
    if h < 290:  return "indigo"
    return "purple"

def _to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])

def _fmt(rgb, a):
    if a is None or a >= 0.999:
        return _to_hex(rgb)
    return "rgba(%d, %d, %d, %s)" % (rgb[0], rgb[1], rgb[2], ("%g" % a))

def _nearest_by_lum(candidates, target_lum):
    return min(candidates, key=lambda c: abs(luminance(parse(c)) - target_lum))

# ---- the mapper ---------------------------------------------------------------
class Mapper:
    """Maps one source colour → an OPSWAT colour, given its CSS role and the
    detected polarity of the source theme."""
    def __init__(self, polarity, accent_rgb, target_polarity="light"):
        self.polarity = polarity          # source: "dark" or "light"
        self.target_polarity = target_polarity
        self.accent = accent_rgb          # (r,g,b) of the brand accent, or None

    def _is_accent(self, rgb):
        if not self.accent:
            return False
        fam = hue_family(rgb)
        return fam in ("blue", "teal") and abs(hsv(rgb)[0] - hsv(self.accent)[0]) < 45

    def map(self, rgba, role):
        rgb, a = rgba[:3], rgba[3]
        h, s, v = hsv(rgb)
        L = luminance(rgb)
        fam = hue_family(rgb)
        vivid = s > 0.45 and v > 0.45          # a real accent/status colour, not a dark navy

        # borders + shadows are always neutral in OPSWAT (regardless of source hue)
        if role == "shadow":
            return _fmt((0, 0, 0) if self.target_polarity == "dark" else SHADOW_RGB,
                        a if (a is not None and a < 1) else 0.18)
        if role == "border":
            if self.target_polarity == "dark":
                return self._out(DARK_BORDER, a)
            return self._out(BORDER_NEUTRALS[0], a)

        # vivid brand / status colours
        if vivid:
            if fam in ("blue", "teal"):
                return self._out(PRIMARY_HOVER if L < 0.18 else PRIMARY, a)
            if fam == "red":                 return self._out(STATUS["error"], a)
            if fam in ("orange", "yellow"):  return self._out(STATUS["warning"], a)
            if fam == "green":               return self._out(STATUS["success"], a)
            if fam in ("purple", "indigo"):  return self._out(STATUS["purple"], a)

        # neutrals / muted tints / dark navies-as-surface — role + polarity aware
        if self.target_polarity == "dark":
            if role == "bg":
                if L < 0.08:
                    tgt = DARK_BG_NEUTRALS[0]
                elif L < 0.18:
                    tgt = DARK_BG_NEUTRALS[1]
                elif L < 0.45:
                    tgt = DARK_BG_NEUTRALS[2]
                else:
                    tgt = DARK_BG_NEUTRALS[1]
                return self._out(tgt, a)
            if role == "fg":
                if self.polarity == "light":
                    tgt = "#ffffff" if L < 0.24 else "#d7e1fc" if L < 0.5 else "#a9bee6"
                else:
                    tgt = "#ffffff" if L > 0.74 else "#d7e1fc" if L > 0.5 else "#a9bee6" if L > 0.25 else "#707682"
                return self._out(tgt, a)
            return self._out(_nearest_by_lum(DARK_BG_NEUTRALS + DARK_FG_NEUTRALS, L), a)

        invert = (self.polarity == "dark")     # dark source → light OPSWAT
        if role == "bg":
            if invert:
                return self._out("#f4f4f5" if L < 0.06 else "#ffffff", a)
            return self._out(_nearest_by_lum(BG_NEUTRALS, max(L, 0.86)), a)
        if role == "fg":
            if invert:    # brighter source text = higher emphasis → darker OPSWAT text
                tgt = "#1b273c" if L > 0.7 else "#485161" if L > 0.45 else "#707682" if L > 0.25 else "#a4a8ae"
            else:         # already-dark text: darker = higher emphasis
                tgt = "#1b273c" if L < 0.15 else "#485161" if L < 0.3 else "#707682" if L < 0.5 else "#a4a8ae"
            return self._out(tgt, a)
        # unknown role
        if invert:
            return self._out("#1b273c" if L > 0.6 else ("#f4f4f5" if L < 0.1 else "#ffffff"), a)
        return self._out(_nearest_by_lum(NEUTRALS, L), a)

    def map_tile(self, rgba):
        """For an icon chip (element with both a bg colour and a bg image): preserve
        luminance polarity so light glyphs stay legible on a dark tile (and vice-versa)."""
        rgb, a = rgba[:3], rgba[3]
        h, s, v = hsv(rgb)
        if s > 0.45 and v > 0.45:               # vivid tile → primary/status, reuse map
            return self.map(rgba, "fg")
        return self._out(_nearest_by_lum(NEUTRALS, luminance(rgb)), a)

    @staticmethod
    def _out(hexstr, a):
        rgb = parse(hexstr)
        return _fmt(rgb, a)
