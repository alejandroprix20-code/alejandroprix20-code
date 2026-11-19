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

# Shared layout constants, so spacing/radius decisions live in one place
# instead of being repeated as magic numbers across every render_* function.
CARD_RADIUS = 16         # corner radius on every card
SECTION_PADDING = 42     # left/right inner margin used by full-width cards
GRID_GAP = 20            # gap between same-row siblings (tiles, repo cards)
TEXT_LINE_HEIGHT = 1.5   # body-text line spacing multiplier (applied as font-size * this)

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
  <rect width="{width}" height="{height}" rx="{CARD_RADIUS}" fill="{bg}"/>
  {body}
</svg>"""


# ---------------------------------------------------------------------------
# A. Hero
# ---------------------------------------------------------------------------

def render_hero(profile: dict) -> str:
    w, h = 940, 324
    headline = profile["headline"]
    location = profile["location"]
    bio_lines = wrap_text(profile["bio"], max_chars=96)[:2]

    body = f"""
    <g {anim('f', 0.0)}>
      <rect x="{SECTION_PADDING}" y="40" width="8" height="8" rx="2" fill="{ACCENT}"/>
      <text x="{SECTION_PADDING + 18}" y="48" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">UX/UI DESIGNER · WEB DEVELOPER</text>
    </g>
    <text {anim('r', 0.12)} x="{SECTION_PADDING - 2}" y="118" font-family="{SERIF}" font-size="56" letter-spacing="-1" fill="{INK}">Alejandro</text>
    <text {anim('r', 0.26)} x="{SECTION_PADDING - 2}" y="172" font-family="{SERIF}" font-style="italic" font-size="56" letter-spacing="-1" fill="{ACCENT}">Horna Quezada</text>
    <g {anim('r', 0.45)}>
      <text x="{SECTION_PADDING}" y="206" font-family="{SANS}" font-size="16" fill="{INK_SOFT}">{esc(headline)}</text>
    </g>
    """

    y = 236
    for line in bio_lines:
        body += f'<text {anim("f", 0.6)} x="{SECTION_PADDING}" y="{y}" font-family="{SANS}" font-size="13" fill="{INK_SOFT}">{esc(line)}</text>\n'
        y += 20

    # Extra breathing room between the bio paragraph and the metadata row below it.
    footer_y = max(y + 24, h - 26)
    body += f"""
    <g {anim('f', 0.8)}>
      <line x1="{SECTION_PADDING}" y1="{footer_y - 20}" x2="{w - SECTION_PADDING}" y2="{footer_y - 20}" stroke="{LINE}" stroke-width="1"/>
      <text x="{SECTION_PADDING}" y="{footer_y}" font-family="{MONO}" font-size="12.5" fill="{INK}">@{esc(profile['github_username'])}</text>
      <text x="220" y="{footer_y}" font-family="{MONO}" font-size="12.5" fill="{INK_MUTED}">{esc(location)}</text>
    </g>
    """

    return card_shell(w, h, body, title=f"{profile['full_name']}. {headline}")


# ---------------------------------------------------------------------------
# B. Navigation tiles (solid accent blocks, à la BUILD/BRAND/LEARN)
# ---------------------------------------------------------------------------

TILE_PALETTE = [ACCENT, INK, ACCENT_MID]


def render_nav_tile(filename: str, index: int, label: str, headline: str, sub: str) -> None:
    w, h = 300, 180
    fill = TILE_PALETTE[index % len(TILE_PALETTE)]
    text_color = "#F4F3EF"

    body = f"""
    <g {anim('f', 0.1)}>
      <text x="24" y="40" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{text_color}" opacity="0.8">{esc(label)}</text>
    </g>
    <text {anim('r', 0.22)} x="22" y="100" font-family="{SERIF}" font-size="30" fill="{text_color}">{esc(headline)}</text>
    <text {anim('f', 0.4)} x="24" y="{h - 26}" font-family="{SANS}" font-size="12" fill="{text_color}" opacity="0.85">{esc(sub)}</text>
    <text {anim('f', 0.4)} x="{w - 40}" y="40" font-family="{MONO}" font-size="16" fill="{text_color}">&#8599;</text>
    """
    write_svg(filename, card_shell(w, h, body, title=f"{label}: {headline}", bg=fill))


# ---------------------------------------------------------------------------
# C. Experience
# ---------------------------------------------------------------------------

def render_experience(profile: dict) -> str:
    w = 940
    entries = profile["experience"]
    h = 130 + 92 * max(len(entries), 1)

    body = f'<text {anim("r", 0.0)} x="42" y="56" font-family="{SERIF}" font-size="30" fill="{INK}">Where I <tspan font-style="italic" fill="{ACCENT}">work</tspan></text>\n'
    body += f'<line x1="42" y1="74" x2="{w - 42}" y2="74" stroke="{LINE}" stroke-width="1"/>\n'

    y = 110
    for i, entry in enumerate(entries):
        d = 0.15 + i * 0.15
        body += f'<g {anim("f", d)}>\n'
        body += f'<circle cx="52" cy="{y + 6}" r="5" fill="{ACCENT}"/>\n'
        if i < len(entries) - 1:
            body += f'<line x1="52" y1="{y + 14}" x2="52" y2="{y + 92}" stroke="{LINE}" stroke-width="2"/>\n'
        body += f'<text x="74" y="{y + 10}" font-family="{SERIF}" font-size="19" fill="{INK}">{esc(entry["title"])}</text>\n'
        body += f'<text x="74" y="{y + 32}" font-family="{MONO}" font-size="12.5" letter-spacing="0.5" fill="{ACCENT}">{esc(entry["company"].upper())}</text>\n'
        period = f'{entry["start"]} – {entry["end"]}'
        body += f'<text x="74" y="{y + 52}" font-family="{SANS}" font-size="12.5" fill="{INK_MUTED}">{esc(period)} · {esc(entry["location"])}</text>\n'
        if entry.get("summary"):
            for j, line in enumerate(wrap_text(entry["summary"], 104)[:2]):
                body += f'<text x="74" y="{y + 72 + j * 17}" font-family="{SANS}" font-size="12" fill="{INK_SOFT}">{esc(line)}</text>\n'
        body += "</g>\n"
        y += 92

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
    rows = (len(certs) + cols - 1) // cols
    h = 160 + (len(education) * 56) + rows * 56

    body = f'<text {anim("r", 0.0)} x="42" y="56" font-family="{SERIF}" font-size="30" fill="{INK}">What I\'ve <tspan font-style="italic" fill="{ACCENT}">learned</tspan></text>\n'
    body += f'<line x1="42" y1="74" x2="{w - 42}" y2="74" stroke="{LINE}" stroke-width="1"/>\n'

    y = 102
    for i, edu in enumerate(education):
        d = 0.15 + i * 0.1
        body += f'<g {anim("f", d)}>\n'
        body += f'<text x="42" y="{y + 14}" font-family="{SERIF}" font-size="17" fill="{INK}">{esc(edu["institution"])}</text>\n'
        body += f'<text x="42" y="{y + 34}" font-family="{SANS}" font-size="12" fill="{INK_MUTED}">{esc(edu["program"])} · {esc(edu.get("period", ""))}</text>\n'
        body += "</g>\n"
        y += 56

    if education:
        y += 8

    body += f'<text x="42" y="{y}" font-family="{MONO}" font-size="11.5" letter-spacing="1.5" fill="{INK_MUTED}">CERTIFICATIONS — CODERHOUSE</text>\n'
    y += 22

    col_w = (w - 84 - 20) // cols
    for i, cert in enumerate(certs):
        col = i % cols
        row = i // cols
        cx = 42 + col * (col_w + 20)
        cy = y + row * 56
        d = 0.1 + i * 0.07
        body += f'<g {anim("f", d)}>\n'
        body += f'<rect x="{cx}" y="{cy}" width="{col_w}" height="44" rx="8" fill="{PANEL}"/>\n'
        body += f'<circle cx="{cx + 20}" cy="{cy + 22}" r="4" fill="{ACCENT}"/>\n'
        body += f'<text x="{cx + 36}" y="{cy + 19}" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{INK}">{esc(cert["name"])}</text>\n'
        status = f'Issued {cert["issued"]}'
        expires = cert.get("expires")
        if expires:
            status += f' · Expired {expires}' if _cert_expired(expires) else f' · Valid to {expires}'
        body += f'<text x="{cx + 36}" y="{cy + 35}" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">{esc(cert["issuer"])} · {esc(status)}</text>\n'
        body += "</g>\n"

    return card_shell(w, h, body, title="Education and certifications")


# ---------------------------------------------------------------------------
# E. Technical skills
# ---------------------------------------------------------------------------

def render_tech_stack(profile: dict) -> str:
    w = 940
    categories = list(profile["skills"].items())
    h = 96 + sum(54 for _ in categories)

    body = f'<text {anim("r", 0.0)} x="42" y="56" font-family="{SERIF}" font-size="30" fill="{INK}">What I <tspan font-style="italic" fill="{ACCENT}">build with</tspan></text>\n'
    body += f'<line x1="42" y1="74" x2="{w - 42}" y2="74" stroke="{LINE}" stroke-width="1"/>\n'

    y = 100
    for i, (category, skills) in enumerate(categories):
        d = 0.1 + i * 0.12
        body += f'<g {anim("f", d)}>\n'
        body += f'<text x="42" y="{y}" font-family="{MONO}" font-size="11.5" letter-spacing="1.5" fill="{ACCENT}">{esc(category.upper())}</text>\n'
        x = 42
        chip_y = y + 14
        for skill in skills:
            chip_w = 16 + len(skill) * 7.2
            if x + chip_w > w - 42:
                x = 42
                chip_y += 32
            body += f'<rect x="{x}" y="{chip_y}" width="{chip_w:.0f}" height="26" rx="13" fill="{PANEL}"/>\n'
            body += f'<text x="{x + chip_w / 2:.0f}" y="{chip_y + 17}" font-size="12" text-anchor="middle" font-family="{SANS}" fill="{INK}">{esc(skill)}</text>\n'
            x += chip_w + 10
        body += "</g>\n"
        y += 54

    return card_shell(w, h, body, title="Technical skills")


# ---------------------------------------------------------------------------
# F. GitHub contribution analytics dashboard
# ---------------------------------------------------------------------------

def render_activity(profile: dict, stats: dict) -> str:
    w, h = 940, 320
    total = stats["total_contributions"]

    body = f'<text {anim("f", 0.0)} x="42" y="46" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">THE LAST 12 MONTHS ON GITHUB</text>\n'
    body += (
        f'<text {anim("r", 0.1)} x="40" y="98" font-family="{SERIF}" font-size="46" fill="{INK}">'
        f'{total:,} <tspan font-style="italic" fill="{ACCENT}">contributions</tspan></text>\n'
    )

    tiles = [
        ("Current streak", f'{stats["current_streak"]}d'),
        ("Longest streak", f'{stats["longest_streak"]}d'),
        ("Active days", stats["active_days"]),
    ]
    tile_w, tile_x0, tile_y = 160, w - 42 - 3 * 170, 46
    for i, (label, value) in enumerate(tiles):
        x = tile_x0 + i * 170
        body += f'<g {anim("f", 0.25 + i * 0.1)}>\n'
        body += f'<text x="{x}" y="{tile_y + 22}" font-family="{SERIF}" font-size="24" fill="{INK}">{value}</text>\n'
        body += f'<text x="{x}" y="{tile_y + 40}" font-family="{MONO}" font-size="10.5" letter-spacing="1" fill="{INK_MUTED}">{esc(label.upper())}</text>\n'
        body += "</g>\n"

    monthly = stats["monthly"]
    months_sorted = sorted(monthly.keys())[-12:]
    max_val = max([monthly[m] for m in months_sorted], default=1) or 1
    peak_month = max(months_sorted, key=lambda m: monthly[m]) if months_sorted else None

    chart_x, chart_y, chart_w, chart_h = 42, 150, w - 84, 110
    bar_gap = 12
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
        body += f'<text {anim("f", d)} x="{bx + bar_w / 2:.1f}" y="{chart_y + chart_h + 22}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{INK_MUTED}">{label}</text>\n'
        if is_peak:
            body += f'<text {anim("p", d + 0.5)} x="{bx + bar_w / 2:.1f}" y="{by - 8:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{ACCENT}">{val}</text>\n'

    if stats.get("busiest_day"):
        busiest = stats["busiest_day"]
        body += (
            f'<text {anim("f", 1.2)} x="42" y="{chart_y + chart_h + 46}" font-family="{SANS}" font-size="11.5" fill="{INK_MUTED}">'
            f'Busiest day: {esc(busiest["date"])} ({busiest["count"]} contributions)</text>\n'
        )

    return card_shell(w, h, body, title=f"{total} contributions in the last 12 months")


# ---------------------------------------------------------------------------
# G. Contribution heatmap
# ---------------------------------------------------------------------------

def render_heatmap(profile: dict, stats: dict) -> str:
    w, h = 940, 210

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
    left = 46

    body = f'<text {anim("r", 0.0)} x="42" y="46" font-family="{SERIF}" font-size="28" fill="{INK}">Every day, <tspan font-style="italic" fill="{ACCENT}">in violet</tspan></text>\n'

    cur = start
    week = 0
    last_month = None
    while cur <= end:
        if cur.weekday() == 6:
            month_label = MONTH_NAMES[cur.month - 1]
            if month_label != last_month:
                x = left + week * (cell + gap)
                body += f'<text {anim("f", 0.5)} x="{x}" y="{top - 16}" font-family="{MONO}" font-size="10" fill="{INK_MUTED}">{month_label}</text>\n'
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
    legend_y = h - 24
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
    w, h = 940, 92
    body = f'<text {anim("r", 0.0)} x="42" y="54" font-family="{SERIF}" font-size="32" fill="{INK}">Featured <tspan font-style="italic" fill="{ACCENT}">Work</tspan></text>\n'
    body += f'<text {anim("f", 0.25)} x="{w - 42}" y="54" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{INK_MUTED}">WHAT I\'M BUILDING</text>\n'
    body += f'<line x1="42" y1="70" x2="{w - 42}" y2="70" stroke="{LINE}" stroke-width="1"/>\n'
    return card_shell(w, h, body, title="Featured work — what I'm building")


# ---------------------------------------------------------------------------
# I. Featured repository cards
# ---------------------------------------------------------------------------

def render_repo_card(filename: str, repo: dict) -> None:
    w, h = 300, 190

    desc_lines = wrap_text(repo.get("description") or "No description provided.", 34)[:3]

    body = f'<text {anim("r", 0.0)} x="24" y="42" font-family="{SERIF}" font-size="19" fill="{INK}">{esc(repo["name"])}</text>\n'
    y = 66
    for line in desc_lines:
        body += f'<text {anim("f", 0.2)} x="24" y="{y}" font-family="{SANS}" font-size="12" fill="{INK_SOFT}">{esc(line)}</text>\n'
        y += 18

    footer_y = h - 28
    body += f'<line x1="24" y1="{footer_y - 18}" x2="{w - 24}" y2="{footer_y - 18}" stroke="{LINE}" stroke-width="1"/>\n'
    body += f'<text {anim("f", 0.35)} x="24" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{ACCENT}">{esc(repo.get("language") or "—")}</text>\n'
    body += f'<text {anim("f", 0.35)} x="150" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">★ {repo.get("stars", 0)}</text>\n'
    body += f'<text {anim("f", 0.35)} x="210" y="{footer_y + 4}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">⑂ {repo.get("forks", 0)}</text>\n'

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

    overrides = profile.get("repo_description_overrides", {})
    for repo_name in profile.get("featured_repos", []):
        repo = dict(repos_by_name.get(repo_name, {"name": repo_name, "description": "", "language": "", "stars": 0, "forks": 0}))
        if repo_name in overrides:
            # GitHub's live API description is in Spanish for this repo; this repo's
            # actual content/purpose is unchanged, just translated for the English-only README.
            repo["description"] = overrides[repo_name]
        safe_name = repo_name.lower().replace("_", "-")
        render_repo_card(f"repo-{safe_name}.svg", repo)

    print("Done." + (" (static preview mode)" if STATIC else ""))


if __name__ == "__main__":
    main()
