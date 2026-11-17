#!/usr/bin/env python3
"""Render the profile README cards as self-contained animated SVGs.

    python scripts/build_cards.py             real data (data/contributions.json) -> cards/
    python scripts/build_cards.py --sample    synthetic data, for a local look only
    STATIC=1 python scripts/build_cards.py    final frame, no animation -> cards-static/
                                              (+ preview.html laid out like the README)

Needs: fonttools, brotli (always) and pillow (only if assets/portrait.* exists).

Every card is used through <img>, so each SVG carries everything it needs:
inline <style> with CSS keyframes, SMIL <animate> elements, and Google Sans
subset to the glyphs that card actually uses, embedded as base64 WOFF2.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# --------------------------------------------------------------------------
# Content. Edit this block, not the drawing code.
# --------------------------------------------------------------------------
NAME = "Jamiel J."
KICKER = "FINANCIAL DATA ANALYST"
ABOUT = (
    "Financial data analyst in Tamil Nadu, India. I build credit-risk models, "
    "fraud detection and driver forecasts, plus a natural-language-to-SQL "
    "analytics platform."
)
INITIALS = "JJ"  # shown when assets/portrait.(jpg|jpeg|png|webp) does not exist

TILES = [
    dict(slug="tile-portfolio", title="Portfolio", sub="jamiel-j.me", icon="globe"),
    dict(slug="tile-linkedin", title="LinkedIn", sub="in/jamiel-j-856ab9329", icon="in"),
    dict(slug="tile-email", title="Email", sub="jahirjamiel@gmail.com", icon="mail"),
]

REPOS = [
    dict(
        slug="repo-vizzy-analytics",
        tag="FLAGSHIP",
        title="Vizzy Analytics",
        metric="104 ms",
        metric_label="p95 query latency on 1M rows",
        metric_note="3.34x faster than pandas",
        desc=(
            "Plain-English questions in, validated SQL, charts and insights out. "
            "SQLGlot blocks unsafe SQL before DuckDB runs it."
        ),
        stack=["FastAPI", "DuckDB", "React 19", "SQLGlot", "Groq"],
    ),
    dict(
        slug="repo-fraud-detection",
        tag="FRAUD ANALYTICS",
        title="Fraud Detection Engine",
        metric="99.76%",
        metric_label="recall on fraudulent claims",
        metric_note="0.9993 ROC-AUC via LightGBM",
        desc=(
            "Cost-sensitive threshold tuning with SMOTE, built to minimise missed "
            "fraud over raw accuracy."
        ),
        stack=["Python", "LightGBM", "Scikit-Learn", "SMOTE"],
    ),
    dict(
        slug="repo-demand-forecasting",
        tag="FORECASTING",
        title="Demand Forecasting",
        metric="4.01%",
        metric_label="WAPE across 45 retail stores",
        metric_note="31.7% lift vs baseline",
        desc=(
            "Inventory optimisation across 45 stores, comparing Prophet, SARIMAX "
            "and quantile regression."
        ),
        stack=["Python", "Prophet", "SARIMAX", "Streamlit"],
    ),
    dict(
        slug="repo-revenue-funnel",
        tag="REVENUE ANALYTICS",
        title="Revenue Funnel Analysis",
        metric="$1.14M",
        metric_label="annualised leakage isolated",
        metric_note="across checkout and cart funnels",
        desc=(
            "Multi-stage drop-off analysis across cart, checkout, payment and "
            "purchase, quantifying revenue lost."
        ),
        stack=["Python", "Pandas", "SQL", "Plotly"],
    ),
    dict(
        slug="repo-jpmc-nii",
        tag="BANKING",
        title="JPMC NII & Deposit-Beta Attribution",
        metric="0.53 / 0.26",
        metric_label="down-beta vs up-beta",
        metric_note="18 quarters, 2022 to 2026",
        desc=(
            "Net interest income broken into deposit-beta effects, verified against "
            "SEC EDGAR and FRED."
        ),
        stack=["Python", "SEC EDGAR", "FRED"],
    ),
]

# Palette, 60 / 30 / 10.
OAT = "#F0E8D6"      # 60  oat milk
FOREST = "#1F4B35"   # 30  forest green
TOMATO = "#D8402B"   # 10  tomato red

# Seconds. The page should play top to bottom, so each card starts after the one above.
T = dict(hero=0.0, tile=0.55, tile_step=0.14, chart=1.2, repo=1.8, repo_step=0.28, graph=4.0)

W = 830  # README content width the cards are designed for

DATA_JSON = ROOT / "data" / "contributions.json"
FONT_FILES = {
    ("sans", 400, "normal"): HERE / "fonts" / "google-sans-latin-400-normal.woff2",
    ("sans", 600, "normal"): HERE / "fonts" / "google-sans-latin-600-normal.woff2",
    ("sans", 700, "normal"): HERE / "fonts" / "google-sans-latin-700-normal.woff2",
    ("serif", 400, "normal"): HERE / "fonts" / "instrument-serif-latin-400-normal.woff2",
    ("serif", 400, "italic"): HERE / "fonts" / "instrument-serif-latin-400-italic.woff2",
}

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
ANIMATE = True  # set to False by STATIC=1


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a: str, b: str, t: float) -> str:
    """Solid colour t of the way from a to b."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


OAT_DEEP = mix(OAT, FOREST, 0.10)      # empty heat cells, grid lines
MUTED = mix(FOREST, OAT, 0.30)         # secondary text on oat
ON_FOREST = mix(FOREST, OAT, 0.74)     # secondary text on forest
RULE = mix(FOREST, OAT, 0.25)          # divider on forest


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_date(d: dt.date) -> str:
    return f"{d:%b} {d.day}, {d.year}"  # no %-d, it breaks on Windows


def nice_ceil(v: float) -> int:
    if v <= 5:
        return 5
    mag = 10 ** math.floor(math.log10(v))
    for k in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if k * mag >= v:
            return int(math.ceil(k * mag))
    return int(10 * mag)


# --------------------------------------------------------------------------
# Fonts: measure with the full font, embed a per-card subset
# --------------------------------------------------------------------------
class Fonts:
    """Two families (Google Sans for UI, Instrument Serif for display), subset per card.
    A face key is (family, weight, style)."""

    def __init__(self):
        self.tt, self.cmap, self.hmtx = {}, {}, {}
        for key, p in FONT_FILES.items():
            if not p.exists():
                sys.exit(f"missing font file: {p}")
            f = TTFont(p)
            self.tt[key] = f
            self.cmap[key] = f.getBestCmap()
            self.hmtx[key] = f["hmtx"]
        self.upem = next(iter(self.tt.values()))["head"].unitsPerEm
        self._cache: dict = {}

    def width(self, s: str, weight: int, size: float, ls: float = 0.0,
              fam: str = "sans", style: str = "normal") -> float:
        cm, hm = self.cmap[(fam, weight, style)], self.hmtx[(fam, weight, style)]
        total = 0
        for ch in s:
            g = cm.get(ord(ch))
            total += hm[g][0] if g else self.upem * 0.5
        return total * size / self.upem + ls * len(s)

    def fit(self, s, weight, size, maxw, minsize=9.0, ls=0.0,
            fam: str = "sans", style: str = "normal") -> float:
        while self.width(s, weight, size, ls, fam, style) > maxw and size > minsize:
            size -= 0.5
        return size

    def wrap(self, s, weight, size, maxw, ls=0.0,
             fam: str = "sans", style: str = "normal") -> list[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if cur and self.width(trial, weight, size, ls, fam, style) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    def missing(self, chars: set, weight: int, fam: str = "sans", style: str = "normal") -> set:
        cm = self.cmap[(fam, weight, style)]
        return {c for c in chars if ord(c) not in cm and not c.isspace()}

    def subset_b64(self, weight: int, chars: set, fam: str = "sans", style: str = "normal") -> str:
        key = (fam, weight, style, "".join(sorted(chars)))
        if key in self._cache:
            return self._cache[key]
        with tempfile.TemporaryDirectory() as td:
            tf, out = Path(td) / "t.txt", Path(td) / "o.woff2"
            tf.write_text("".join(sorted(chars)) + " ", encoding="utf-8")
            cmd = [
                sys.executable, "-m", "fontTools.subset", str(FONT_FILES[(fam, weight, style)]),
                f"--text-file={tf}", "--flavor=woff2", f"--output-file={out}",
                "--layout-features=kern,liga", "--no-hinting",
                "--no-recalc-timestamp",  # keeps output byte-stable so unchanged data means no commit
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            b64 = base64.b64encode(out.read_bytes()).decode("ascii")
        self._cache[key] = b64
        return b64


FONTS: Fonts  # created in main()


# --------------------------------------------------------------------------
# Card: collects SVG, tracks the glyphs used, wraps everything in <svg>
# --------------------------------------------------------------------------
ANIM_CSS = """
@keyframes fade{from{opacity:0}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}}
@keyframes pop{from{opacity:0;transform:scale(.35)}}
@keyframes grow{from{transform:scaleY(0)}}
@keyframes draw{from{stroke-dashoffset:1}}
@keyframes sweep{from{transform:translateX(-160px)}to{transform:translateX(900px)}}
@keyframes wave{0%,100%{opacity:1}50%{opacity:.68}}
.fade{animation:fade .9s ease-out backwards}
.sweep{animation:sweep 7s linear infinite;will-change:transform}
.wave{animation:wave 3.4s ease-in-out infinite}
.rise,.col{animation:rise .75s cubic-bezier(.22,.8,.24,1) backwards}
.pop{animation:pop .7s cubic-bezier(.3,1.4,.5,1) backwards;transform-box:fill-box;transform-origin:50% 50%}
.grow{animation:grow .85s cubic-bezier(.22,.8,.24,1) backwards;transform-box:fill-box;transform-origin:50% 100%}
.draw{stroke-dasharray:1;animation:draw .9s ease-out backwards}
.s{display:none}
@media (prefers-reduced-motion:reduce){
*{animation:none!important}
.m{display:none}
.s{display:inline}
}
"""


class Card:
    def __init__(self, slug: str, w: float, h: float, base: float, title: str, desc: str = "",
                 radius: float = 20):
        self.slug, self.w, self.h, self.base = slug, w, h, base
        self.title, self.desc = title, desc
        self.radius = radius
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.chars: dict = {}

    def glyphs(self, fam: str, weight: int, style: str) -> set:
        return self.chars.setdefault((fam, weight, style), set())

    # -- animation plumbing ------------------------------------------------
    def a(self, kind: str | None = None, delay: float = 0.0) -> str:
        """class + delay attributes for a CSS-keyframe entrance."""
        if not ANIMATE or not kind:
            return ""
        return f' class="{kind}" style="animation-delay:{self.base + delay:.2f}s"'

    def t0(self, delay: float) -> str:
        """Absolute SMIL begin time (seconds) for something that should start at base+delay."""
        return f"{self.base + delay:.2f}s"

    def smil(self, static: str, motion: str) -> str:
        """SMIL cannot be switched off from CSS, so keep a still copy and swap them
        under prefers-reduced-motion. In STATIC mode only the still copy is emitted."""
        if not ANIMATE:
            return static
        return f'<g class="m">{motion}</g><g class="s">{static}</g>'

    # -- drawing -----------------------------------------------------------
    def add(self, svg: str):
        self.parts.append(svg)

    def text(self, x, y, s, size, weight=400, fill=FOREST, anchor="start", ls=0.0,
             kind=None, delay=0.0, fam="sans", style="normal"):
        self.glyphs(fam, weight, style).update(s)
        attrs = f'x="{x:g}" y="{y:g}" font-size="{size:g}" font-weight="{weight}" fill="{fill}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if ls:
            attrs += f' letter-spacing="{ls:g}"'
        classes = []
        if fam == "serif":
            classes.append("serif")
        if style == "italic":
            classes.append("italic")
        if kind:
            classes.append(kind)
        if classes:
            attrs += f' class="{" ".join(classes)}"'
        if ANIMATE and kind:
            attrs += f' style="animation-delay:{self.base + delay:.2f}s"'
        self.add(f"<text {attrs}>{escape(s)}</text>")

    def render(self) -> str:
        family_name = {"sans": "GSE", "serif": "GSESerif"}
        family_stack = {
            "sans": 'GSE,"Google Sans",system-ui,sans-serif',
            "serif": 'GSESerif,"Instrument Serif",Georgia,serif',
        }
        faces = []
        for (fam, wgt, style), chars in self.chars.items():
            if not chars:
                continue
            bad = FONTS.missing(chars, wgt, fam, style)
            if bad:
                print(f"  warning: {self.slug}: glyphs missing from {fam} {wgt} {style}: {''.join(sorted(bad))}")
            faces.append(
                "@font-face{font-family:%s;font-style:%s;font-weight:%d;"
                "src:url(data:font/woff2;base64,%s) format('woff2')}"
                % (family_name[fam], style, wgt, FONTS.subset_b64(wgt, chars, fam, style))
            )
        css = "".join(faces)
        css += 'text{font-family:%s;text-rendering:geometricPrecision}' % family_stack["sans"]
        css += 'text.serif{font-family:%s}' % family_stack["serif"]
        css += 'text.italic{font-style:italic}'
        if ANIMATE:
            css += ANIM_CSS
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:g} {self.h:g}" '
            f'width="{self.w:g}" height="{self.h:g}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(self.title)}</title><desc id="d">{escape(self.desc or self.title)}</desc>'
            f"<style>{css}</style>"
            f'<defs><clipPath id="card"><rect width="{self.w:g}" height="{self.h:g}" rx="{self.radius:g}"/></clipPath>'
            f'{"".join(self.defs)}</defs>'
            f'<g clip-path="url(#card)">{"".join(self.parts)}</g></svg>'
        )


def arrow_up_right(c: Card, cx: float, cy: float, s: float, stroke: str, begin_delay: float,
                   width: float = 3.0) -> str:
    """Up-right arrow centred on (cx, cy), `s` px across. One-shot SMIL hop on load."""
    h = s / 2
    d = (f"M{cx - h:g} {cy + h:g}L{cx + h:g} {cy - h:g}"
         f"M{cx - h * 0.1:g} {cy - h:g}H{cx + h:g}V{cy + h * 0.1:g}")
    path = (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width:g}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    motion = (
        f'<g><animateTransform attributeName="transform" type="translate" from="-9 9" to="0 0" '
        f'begin="{c.t0(begin_delay)}" dur=".55s" fill="freeze" calcMode="spline" '
        f'keySplines=".22 .8 .24 1" keyTimes="0;1"/>{path}</g>'
    )
    return c.smil(path, motion)


def arrow_nudge(c: Card, cx: float, cy: float, s: float, stroke: str,
                begin_delay: float, width: float = 2.4) -> str:
    """Looping arrow drift. The still copy is used under reduced motion."""
    h = s / 2
    d = (f"M{cx - h:g} {cy + h:g}L{cx + h:g} {cy - h:g}"
         f"M{cx - h * 0.1:g} {cy - h:g}H{cx + h:g}V{cy + h * 0.1:g}")
    path = (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width:g}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    motion = (
        f'<g><animateTransform attributeName="transform" type="translate" '
        f'values="0 0;4 -4;0 0" dur="2.8s" begin="{c.t0(begin_delay)}" '
        f'repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" '
        f'keySplines=".4 0 .6 1;.4 0 .6 1"/>{path}</g>'
    )
    return c.smil(path, motion)


def sweep_layer(c: Card, x: float, y: float, w: float, h: float, clip_id: str,
                duration: float, delay: float) -> str:
    """A visible band with a leading edge travelling across a region.
    Hidden entirely under reduced motion."""
    c.defs.append(
        '<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{FOREST}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{FOREST}" stop-opacity=".18"/>'
        f'<stop offset="1" stop-color="{FOREST}" stop-opacity="0"/>'
        '</linearGradient>'
        f'<clipPath id="{clip_id}"><rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"/></clipPath>'
    )
    layer = (
        f'<g clip-path="url(#{clip_id})"><g class="sweep" '
        f'style="animation-duration:{duration:g}s;animation-delay:{delay:g}s">'
        f'<rect x="{x:g}" y="{y:g}" width="140" height="{h:g}" fill="url(#sweep)"/>'
        f'<rect x="{x + 70:g}" y="{y:g}" width="1.5" height="{h:g}" '
        f'fill="{FOREST}" opacity=".26"/>'
        f'</g></g>'
    )
    return c.smil("", layer)


def pulse_ring(c: Card, cx: float, cy: float, r0: float, r1: float, stroke: str,
               begin_delay: float, dur: float = 2.6, width: float = 2.0) -> str:
    """Looping SMIL ring. Nothing for the still copy."""
    ring = (
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r0:g}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width:g}" opacity="0">'
        f'<animate attributeName="r" values="{r0:g};{r1:g}" dur="{dur}s" begin="{c.t0(begin_delay)}" '
        f'repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".9;0" dur="{dur}s" begin="{c.t0(begin_delay)}" '
        f'repeatCount="indefinite"/></circle>'
    )
    return c.smil("", ring)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load_days(path: Path):
    if not path.exists():
        sys.exit(
            f"{path} not found. Run the 'cards' workflow once (Actions tab, Run workflow), "
            "or pass --sample for a local look with fake data."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    days = sorted((dt.date.fromisoformat(d["date"]), int(d["count"])) for d in raw["days"])
    if len(days) < 30:
        sys.exit(f"{path} has only {len(days)} days, refusing to render from that.")
    return days


def sample_days(n: int = 365):
    rnd = random.Random(7)
    end = dt.date.today()
    out = []
    for i in range(n):
        d = end - dt.timedelta(days=n - 1 - i)
        base = 0.0 if rnd.random() < 0.34 else rnd.choice([1, 1, 2, 3, 4, 6, 9])
        if d.weekday() >= 5:
            base *= 0.35
        phase = 1.0 + 0.7 * math.sin(i / 38.0)
        out.append((d, int(round(base * phase))))
    out[-1] = (out[-1][0], 3)
    for k in range(1, 9):  # a live streak at the end
        out[-1 - k] = (out[-1 - k][0], max(1, out[-1 - k][1]))
    out[200] = (out[200][0], 27)
    return out


def streaks(counts: list[int]):
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today not done yet does not break the streak
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


def month_start(d: dt.date, back: int) -> dt.date:
    idx = d.year * 12 + (d.month - 1) - back
    return dt.date(idx // 12, idx % 12 + 1, 1)


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------
def portrait_data_uri() -> str | None:
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ROOT / "assets" / f"portrait.{ext}"
        if p.exists():
            from PIL import Image  # only needed when a portrait exists

            im = Image.open(p).convert("RGB")
            s = min(im.size)
            l, t = (im.width - s) // 2, (im.height - s) // 2
            im = im.crop((l, t, l + s, t + s)).resize((340, 340), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=84, optimize=True)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return None


def build_hero() -> Card:
    H = 390
    PX = 588  # forest panel; the portrait overlaps its left edge
    c = Card("hero", W, H, T["hero"], f"{NAME}, {KICKER.lower()}", ABOUT)
    c.add(f'<rect width="{W}" height="{H}" fill="{OAT}"/>')
    c.add(f'<rect x="{PX}" width="{W - PX}" height="{H}" fill="{FOREST}"{c.a("fade", .05)}/>')

    pcx, pcy, pr = 612, 180, 76
    c.add(f'<circle cx="{pcx - 34}" cy="{pcy + 32}" r="80" fill="{TOMATO}"{c.a("pop", .35)}/>')
    uri = portrait_data_uri()
    if uri:
        c.defs.append(f'<clipPath id="pc"><circle cx="{pcx}" cy="{pcy}" r="{pr}"/></clipPath>')
        c.add(
            f'<g{c.a("pop", .5)}><circle cx="{pcx}" cy="{pcy}" r="{pr + 5}" fill="none" '
            f'stroke="{OAT}" stroke-width="1.5"/>'
            f'<image href="{uri}" x="{pcx - pr}" y="{pcy - pr}" width="{pr * 2}" height="{pr * 2}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#pc)"/></g>'
        )
    else:
        c.add(f'<circle cx="{pcx}" cy="{pcy}" r="{pr}" fill="{OAT}"{c.a("pop", .5)}/>')
        c.add(f'<circle cx="{pcx}" cy="{pcy}" r="{pr + 5}" fill="none" stroke="{OAT}" '
              f'stroke-width="1.5"{c.a("fade", .62)}/>')
        c.text(pcx, pcy + 17, INITIALS, 50, 400, FOREST, anchor="middle", kind="pop", delay=.66,
               fam="serif", style="italic")
    c.add(pulse_ring(c, pcx, pcy, pr + 5, pr + 28, OAT, 1.5, dur=3.2))

    # the tagline lives in the forest panel, under the portrait
    c.add(f'<path d="M620 304V360" stroke="{RULE}" stroke-width="1"{c.a("fade", .3)}/>')
    for i, line in enumerate(FONTS.wrap("Turning messy data into defensible decisions.",
                                        400, 16, 172, fam="serif", style="italic")):
        c.text(636, 310 + i * 22, line, 16, 400, OAT, kind="rise", delay=.5 + i * .1,
               fam="serif", style="italic")

    c.add(f'<rect x="40" y="60" width="36" height="4" rx="2" fill="{TOMATO}"{c.a("rise", .1)}/>')
    c.text(40, 84, KICKER, 12, 700, FOREST, ls=2.6, kind="rise", delay=.12)
    # the name is one line: "Jamiel" in forest, "J." in tomato italic
    nw = FONTS.width("Jamiel", 400, 124, -2, "serif")
    c.text(32, 240, "Jamiel", 124, 400, FOREST, ls=-2, kind="rise", delay=.22, fam="serif")
    c.text(32 + nw + 12, 240, "J.", 124, 400, TOMATO, ls=-2, kind="rise", delay=.34,
           fam="serif", style="italic")
    c.add(f'<path d="M40 284H500" stroke="{RULE}" stroke-width="1"{c.a("fade", .4)}/>')
    for i, line in enumerate(FONTS.wrap(ABOUT, 400, 15, 480)):
        c.text(40, 312 + i * 22, line, 15, 400, MUTED, kind="rise", delay=.5 + i * .12)
    return c


def build_tile(i: int, t: dict) -> Card:
    TW, TH = 270, 112
    c = Card(t["slug"], TW, TH, T["tile"] + T["tile_step"] * i, f'{t["title"]}: {t["sub"]}')
    c.add(f'<rect width="{TW}" height="{TH}" fill="{OAT}"/>')
    c.add(f'<rect x="20" y="24" width="28" height="3" fill="{TOMATO}"{c.a("rise", .08)}/>')
    bx, by, bs = 20, 42, 36
    c.add(f'<rect x="{bx}" y="{by}" width="{bs}" height="{bs}" rx="10" fill="{FOREST}"{c.a("pop", .1)}/>')
    cx, cy = bx + bs / 2, by + bs / 2
    st = f'fill="none" stroke="{OAT}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
    if t["icon"] == "globe":
        c.add(f'<g{c.a("fade", .3)}><circle cx="{cx}" cy="{cy}" r="9.5" {st}/>'
              f'<ellipse cx="{cx}" cy="{cy}" rx="4" ry="9.5" {st}/>'
              f'<path d="M{cx - 9.5} {cy}H{cx + 9.5}" {st}/></g>')
    elif t["icon"] == "mail":
        c.add(f'<g{c.a("fade", .3)}><rect x="{cx - 10.5}" y="{cy - 7.5}" width="21" height="15" rx="4" {st}/>'
              f'<path d="M{cx - 9.5} {cy - 5}L{cx} {cy + 2.5}L{cx + 9.5} {cy - 5}" {st}/></g>')
    else:
        c.text(cx, cy + 6.5, "in", 18, 700, OAT, anchor="middle", kind="fade", delay=.3)
    c.text(70, 65, t["title"], 20, 400, FOREST, kind="rise", delay=.18, fam="serif")
    size = FONTS.fit(t["sub"], 400, 12, TW - 70 - 16)
    c.text(70, 87, t["sub"], size, 400, MUTED, kind="rise", delay=.26)
    c.add(arrow_up_right(c, 240, 88, 12, TOMATO, .42, width=2))
    return c


def month_buckets(days):
    last = days[-1][0]
    start = month_start(last, 11)
    months = [month_start(last, 11 - k) for k in range(12)]
    sums = {m: 0 for m in months}
    for d, n in days:
        if d >= start:
            sums[dt.date(d.year, d.month, 1)] += n
    return months, [sums[m] for m in months], start, last


def build_chart(days) -> Card:
    H = 364
    months, vals, start, last = month_buckets(days)
    window = [(d, n) for d, n in days if d >= start]
    total = sum(n for _, n in window)
    counts_all = [n for _, n in days]
    cur_streak, best_streak = streaks(counts_all)
    active = sum(1 for n in counts_all if n > 0)
    busiest_day, busiest_n = max(days, key=lambda x: (x[1], x[0]))

    c = Card("chart-monthly", W, H, T["chart"], "Contributions per month",
             f"Bar chart of contributions per month, {months[0]:%b %Y} to {months[-1]:%b %Y}.")
    c.add(f'<rect width="{W}" height="{H}" fill="{OAT}"/>')
    c.text(40, 54, "Contributions per month", 22, 400, FOREST, kind="rise", delay=0, fam="serif")
    c.text(40, 74, f"{months[0]:%b %Y} to {months[-1]:%b %Y}, {fmt_int(total)} contributions. "
                   f"The latest month is still running.", 12, 400, MUTED, kind="rise", delay=.08)
    c.add(f'<path d="M40 88H{W - 40}" stroke="{RULE}" stroke-width="1"{c.a("fade", .2)}/>')

    x0, x1, base, top = 64, W - 64, 240, 116
    ymax = nice_ceil(max(vals) or 1)
    band = (x1 - x0) / 12
    bw = 30
    grid = []
    for frac in (0, .5, 1):
        y = base - (base - top) * frac
        grid.append(f'<path d="M{x0 - 8} {y:g}H{x1 + 8}" stroke="{OAT_DEEP if frac else mix(OAT, FOREST, .28)}" '
                    f'stroke-width="{1.2 if frac else 1.6}"/>')
        c.glyphs("sans", 400, "normal").update(str(int(ymax * frac)))
        grid.append(f'<text x="{x0 - 14}" y="{y + 4:g}" font-size="11" font-weight="400" fill="{MUTED}" '
                    f'text-anchor="end">{int(ymax * frac)}</text>')
    c.add(f"<g{c.a('fade', .15)}>{''.join(grid)}</g>")

    peak = vals.index(max(vals))
    for k, (m, v) in enumerate(zip(months, vals)):
        bx = x0 + band * k + (band - bw) / 2
        h = (base - top) * v / ymax
        by = base - h
        fill = TOMATO if (k == peak and v > 0) else FOREST
        d = .3 + .07 * k
        if v > 0:
            c.add(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{h:.1f}" rx="4" fill="{fill}"{c.a("grow", d)}/>')
        is_last = k == 11
        ly = by - (24 if is_last else 8)
        c.text(bx + bw / 2, ly, str(v), 11, 600, FOREST, anchor="middle", kind="fade", delay=d + .55)
        c.text(bx + bw / 2, base + 22, f"{m:%b}", 11, 600 if is_last else 400, FOREST if is_last else MUTED,
               anchor="middle", kind="fade", delay=.2 + .04 * k)
        if k == 0 or m.month == 1:
            c.text(bx + bw / 2, base + 36, str(m.year), 10, 400, MUTED, anchor="middle", kind="fade", delay=.3)
        if is_last:
            dx, dy = bx + bw / 2, by - 10
            c.add(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3.5" fill="{TOMATO}"{c.a("pop", d + .7)}/>')
            c.add(pulse_ring(c, dx, dy, 3.5, 13, TOMATO, d + 1.0))

    c.add(sweep_layer(c, 40, 100, 750, 150, "barsclip", 8.0, 2.0))

    # stat strip across the foot of the card, divided by hairlines
    cols = [64, 310, 556]
    c.add(f'<path d="M40 294H{W - 40}" stroke="{RULE}" stroke-width="1"{c.a("fade", .3)}/>')
    for x in (287, 533):
        c.add(f'<path d="M{x} 300V340" stroke="{RULE}" stroke-width="1"{c.a("fade", .35)}/>')
    rows = [
        ("CURRENT STREAK", str(cur_streak), "days" if cur_streak != 1 else "day",
         f"Longest: {best_streak} {'days' if best_streak != 1 else 'day'}"),
        ("ACTIVE DAYS", str(active), f"of {len(days)} days", ""),
        ("BUSIEST DAY", str(busiest_n), "contributions", fmt_date(busiest_day)),
    ]
    for k, (label, value, unit, sub) in enumerate(rows):
        x = cols[k]
        d = .5 + .12 * k
        c.text(x, 312, label, 10, 700, MUTED, ls=1.2, kind="rise", delay=d)
        c.text(x, 336, value, 26, 400, FOREST, kind="rise", delay=d + .06, fam="serif")
        vw = FONTS.width(value, 400, 26, 0.0, "serif")
        c.text(x + vw + 6, 336, unit, 11, 400, MUTED, kind="rise", delay=d + .1)
        if sub:
            c.text(x, 352, sub, 10, 400, MUTED, kind="rise", delay=d + .14)
    return c


def build_repo(i: int, r: dict) -> Card:
    """One row of the featured-work index. Rows are square and stack flush."""
    H = 156
    c = Card(r["slug"], W, H, T["repo"] + T["repo_step"] * i,
             f'{r["title"]}: {r["metric"]} {r["metric_label"]}', r["desc"], radius=0)
    c.add(f'<rect width="{W}" height="{H}" fill="{OAT}"/>')
    c.add(f'<path d="M0 0.5H{W}" stroke="{RULE}" stroke-width="1"{c.a("fade", .05)}/>')

    px = 40
    c.text(px, 80, r["metric"], FONTS.fit(r["metric"], 400, 34, 190, fam="serif"), 400, FOREST,
           kind="rise", delay=.12, fam="serif")
    c.text(px, 106, r["metric_label"], 10.5, 400, MUTED, kind="rise", delay=.2)
    if r.get("metric_note"):
        c.text(px, 122, r["metric_note"], 10.5, 600, FOREST, kind="rise", delay=.26)

    c.add(f'<path d="M250 24V136" stroke="{RULE}" stroke-width="1"{c.a("fade", .15)}/>')

    mx, mw = 282, 470
    c.text(mx, 56, r["title"], FONTS.fit(r["title"], 400, 22, mw, fam="serif"), 400, FOREST,
           kind="rise", delay=.16, fam="serif")
    desc = FONTS.wrap(r["desc"], 400, 13, mw)
    if len(desc) > 2:
        sys.exit(f"{r['slug']}: description wraps to {len(desc)} lines, max is 2. Shorten it.")
    for k, ln in enumerate(desc):
        c.text(mx, 82 + 19 * k, ln, 13, 400, MUTED, kind="rise", delay=.26 + .07 * k)

    x = mx
    for k, chip in enumerate(r["stack"]):
        cw = FONTS.width(chip, 600, 10.5) + 20
        if x + cw > mx + mw:
            break
        c.add(f'<g{c.a("rise", .4 + .05 * k)}><rect x="{x:.1f}" y="112" width="{cw:.1f}" height="20" rx="10" '
              f'fill="none" stroke="{FOREST}" stroke-width="1.3"/></g>')
        c.text(x + cw / 2, 126, chip, 10.5, 600, FOREST, anchor="middle", kind="rise", delay=.4 + .05 * k)
        x += cw + 7

    c.add(arrow_nudge(c, W - 40, 72, 18, TOMATO, .45))
    return c


def build_graph(days) -> Card:
    H = 250
    total = sum(n for _, n in days)
    c = Card("contribution-graph", W, H, T["graph"], "Contribution graph",
             f"Daily contribution heatmap, {days[0][0]:%b %Y} to {days[-1][0]:%b %Y}.")
    c.add(f'<rect width="{W}" height="{H}" fill="{OAT}"/>')
    c.text(40, 54, "Contribution graph", 22, 400, FOREST, kind="rise", delay=0, fam="serif")
    c.text(40, 74, f"{fmt_int(total)} contributions, {fmt_date(days[0][0])} to {fmt_date(days[-1][0])}",
           12, 400, MUTED, kind="rise", delay=.08)
    c.add(f'<path d="M40 90H{W - 40}" stroke="{RULE}" stroke-width="1"{c.a("fade", .2)}/>')

    nz = sorted(n for _, n in days if n > 0)
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]
    shades = [OAT_DEEP] + [mix(OAT_DEEP, FOREST, t) for t in (.34, .58, .8, 1.0)]

    def level(n):
        return 0 if n == 0 else 1 if n <= q[0] else 2 if n <= q[1] else 3 if n <= q[2] else 4

    first_wd = (days[0][0].weekday() + 1) % 7  # Sunday-first rows
    ncols = math.ceil((first_wd + len(days)) / 7)
    gx, gy = 64, 124
    pitch = min(14.0, (W - gx - 40 + 3) / ncols)
    cell = pitch - 3.5

    # legend, right aligned in the header
    lx = W - 40
    c.text(lx, 74, "More", 11, 400, MUTED, anchor="end", kind="fade", delay=.2)
    sx = lx - FONTS.width("More", 400, 11) - 8 - 11
    leg = []
    for lv in range(4, -1, -1):
        leg.append(f'<rect x="{sx:.1f}" y="64" width="11" height="11" rx="4" fill="{shades[lv]}"/>')
        sx -= 14
    c.add(f"<g{c.a('fade', .2)}>{''.join(leg)}</g>")
    c.text(sx + 14 - 8, 74, "Less", 11, 400, MUTED, anchor="end", kind="fade", delay=.2)

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        c.text(40, gy + row * pitch + cell - 2, name, 9.5, 400, MUTED, kind="fade", delay=.15)

    busiest_day, busiest_n = max(days, key=lambda x: (x[1], x[0]))
    cols: dict[int, list[str]] = {}
    month_cols = []
    for idx, (d, n) in enumerate(days):
        pos = first_wd + idx
        col, row = divmod(pos, 7)
        if d.day == 1:
            month_cols.append((col, d))
        stroke = f' stroke="{TOMATO}" stroke-width="2"' if d == busiest_day and n > 0 else ""
        cols.setdefault(col, []).append(
            f'<rect x="{gx + col * pitch:.1f}" y="{gy + row * pitch:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
            f'rx="4" fill="{shades[level(n)]}"{stroke}/>'
        )
    for col in sorted(cols):
        wave = (f'<g class="wave" style="animation-delay:{(col % 5) * 0.22:.2f}s">'
                if ANIMATE else '<g>')
        c.add(f'<g{c.a("col", .25 + .013 * col)}>{wave}{"".join(cols[col])}</g></g>')
    c.add(sweep_layer(c, gx - 8, gy - 8, W - gx - 32 + 16, 7 * pitch + 16,
                      "heatclip", 11.0, 4.0))

    labelled = []
    if not month_cols or month_cols[0][0] >= 3:
        labelled.append((0, days[0][0]))
    labelled += month_cols
    for col, d in labelled:
        c.text(gx + col * pitch, gy - 9, f"{d:%b}", 10, 400, MUTED, kind="fade", delay=.3 + .013 * col)

    last_pos = first_wd + len(days) - 1
    lc, lr = divmod(last_pos, 7)
    c.add(pulse_ring(c, gx + lc * pitch + cell / 2, gy + lr * pitch + cell / 2, cell / 2 + 1, cell / 2 + 9,
                     TOMATO, .25 + .013 * lc + 1.0, dur=2.6, width=2))
    return c


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def preview_html() -> str:
    def img(name, w="100%"):
        return f'<img src="{name}.svg" width="{w}" alt="">'
    tiles = "".join(img(t["slug"], "32.5%") for t in TILES)
    repos = "".join(f'<img class="repo" src="{r["slug"]}.svg" width="100%" alt="">' for r in REPOS)
    return f"""<!doctype html><meta charset="utf-8"><title>cards preview (static)</title>
<style>body{{margin:0;background:#fff;font-family:system-ui}}main{{width:{W}px;margin:24px auto}}
p{{margin:0 0 16px;text-align:center}}p.flush{{margin:0;font-size:0;line-height:0}}img{{vertical-align:top}}
img.repo{{transition:transform .25s cubic-bezier(.22,.8,.24,1),filter .25s ease}}
img.repo:hover{{transform:translateY(-3px);filter:brightness(1.03)}}</style>
<main><p>{img('hero')}</p><p>{tiles}</p><p>{img('chart-monthly')}</p>
<p class="flush">{repos}</p><p>{img('contribution-graph')}</p></main>
"""


def main():
    global ANIMATE, FONTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true", help="final frame, no animation (same as STATIC=1)")
    ap.add_argument("--sample", action="store_true", help="use synthetic contribution data")
    ap.add_argument("--data", type=Path, default=DATA_JSON)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    static = args.static or os.environ.get("STATIC") == "1"
    ANIMATE = not static
    out = args.out or (ROOT / ("cards-static" if static else "cards"))
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()

    FONTS = Fonts()
    days = sample_days() if args.sample else load_days(args.data)

    cards = [build_hero()]
    cards += [build_tile(i, t) for i, t in enumerate(TILES)]
    cards.append(build_chart(days))
    cards += [build_repo(i, r) for i, r in enumerate(REPOS)]
    cards.append(build_graph(days))

    for card in cards:
        svg = card.render()
        (out / f"{card.slug}.svg").write_text(svg, encoding="utf-8")
        print(f"  {card.slug}.svg  {len(svg) / 1024:.1f} KB")
    if static:
        (out / "preview.html").write_text(preview_html(), encoding="utf-8")
        print(f"static frames in {out} (open preview.html and screenshot it)")
    else:
        print(f"{len(cards)} cards in {out}")


if __name__ == "__main__":
    main()
