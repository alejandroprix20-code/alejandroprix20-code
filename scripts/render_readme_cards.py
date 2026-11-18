#!/usr/bin/env python3
"""Generate every animated SVG card used by the GitHub profile README.

Design: "Editorial Mono" — a light, editorial look pairing a serif display
headline (italic for emphasis) with tracked-out uppercase monospace labels,
on a warm off-white card with a single violet accent. Inspired by the layout
grammar of github.com/AviVashishta29's profile cards (serif+mono pairing,
rise/fade/grow/pop reveals, accent-tinted heatmap), re-implemented from
scratch with original content, palette and animation code.

Reads:
    data/profile.json        - verified professional information
    data/contributions.json  - normalized GitHub contribution data
    data/repos.json          - cached metadata for featured repositories

Writes SVG files into cards/.

Usage:
    python scripts/render_readme_cards.py            # animated cards
    STATIC=1 python scripts/render_readme_cards.py    # fully revealed, no animation
"""
from __future__ import annotations

import base64
import datetime as dt
import functools
import json
import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CARDS_DIR = os.path.join(ROOT, "cards")
FONTS_DIR = os.path.join(ROOT, "fonts")

STATIC = os.environ.get("STATIC") == "1"

# ---------------------------------------------------------------------------
# Design tokens — "Editorial Mono"
# ---------------------------------------------------------------------------

BG = "#F4F3EF"           # warm off-white card background
INK = "#13131A"          # near-black text
INK_SOFT = "#4B4B52"     # secondary text
INK_MUTED = "#8A8A90"    # tertiary / labels
LINE = "#E1DFD7"         # hairline borders / dividers
PANEL = "#EAE8E0"        # subtle panel fill on top of BG

ACCENT = "#5B3DF5"       # violet — the personal brand accent
ACCENT_SOFT = "#C9BFFB"  # tint for low-intensity heatmap cells
ACCENT_MID = "#8E79F8"   # mid-intensity tint

SERIF = "'Instrument Serif', Georgia, 'Times New Roman', serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "'Geist', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# Shared spacing system — a consistent rhythm across every card so nothing
# feels compressed or arbitrarily positioned.
PAD = 48          # outer card padding (left/right/top safe margin)
RADIUS = 18        # card corner radius
SECTION_GAP = 26   # space between a heading/rule and the content below it

# ---------------------------------------------------------------------------
# Embedded, glyph-subsetted fonts (self-contained — no network fetch at
# render time). See fonts/LICENSE-OFL.txt: Instrument Serif and Geist/Geist
# Mono are both SIL Open Font License 1.1, which permits base64 embedding.
# These are the same families used by github.com/AviVashishta29's cards.
# ---------------------------------------------------------------------------

_FONT_FACES = [
    ("Instrument Serif", "InstrumentSerif-Regular.woff2", "normal", 400),
    ("Instrument Serif", "InstrumentSerif-Italic.woff2", "italic", 400),
    ("Geist", "Geist-400.woff2", "normal", 400),
    ("Geist", "Geist-600.woff2", "normal", 600),
    ("Geist Mono", "GeistMono-400.woff2", "normal", 400),
]


@functools.lru_cache(maxsize=None)
def _font_css() -> str:
    rules = []
    for family, fname, style, weight in _FONT_FACES:
        path = os.path.join(FONTS_DIR, fname)
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        rules.append(
            "@font-face{"
            f"font-family:'{family}';font-style:{style};font-weight:{weight};"
            f"font-display:swap;src:url(data:font/woff2;base64,{data}) format('woff2');"
            "}"
        )
    return "\n".join(rules)

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

ANIM_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.4)}70%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:none}}
.r{opacity:0;animation:rise .7s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .8s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .7s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p{animation:none!important;opacity:1!important;transform:none!important}}
"""


def esc(s: str) -> str:
    return escape(str(s))


def load_json(name: str, default=None):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_svg(filename: str, content: str) -> None:
    os.makedirs(CARDS_DIR, exist_ok=True)
    path = os.path.join(CARDS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"wrote {os.path.relpath(path, ROOT)}")


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) > max_chars:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def anim(class_name: str, delay: float) -> str:
    if STATIC:
        return ""
    return f'class="{class_name}" style="animation-delay:{delay:.2f}s"'


def card_shell(width: int, height: int, body: str, title: str, bg: str = BG) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
  <title>{esc(title)}</title>
  <style>
    {_font_css()}
    text {{ font-family: {SANS}; }}
    {ANIM_CSS}
  </style>
  <rect width="{width}" height="{height}" rx="{RADIUS}" fill="{bg}"/>
  {body}
</svg>"""


# ---------------------------------------------------------------------------
# A. Hero
# ---------------------------------------------------------------------------

def _hero_illustration(cx: float, cy: float, scale: float = 1.0) -> str:
    """Original abstract motif (overlapping interface frames) — no portrait,
    no copied assets. Reads as an editorial geometric mark, not a face."""
    s = scale
    rings = []
    radii = [108, 80, 52]
    colors = [ACCENT_SOFT, ACCENT_MID, ACCENT]
    widths = [10, 9, 8]
    for i, (r, color, sw) in enumerate(zip(radii, colors, widths)):
        d = 0.5 + i * 0.12
        rings.append(
            f'<circle {anim("p", d)} cx="{cx}" cy="{cy}" r="{r * s:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{sw}"/>'
        )
    # a small grid of corner brackets + dots suggesting a UI canvas
    frame = (
        f'<g {anim("f", 0.75)} opacity="1">'
        f'<rect x="{cx - 64*s:.1f}" y="{cy - 64*s:.1f}" width="{128*s:.1f}" height="{128*s:.1f}" '
        f'rx="{16*s:.1f}" fill="none" stroke="{INK}" stroke-width="3"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{9*s:.1f}" fill="{ACCENT}"/>'
        f'<circle cx="{cx - 36*s:.1f}" cy="{cy + 36*s:.1f}" r="{5*s:.1f}" fill="{INK}"/>'
        f'<circle cx="{cx + 34*s:.1f}" cy="{cy - 28*s:.1f}" r="{3.5*s:.1f}" fill="{INK}"/>'
        f'</g>'
    )
    return "\n".join(rings) + "\n" + frame


def render_hero(profile: dict) -> str:
    w, h = 940, 360
    headline = profile["headline"]
    location = profile["location"]
    bio_lines = wrap_text(profile["bio"], max_chars=72)[:2]

    left_w = 600
    body = f"""
    <g {anim('f', 0.0)}>
      <rect x="{PAD}" y="{PAD}" width="8" height="8" rx="2" fill="{ACCENT}"/>
      <text x="{PAD + 18}" y="{PAD + 8}" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">UX/UI DESIGNER · WEB DEVELOPER</text>
    </g>
    <text {anim('r', 0.12)} x="{PAD - 2}" y="144" font-family="{SERIF}" font-size="62" letter-spacing="-1" fill="{INK}">Alejandro</text>
    <text {anim('r', 0.26)} x="{PAD - 2}" y="204" font-family="{SERIF}" font-style="italic" font-size="62" letter-spacing="-1" fill="{ACCENT}">Horna Quezada</text>
    <g {anim('r', 0.45)}>
      <text x="{PAD}" y="240" font-family="{SANS}" font-size="16" fill="{INK_SOFT}">{esc(headline)}</text>
    </g>
    """

    y = 272
    for line in bio_lines:
        body += f'<text {anim("f", 0.6)} x="{PAD}" y="{y}" font-family="{SANS}" font-size="13.5" fill="{INK_SOFT}">{esc(line)}</text>\n'
        y += 22

    body += f"""
    <line x1="{PAD}" y1="{h - 58}" x2="{left_w}" y2="{h - 58}" stroke="{LINE}" stroke-width="1"/>
    <g {anim('f', 0.8)}>
      <text x="{PAD}" y="{h - 30}" font-family="{MONO}" font-size="12.5" fill="{INK}">@{esc(profile['github_username'])}</text>
      <text x="236" y="{h - 30}" font-family="{MONO}" font-size="12.5" fill="{INK_MUTED}">{esc(location)}</text>
    </g>
    """

    body += _hero_illustration(cx=(left_w + w - PAD) / 2, cy=h / 2, scale=1.0)

    return card_shell(w, h, body, title=f"{profile['full_name']}. {headline}")


# ---------------------------------------------------------------------------
# B. Navigation tiles (solid accent blocks, à la BUILD/BRAND/LEARN)
# ---------------------------------------------------------------------------

TILE_PALETTE = [ACCENT, INK, ACCENT_MID]


def render_nav_tile(filename: str, index: int, label: str, headline: str, sub: str) -> None:
    w, h = 300, 200
    fill = TILE_PALETTE[index % len(TILE_PALETTE)]
    text_color = "#F4F3EF"

    body = f"""
    <g {anim('f', 0.1)}>
      <text x="28" y="44" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{text_color}" opacity="0.8">{esc(label)}</text>
    </g>
    <text {anim('r', 0.22)} x="26" y="112" font-family="{SERIF}" font-size="32" fill="{text_color}">{esc(headline)}</text>
    <text {anim('f', 0.4)} x="28" y="{h - 28}" font-family="{SANS}" font-size="12" fill="{text_color}" opacity="0.85">{esc(sub)}</text>
    <text {anim('f', 0.4)} x="{w - 44}" y="44" font-family="{MONO}" font-size="16" fill="{text_color}">&#8599;</text>
    """
    write_svg(filename, card_shell(w, h, body, title=f"{label}: {headline}", bg=fill))


# ---------------------------------------------------------------------------
# C. Experience
# ---------------------------------------------------------------------------

def render_experience(profile: dict) -> str:
    w = 940
    entries = profile["experience"]
    row_h = 104
    h = 150 + row_h * max(len(entries), 1)

    body = f'<text {anim("r", 0.0)} x="{PAD}" y="58" font-family="{SERIF}" font-size="32" fill="{INK}">Where I <tspan font-style="italic" fill="{ACCENT}">work</tspan></text>\n'
    body += f'<line x1="{PAD}" y1="80" x2="{w - PAD}" y2="80" stroke="{LINE}" stroke-width="1"/>\n'

    y = 80 + SECTION_GAP
    for i, entry in enumerate(entries):
        d = 0.15 + i * 0.15
        body += f'<g {anim("f", d)}>\n'
        body += f'<circle cx="{PAD + 4}" cy="{y + 8}" r="5" fill="{ACCENT}"/>\n'
        if i < len(entries) - 1:
            body += f'<line x1="{PAD + 4}" y1="{y + 16}" x2="{PAD + 4}" y2="{y + row_h}" stroke="{LINE}" stroke-width="2"/>\n'
        tx = PAD + 28
        body += f'<text x="{tx}" y="{y + 12}" font-family="{SERIF}" font-size="21" fill="{INK}">{esc(entry["title"])}</text>\n'
        body += f'<text x="{tx}" y="{y + 36}" font-family="{MONO}" font-size="12.5" letter-spacing="0.5" fill="{ACCENT}">{esc(entry["company"].upper())}</text>\n'
        period = f'{entry["start"]} – {entry["end"]}'
        body += f'<text x="{tx}" y="{y + 58}" font-family="{SANS}" font-size="12.5" fill="{INK_MUTED}">{esc(period)} · {esc(entry["location"])}</text>\n'
        if entry.get("summary"):
            for j, line in enumerate(wrap_text(entry["summary"], 104)[:2]):
                body += f'<text x="{tx}" y="{y + 80 + j * 18}" font-family="{SANS}" font-size="12" fill="{INK_SOFT}">{esc(line)}</text>\n'
        body += "</g>\n"
        y += row_h

    return card_shell(w, h, body, title="Professional experience")


# ---------------------------------------------------------------------------
# D. Education & certifications
# ---------------------------------------------------------------------------

def _cert_expired(expires: str) -> bool:
    try:
        expiry = dt.datetime.strptime(expires, "%b %Y").replace(day=1)
    except ValueError:
        return False
    today = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return expiry < today.replace(day=1)


def render_education(profile: dict) -> str:
    w = 940
    certs = profile["certifications"]
    education = profile["education"]
    cols = 2
    cert_row_h = 64
    rows = (len(certs) + cols - 1) // cols
    h = 170 + (len(education) * 60) + rows * cert_row_h

    body = f'<text {anim("r", 0.0)} x="{PAD}" y="58" font-family="{SERIF}" font-size="32" fill="{INK}">What I\'ve <tspan font-style="italic" fill="{ACCENT}">learned</tspan></text>\n'
    body += f'<line x1="{PAD}" y1="80" x2="{w - PAD}" y2="80" stroke="{LINE}" stroke-width="1"/>\n'

    y = 80 + SECTION_GAP
    for i, edu in enumerate(education):
        d = 0.15 + i * 0.1
        body += f'<g {anim("f", d)}>\n'
        body += f'<text x="{PAD}" y="{y + 16}" font-family="{SERIF}" font-size="18" fill="{INK}">{esc(edu["institution"])}</text>\n'
        body += f'<text x="{PAD}" y="{y + 38}" font-family="{SANS}" font-size="12" fill="{INK_MUTED}">{esc(edu["program"])} · {esc(edu.get("period", ""))}</text>\n'
        body += "</g>\n"
        y += 60

    if education:
        y += 10

    body += f'<text x="{PAD}" y="{y}" font-family="{MONO}" font-size="11.5" letter-spacing="1.5" fill="{INK_MUTED}">CERTIFICATIONS — CODERHOUSE</text>\n'
    y += 26

    gutter = 24
    col_w = (w - 2 * PAD - gutter) // cols
    cert_card_h = 52
    for i, cert in enumerate(certs):
        col = i % cols
        row = i // cols
        cx = PAD + col * (col_w + gutter)
        cy = y + row * cert_row_h
        d = 0.1 + i * 0.07
        body += f'<g {anim("f", d)}>\n'
        body += f'<rect x="{cx}" y="{cy}" width="{col_w}" height="{cert_card_h}" rx="10" fill="{PANEL}"/>\n'
        body += f'<circle cx="{cx + 22}" cy="{cy + 26}" r="4" fill="{ACCENT}"/>\n'
        body += f'<text x="{cx + 40}" y="{cy + 23}" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{INK}">{esc(cert["name"])}</text>\n'
        status = f'Issued {cert["issued"]}'
        expires = cert.get("expires")
        if expires:
            status += f' · Expired {expires}' if _cert_expired(expires) else f' · Valid to {expires}'
        body += f'<text x="{cx + 40}" y="{cy + 40}" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">{esc(cert["issuer"])} · {esc(status)}</text>\n'
        body += "</g>\n"

    return card_shell(w, h, body, title="Education and certifications")


# ---------------------------------------------------------------------------
# E. Technical skills
# ---------------------------------------------------------------------------

def render_tech_stack(profile: dict) -> str:
    w = 940
    categories = list(profile["skills"].items())
    row_h = 60
    h = 110 + sum(row_h for _ in categories)

    body = f'<text {anim("r", 0.0)} x="{PAD}" y="58" font-family="{SERIF}" font-size="32" fill="{INK}">What I <tspan font-style="italic" fill="{ACCENT}">build with</tspan></text>\n'
    body += f'<line x1="{PAD}" y1="80" x2="{w - PAD}" y2="80" stroke="{LINE}" stroke-width="1"/>\n'

    y = 80 + SECTION_GAP
    for i, (category, skills) in enumerate(categories):
        d = 0.1 + i * 0.12
        body += f'<g {anim("f", d)}>\n'
        body += f'<text x="{PAD}" y="{y}" font-family="{MONO}" font-size="11.5" letter-spacing="1.5" fill="{ACCENT}">{esc(category.upper())}</text>\n'
        x = PAD
        chip_y = y + 16
        for skill in skills:
            chip_w = 20 + len(skill) * 7.4
            if x + chip_w > w - PAD:
                x = PAD
                chip_y += 34
            body += f'<rect x="{x}" y="{chip_y}" width="{chip_w:.0f}" height="28" rx="14" fill="{PANEL}"/>\n'
            body += f'<text x="{x + chip_w / 2:.0f}" y="{chip_y + 18}" font-size="12" text-anchor="middle" font-family="{SANS}" fill="{INK}">{esc(skill)}</text>\n'
            x += chip_w + 12
        body += "</g>\n"
        y += row_h

    return card_shell(w, h, body, title="Technical skills")


# ---------------------------------------------------------------------------
# F. GitHub contribution analytics dashboard
# ---------------------------------------------------------------------------

def render_activity(profile: dict, stats: dict) -> str:
    w, h = 940, 340
    total = stats["total_contributions"]

    # Two-column split: a wide left column (count + monthly chart) and a
    # narrow right column of stacked metrics, each separated by a hairline —
    # mirrors the reference's "contributions / streak / days / busiest day"
    # composition instead of cramming everything into one horizontal row.
    divider_x = 666
    right_x = divider_x + PAD

    body = f'<text {anim("f", 0.0)} x="{PAD}" y="46" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">THE LAST 12 MONTHS ON GITHUB</text>\n'
    body += (
        f'<text {anim("r", 0.1)} x="{PAD - 2}" y="98" font-family="{SERIF}" font-size="46" fill="{INK}">'
        f'{total:,} <tspan font-style="italic" fill="{ACCENT}">contributions</tspan></text>\n'
    )

    monthly = stats["monthly"]
    months_sorted = sorted(monthly.keys())[-12:]
    max_val = max([monthly[m] for m in months_sorted], default=1) or 1
    peak_month = max(months_sorted, key=lambda m: monthly[m]) if months_sorted else None

    chart_x, chart_y, chart_w, chart_h = PAD, 160, divider_x - PAD - 28, 108
    bar_gap = 10
    bar_w = (chart_w - bar_gap * (len(months_sorted) - 1)) / max(len(months_sorted), 1)

    for i, m in enumerate(months_sorted):
        val = monthly[m]
        bar_h = (val / max_val) * (chart_h - 10) if max_val else 0
        bx = chart_x + i * (bar_w + bar_gap)
        by = chart_y + chart_h - bar_h
        label = MONTH_NAMES[int(m.split("-")[1]) - 1]
        is_peak = m == peak_month and val > 0
        color = ACCENT if is_peak else INK
        d = 0.3 + i * 0.05
        body += f'<rect {anim("g", d)} x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{max(bar_h, 2):.1f}" rx="3" fill="{color}"><title>{label}: {val}</title></rect>\n'
        body += f'<text {anim("f", d)} x="{bx + bar_w / 2:.1f}" y="{chart_y + chart_h + 24}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">{label}</text>\n'
        if is_peak:
            body += f'<text {anim("p", d + 0.5)} x="{bx + bar_w / 2:.1f}" y="{by - 8:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{ACCENT}">{val}</text>\n'

    # Right column: stacked metrics with thin separators, numbers dominant.
    body += f'<line x1="{divider_x}" y1="44" x2="{divider_x}" y2="{h - 44}" stroke="{LINE}" stroke-width="1"/>\n'

    metrics = [
        (f'{stats["current_streak"]}d / {stats["longest_streak"]}d', "CURRENT STREAK, AND THE LONGEST"),
        (str(stats["active_days"]), "ACTIVE DAYS IN THE LAST YEAR"),
    ]
    if stats.get("busiest_day"):
        metrics.append((str(stats["busiest_day"]["count"]), "ON THE BUSIEST DAY"))
    else:
        metrics.append(("—", "NO BUSIEST DAY DATA YET"))

    row_h = (h - 88) / len(metrics)
    for i, (value, label) in enumerate(metrics):
        ry = 64 + i * row_h
        d = 0.35 + i * 0.12
        body += f'<g {anim("f", d)}>\n'
        body += f'<text x="{right_x}" y="{ry + 30}" font-family="{SERIF}" font-size="30" fill="{INK}">{esc(value)}</text>\n'
        body += (
            f'<text x="{right_x}" y="{ry + 52}" font-family="{SANS}" font-size="11.5" fill="{INK_MUTED}">'
            f'{esc(label.capitalize())}</text>\n'
        )
        body += "</g>\n"
        if i < len(metrics) - 1:
            sep_y = 64 + (i + 1) * row_h - 20
            body += f'<line x1="{right_x}" y1="{sep_y}" x2="{w - PAD}" y2="{sep_y}" stroke="{LINE}" stroke-width="1"/>\n'

    return card_shell(w, h, body, title=f"{total} contributions in the last 12 months")


# ---------------------------------------------------------------------------
# G. Contribution heatmap
# ---------------------------------------------------------------------------

def render_heatmap(profile: dict, stats: dict) -> str:
    w, h = 940, 230

    days = {d["date"]: d["count"] for d in stats["days"]}
    if days:
        all_dates = sorted(days.keys())
        start = dt.date.fromisoformat(all_dates[0])
        end = dt.date.fromisoformat(all_dates[-1])
    else:
        end = dt.date.today()
        start = end - dt.timedelta(days=364)

    start -= dt.timedelta(days=(start.weekday() + 1) % 7)

    counts = [v for v in days.values() if v > 0]
    max_count = max(counts) if counts else 1

    def level_color(count: int) -> str:
        if count == 0:
            return PANEL
        if count <= max_count * 0.25:
            return ACCENT_SOFT
        if count <= max_count * 0.6:
            return ACCENT_MID
        return ACCENT

    cell = 11
    gap = 3
    top = 86
    left = PAD

    body = f'<text {anim("r", 0.0)} x="{PAD}" y="44" font-family="{SERIF}" font-size="28" fill="{INK}">Every day, <tspan font-style="italic" fill="{ACCENT}">in violet</tspan></text>\n'
    body += f'<text {anim("f", 0.2)} x="{w - PAD}" y="40" text-anchor="end" font-family="{MONO}" font-size="10.5" letter-spacing="1.5" fill="{INK_MUTED}">REFRESHED DAILY</text>\n'

    cur = start
    week = 0
    last_month = None
    while cur <= end:
        if cur.weekday() == 6:
            month_label = MONTH_NAMES[cur.month - 1]
            if month_label != last_month:
                x = left + week * (cell + gap)
                body += f'<text {anim("f", 0.5)} x="{x}" y="{top - 12}" font-family="{MONO}" font-size="10" fill="{INK_MUTED}">{month_label}</text>\n'
                last_month = month_label
        day_index = (cur.weekday() + 1) % 7
        x = left + week * (cell + gap)
        y = top + day_index * (cell + gap)
        c = days.get(cur.isoformat(), 0)
        color = level_color(c)
        d = 0.5 + (week * 0.012)
        body += f'<rect {anim("p", d)} x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}"><title>{cur.isoformat()}: {c}</title></rect>\n'
        if day_index == 6:
            week += 1
        cur += dt.timedelta(days=1)

    legend_x = w - 220
    legend_y = h - 30
    legend_colors = [PANEL, ACCENT_SOFT, ACCENT_MID, ACCENT]
    body += f'<text x="{legend_x - 30}" y="{legend_y + 9}" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">Less</text>\n'
    for i, color in enumerate(legend_colors):
        body += f'<rect x="{legend_x + i * 16}" y="{legend_y}" width="11" height="11" rx="3" fill="{color}"/>\n'
    body += f'<text x="{legend_x + len(legend_colors) * 16 + 8}" y="{legend_y + 9}" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">More</text>\n'

    total = stats.get("total_contributions", 0)
    return card_shell(w, h, body, title=f"Contribution graph: {total} contributions in the last year")


# ---------------------------------------------------------------------------
# H. Editorial separator
# ---------------------------------------------------------------------------

def render_title_coding() -> str:
    w, h = 940, 100
    body = f'<text {anim("r", 0.0)} x="{PAD}" y="58" font-family="{SERIF}" font-size="34" fill="{INK}">Featured <tspan font-style="italic" fill="{ACCENT}">Work</tspan></text>\n'
    body += f'<text {anim("f", 0.25)} x="{w - PAD}" y="58" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">WHAT I\'M BUILDING</text>\n'
    body += f'<line x1="{PAD}" y1="76" x2="{w - PAD}" y2="76" stroke="{LINE}" stroke-width="1"/>\n'
    return card_shell(w, h, body, title="Featured work — what I'm building")


# ---------------------------------------------------------------------------
# I. Featured repository cards
# ---------------------------------------------------------------------------

def render_repo_card(filename: str, repo: dict) -> None:
    w, h = 300, 210

    desc_lines = wrap_text(repo.get("description") or "No description provided.", 32)[:3]

    pad = 28
    body = f'<text {anim("r", 0.0)} x="{pad}" y="46" font-family="{SERIF}" font-size="20" fill="{INK}">{esc(repo["name"])}</text>\n'
    y = 72
    for line in desc_lines:
        body += f'<text {anim("f", 0.2)} x="{pad}" y="{y}" font-family="{SANS}" font-size="12" fill="{INK_SOFT}">{esc(line)}</text>\n'
        y += 19

    footer_y = h - 32
    body += f'<line x1="{pad}" y1="{footer_y - 20}" x2="{w - pad}" y2="{footer_y - 20}" stroke="{LINE}" stroke-width="1"/>\n'
    body += f'<text {anim("f", 0.35)} x="{pad}" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{ACCENT}">{esc(repo.get("language") or "—")}</text>\n'
    body += f'<text {anim("f", 0.35)} x="{pad + 128}" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">★ {repo.get("stars", 0)}</text>\n'
    body += f'<text {anim("f", 0.35)} x="{pad + 190}" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">⑂ {repo.get("forks", 0)}</text>\n'

    write_svg(filename, card_shell(w, h, body, title=repo["name"]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    profile = load_json("profile.json")
    stats = load_json(
        "contributions.json",
        default={
            "total_contributions": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "active_days": 0,
            "busiest_day": None,
            "monthly": {},
            "days": [],
        },
    )
    repos = load_json("repos.json", default=[])
    repos_by_name = {r["name"]: r for r in repos}

    write_svg("hero.svg", render_hero(profile))
    write_svg("heatmap.svg", render_heatmap(profile, stats))
    write_svg("activity.svg", render_activity(profile, stats))

    render_nav_tile("tile-projects.svg", 0, "PROJECTS", "Explore the code", "GitHub repositories →")
    render_nav_tile("tile-skills.svg", 1, "EXPERIENCE & SKILLS", "What I build with", "Scroll down ↓")
    render_nav_tile("tile-connect.svg", 2, "CONNECT", "Let's talk", "linkedin.com/in/alejandro-horna-quezada")

    write_svg("experience.svg", render_experience(profile))
    write_svg("education.svg", render_education(profile))
    write_svg("tech-stack.svg", render_tech_stack(profile))
    write_svg("title-coding.svg", render_title_coding())

    for repo_name in profile.get("featured_repos", []):
        repo = repos_by_name.get(repo_name, {"name": repo_name, "description": "", "language": "", "stars": 0, "forks": 0})
        safe_name = repo_name.lower().replace("_", "-")
        render_repo_card(f"repo-{safe_name}.svg", repo)

    print("Done." + (" (static preview mode)" if STATIC else ""))


if __name__ == "__main__":
    main()
