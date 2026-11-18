#!/usr/bin/env python3
"""Generate every animated SVG card used by the GitHub profile README.

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

import datetime as dt
import json
import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CARDS_DIR = os.path.join(ROOT, "cards")

STATIC = os.environ.get("STATIC") == "1"

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

BG = "#0B0E14"
BG_PANEL = "#111521"
BORDER = "#242B3D"
TEXT_PRIMARY = "#E6E9F0"
TEXT_SECONDARY = "#9AA4B8"
TEXT_MUTED = "#5F6A82"
FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


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


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def base_defs(accent1: str, accent2: str) -> str:
    return f"""
    <defs>
      <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="{accent1}"/>
        <stop offset="100%" stop-color="{accent2}"/>
      </linearGradient>
      <linearGradient id="panelFade" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="{BG_PANEL}"/>
        <stop offset="100%" stop-color="{BG}"/>
      </linearGradient>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="6" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    """


def reduced_motion_css() -> str:
    return """
      @media (prefers-reduced-motion: reduce) {
        * { animation: none !important; opacity: 1 !important; transform: none !important; }
      }
    """


def reveal_css(selector_delays: list[tuple[str, float]], duration: float = 0.6) -> str:
    """Builds fade/slide-up reveal keyframes for a list of (selector, delay) pairs."""
    if STATIC:
        return ""
    rules = [
        """
        @keyframes revealUp {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        """
    ]
    for selector, delay in selector_delays:
        rules.append(
            f"""
            {selector} {{
              opacity: 0;
              animation: revealUp {duration}s ease-out forwards;
              animation-delay: {delay}s;
            }}
            """
        )
    return "\n".join(rules)


def static_opacity_override(selectors: list[str]) -> str:
    if not STATIC:
        return ""
    joined = ", ".join(selectors)
    return f"{joined} {{ opacity: 1; }}"


def card_shell(width: int, height: int, body: str, accent1: str, accent2: str, extra_css: str = "") -> str:
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>Alejandro Horna Quezada profile card</title>
  {base_defs(accent1, accent2)}
  <style>
    text {{ font-family: {FONT}; }}
    {reduced_motion_css()}
    {extra_css}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{BG}"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="none" stroke="{BORDER}" stroke-width="1.5"/>
  {body}
</svg>"""


# ---------------------------------------------------------------------------
# A. Hero
# ---------------------------------------------------------------------------

def render_hero(profile: dict) -> str:
    w, h = 940, 300
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]
    name = esc(profile["full_name"])
    username = esc(profile["github_username"])
    headline = esc(profile["headline"])
    location = esc(profile["location"])

    css = reveal_css(
        [
            (".hero-name", 0.1),
            (".hero-handle", 0.25),
            (".hero-headline", 0.4),
            (".hero-meta", 0.55),
            (".hero-bio", 0.7),
        ]
    ) + static_opacity_override([".hero-name", ".hero-handle", ".hero-headline", ".hero-meta", ".hero-bio"])

    if not STATIC:
        css += """
        @keyframes driftGlow {
          0%   { transform: translate(0px, 0px); }
          50%  { transform: translate(14px, -10px); }
          100% { transform: translate(0px, 0px); }
        }
        .glow-orb { animation: driftGlow 9s ease-in-out infinite; }
        """

    bio_lines = wrap_text(profile["bio"], max_chars=92)[:2]

    body = f"""
    <circle class="glow-orb" cx="{w - 120}" cy="80" r="160" fill="url(#accentGrad)" opacity="0.18" filter="url(#glow)"/>
    <circle class="glow-orb" cx="140" cy="{h - 40}" r="120" fill="url(#accentGrad)" opacity="0.12" filter="url(#glow)"/>

    <rect x="40" y="40" width="5" height="54" rx="2.5" fill="url(#accentGrad)"/>
    <text class="hero-name" x="62" y="70" font-size="34" font-weight="700" fill="{TEXT_PRIMARY}">{name}</text>
    <text class="hero-handle" x="62" y="96" font-size="16" font-weight="500" fill="url(#accentGrad)">@{username}</text>

    <text class="hero-headline" x="42" y="140" font-size="19" font-weight="600" fill="{TEXT_PRIMARY}">{headline}</text>

    <g class="hero-meta">
      <text x="42" y="170" font-size="13.5" fill="{TEXT_SECONDARY}">📍 {location}</text>
    </g>
    """

    y = 205
    for line in bio_lines:
        body += f'<text class="hero-bio" x="42" y="{y}" font-size="13.5" fill="{TEXT_SECONDARY}">{esc(line)}</text>\n'
        y += 22

    return card_shell(w, h, body, accent1, accent2, css)


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


# ---------------------------------------------------------------------------
# B. Navigation tiles
# ---------------------------------------------------------------------------

def render_nav_tile(filename: str, icon: str, title: str, subtitle: str, profile: dict) -> None:
    w, h = 300, 150
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]
    css = reveal_css([(".tile-title", 0.1), (".tile-sub", 0.25)]) + static_opacity_override(
        [".tile-title", ".tile-sub"]
    )
    body = f"""
    <rect x="18" y="18" width="{w - 36}" height="{h - 36}" rx="14" fill="url(#panelFade)" stroke="{BORDER}" stroke-width="1"/>
    <text x="40" y="62" font-size="26">{icon}</text>
    <text class="tile-title" x="40" y="96" font-size="17" font-weight="700" fill="{TEXT_PRIMARY}">{esc(title)}</text>
    <text class="tile-sub" x="40" y="118" font-size="12.5" fill="{TEXT_SECONDARY}">{esc(subtitle)}</text>
    <rect x="18" y="18" width="4" height="{h - 36}" rx="2" fill="url(#accentGrad)"/>
    """
    write_svg(filename, card_shell(w, h, body, accent1, accent2, css))


# ---------------------------------------------------------------------------
# C. Experience
# ---------------------------------------------------------------------------

def render_experience(profile: dict) -> str:
    w = 940
    entries = profile["experience"]
    h = 120 + 90 * max(len(entries), 1)
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]

    css = reveal_css([(f".exp-{i}", 0.15 + i * 0.15) for i in range(len(entries))]) + static_opacity_override(
        [f".exp-{i}" for i in range(len(entries))]
    )

    body = f'<text x="42" y="52" font-size="20" font-weight="700" fill="{TEXT_PRIMARY}">Professional Experience</text>\n'
    body += f'<rect x="42" y="64" width="46" height="3" rx="1.5" fill="url(#accentGrad)"/>\n'

    y = 100
    for i, entry in enumerate(entries):
        body += f'<g class="exp-{i}">\n'
        body += f'<circle cx="52" cy="{y + 8}" r="6" fill="url(#accentGrad)"/>\n'
        if i < len(entries) - 1:
            body += f'<line x1="52" y1="{y + 16}" x2="52" y2="{y + 90}" stroke="{BORDER}" stroke-width="2"/>\n'
        body += f'<text x="74" y="{y + 12}" font-size="16.5" font-weight="700" fill="{TEXT_PRIMARY}">{esc(entry["title"])}</text>\n'
        body += (
            f'<text x="74" y="{y + 34}" font-size="13.5" font-weight="600" fill="url(#accentGrad)">'
            f'{esc(entry["company"])}</text>\n'
        )
        period = f'{entry["start"]} – {entry["end"]}'
        body += f'<text x="74" y="{y + 54}" font-size="12.5" fill="{TEXT_SECONDARY}">{esc(period)} · {esc(entry["location"])}</text>\n'
        if entry.get("summary"):
            for j, line in enumerate(wrap_text(entry["summary"], 100)[:2]):
                body += f'<text x="74" y="{y + 74 + j * 18}" font-size="12.5" fill="{TEXT_MUTED}">{esc(line)}</text>\n'
        body += "</g>\n"
        y += 90

    return card_shell(w, h, body, accent1, accent2, css)


# ---------------------------------------------------------------------------
# D. Education & certifications
# ---------------------------------------------------------------------------

def render_education(profile: dict) -> str:
    w = 940
    certs = profile["certifications"]
    education = profile["education"]
    cols = 2
    rows = (len(certs) + cols - 1) // cols
    h = 150 + (len(education) * 60) + rows * 56

    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]
    css = reveal_css(
        [(f".cert-{i}", 0.1 + i * 0.08) for i in range(len(certs))]
        + [(f".edu-{i}", 0.1 + i * 0.1) for i in range(len(education))]
    ) + static_opacity_override(
        [f".cert-{i}" for i in range(len(certs))] + [f".edu-{i}" for i in range(len(education))]
    )

    body = f'<text x="42" y="52" font-size="20" font-weight="700" fill="{TEXT_PRIMARY}">Education &amp; Certifications</text>\n'
    body += '<rect x="42" y="64" width="46" height="3" rx="1.5" fill="url(#accentGrad)"/>\n'

    y = 92
    for i, edu in enumerate(education):
        body += f'<g class="edu-{i}">\n'
        body += f'<text x="42" y="{y + 16}" font-size="15" font-weight="700" fill="{TEXT_PRIMARY}">{esc(edu["institution"])}</text>\n'
        body += f'<text x="42" y="{y + 36}" font-size="12.5" fill="{TEXT_SECONDARY}">{esc(edu["program"])} · {esc(edu.get("period", ""))}</text>\n'
        body += "</g>\n"
        y += 60

    if education:
        y += 10

    body += f'<text x="42" y="{y}" font-size="13" font-weight="600" fill="{TEXT_SECONDARY}">CERTIFICATIONS</text>\n'
    y += 20

    col_w = (w - 84 - 20) // cols
    for i, cert in enumerate(certs):
        col = i % cols
        row = i // cols
        cx = 42 + col * (col_w + 20)
        cy = y + row * 56
        body += f'<g class="cert-{i}">\n'
        body += f'<rect x="{cx}" y="{cy}" width="{col_w}" height="46" rx="10" fill="url(#panelFade)" stroke="{BORDER}" stroke-width="1"/>\n'
        body += f'<circle cx="{cx + 24}" cy="{cy + 23}" r="5" fill="url(#accentGrad)"/>\n'
        body += f'<text x="{cx + 42}" y="{cy + 20}" font-size="12.5" font-weight="600" fill="{TEXT_PRIMARY}">{esc(cert["name"])}</text>\n'
        body += f'<text x="{cx + 42}" y="{cy + 37}" font-size="11" fill="{TEXT_SECONDARY}">{esc(cert["issuer"])} · {esc(cert["issued"])}</text>\n'
        body += "</g>\n"

    return card_shell(w, h, body, accent1, accent2, css)


# ---------------------------------------------------------------------------
# E. Technical skills
# ---------------------------------------------------------------------------

def render_tech_stack(profile: dict) -> str:
    w = 940
    categories = list(profile["skills"].items())
    h = 80 + sum(56 for _ in categories)
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]

    css = reveal_css([(f".cat-{i}", 0.1 + i * 0.12) for i in range(len(categories))]) + static_opacity_override(
        [f".cat-{i}" for i in range(len(categories))]
    )

    body = f'<text x="42" y="52" font-size="20" font-weight="700" fill="{TEXT_PRIMARY}">Technical Skills</text>\n'
    body += '<rect x="42" y="64" width="46" height="3" rx="1.5" fill="url(#accentGrad)"/>\n'

    y = 96
    for i, (category, skills) in enumerate(categories):
        body += f'<g class="cat-{i}">\n'
        body += f'<text x="42" y="{y}" font-size="13" font-weight="700" fill="url(#accentGrad)">{esc(category.upper())}</text>\n'
        x = 42
        chip_y = y + 16
        for skill in skills:
            chip_w = 14 + len(skill) * 7.2
            if x + chip_w > w - 42:
                x = 42
                chip_y += 32
            body += (
                f'<rect x="{x}" y="{chip_y}" width="{chip_w:.0f}" height="26" rx="13" '
                f'fill="{BG_PANEL}" stroke="{BORDER}" stroke-width="1"/>\n'
            )
            body += f'<text x="{x + chip_w / 2:.0f}" y="{chip_y + 17}" font-size="12" text-anchor="middle" fill="{TEXT_PRIMARY}">{esc(skill)}</text>\n'
            x += chip_w + 10
        body += "</g>\n"
        y += 56

    return card_shell(w, h, body, accent1, accent2, css)


# ---------------------------------------------------------------------------
# F. GitHub contribution analytics dashboard
# ---------------------------------------------------------------------------

def render_activity(profile: dict, stats: dict) -> str:
    w, h = 940, 300
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]

    css = reveal_css(
        [(".stat-tiles", 0.1), (".chart-bars", 0.3)], duration=0.5
    ) + static_opacity_override([".stat-tiles", ".chart-bars"])

    tiles = [
        ("Total contributions", stats["total_contributions"]),
        ("Current streak", f'{stats["current_streak"]}d'),
        ("Longest streak", f'{stats["longest_streak"]}d'),
        ("Active days", stats["active_days"]),
    ]

    body = f'<text x="42" y="46" font-size="20" font-weight="700" fill="{TEXT_PRIMARY}">GitHub Activity — Last 12 Months</text>\n'
    body += '<rect x="42" y="58" width="46" height="3" rx="1.5" fill="url(#accentGrad)"/>\n'

    body += '<g class="stat-tiles">\n'
    tile_w = (w - 84 - 3 * 16) / 4
    for i, (label, value) in enumerate(tiles):
        x = 42 + i * (tile_w + 16)
        body += f'<rect x="{x:.0f}" y="78" width="{tile_w:.0f}" height="64" rx="12" fill="url(#panelFade)" stroke="{BORDER}" stroke-width="1"/>\n'
        body += f'<text x="{x + 16:.0f}" y="112" font-size="26" font-weight="700" fill="{TEXT_PRIMARY}">{value}</text>\n'
        body += f'<text x="{x + 16:.0f}" y="130" font-size="11" fill="{TEXT_SECONDARY}">{esc(label)}</text>\n'
    body += "</g>\n"

    # Monthly bar chart for the last 12 months
    monthly = stats["monthly"]
    months_sorted = sorted(monthly.keys())[-12:]
    max_val = max([monthly[m] for m in months_sorted], default=1) or 1

    chart_x, chart_y, chart_w, chart_h = 42, 170, w - 84, 100
    bar_gap = 10
    bar_w = (chart_w - bar_gap * (len(months_sorted) - 1)) / max(len(months_sorted), 1)

    body += '<g class="chart-bars">\n'
    for i, m in enumerate(months_sorted):
        val = monthly[m]
        bar_h = (val / max_val) * (chart_h - 20) if max_val else 0
        bx = chart_x + i * (bar_w + bar_gap)
        by = chart_y + chart_h - bar_h
        label = MONTH_NAMES[int(m.split("-")[1]) - 1]
        body += f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{max(bar_h, 2):.1f}" rx="3" fill="url(#accentGrad)" opacity="0.85"/>\n'
        body += f'<text x="{bx + bar_w / 2:.1f}" y="{chart_y + chart_h + 18}" font-size="10.5" text-anchor="middle" fill="{TEXT_MUTED}">{label}</text>\n'
    body += "</g>\n"

    if stats.get("busiest_day"):
        busiest = stats["busiest_day"]
        body += (
            f'<text x="42" y="{chart_y + chart_h + 42}" font-size="11.5" fill="{TEXT_SECONDARY}">'
            f'Busiest day: {esc(busiest["date"])} ({busiest["count"]} contributions)</text>\n'
        )

    return card_shell(w, h, body, accent1, accent2, css)


# ---------------------------------------------------------------------------
# G. Contribution heatmap
# ---------------------------------------------------------------------------

def render_heatmap(profile: dict, stats: dict) -> str:
    w, h = 940, 190
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]

    days = {d["date"]: d["count"] for d in stats["days"]}
    if days:
        all_dates = sorted(days.keys())
        start = dt.date.fromisoformat(all_dates[0])
        end = dt.date.fromisoformat(all_dates[-1])
    else:
        end = dt.date.today()
        start = end - dt.timedelta(days=364)

    # Align start to the preceding Sunday so weeks form clean columns
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)

    counts = [v for v in days.values() if v > 0]
    max_count = max(counts) if counts else 1

    def level(count: int) -> int:
        if count == 0:
            return 0
        if count <= max_count * 0.25:
            return 1
        if count <= max_count * 0.5:
            return 2
        if count <= max_count * 0.75:
            return 3
        return 4

    level_colors = [BG_PANEL, "#2A2560", "#4A3FA0", "#6E58D8", accent1]

    cell = 11
    gap = 3
    top = 54
    left = 46

    css = reveal_css([(".heatmap-grid", 0.15)], duration=0.8) + static_opacity_override([".heatmap-grid"])

    body = f'<text x="42" y="36" font-size="18" font-weight="700" fill="{TEXT_PRIMARY}">Contribution Heatmap</text>\n'

    body += '<g class="heatmap-grid">\n'
    cur = start
    week = 0
    last_month = None
    while cur <= end:
        if cur.weekday() == 6:  # Sunday start of column
            month_label = MONTH_NAMES[cur.month - 1]
            if month_label != last_month:
                x = left + week * (cell + gap)
                body += f'<text x="{x}" y="{top - 10}" font-size="10" fill="{TEXT_MUTED}">{month_label}</text>\n'
                last_month = month_label
        day_index = (cur.weekday() + 1) % 7  # 0 = Sunday
        x = left + week * (cell + gap)
        y = top + day_index * (cell + gap)
        c = days.get(cur.isoformat(), 0)
        color = level_colors[level(c)]
        body += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}"/>\n'
        if day_index == 6:
            week += 1
        cur += dt.timedelta(days=1)
    body += "</g>\n"

    legend_x = w - 220
    legend_y = h - 24
    body += f'<text x="{legend_x - 30}" y="{legend_y + 9}" font-size="10.5" fill="{TEXT_MUTED}">Less</text>\n'
    for i, color in enumerate(level_colors):
        body += f'<rect x="{legend_x + i * 16}" y="{legend_y}" width="11" height="11" rx="3" fill="{color}"/>\n'
    body += f'<text x="{legend_x + len(level_colors) * 16 + 8}" y="{legend_y + 9}" font-size="10.5" fill="{TEXT_MUTED}">More</text>\n'

    return card_shell(w, h, body, accent1, accent2, css)


# ---------------------------------------------------------------------------
# H. Featured repository cards
# ---------------------------------------------------------------------------

def render_repo_card(filename: str, repo: dict, profile: dict) -> None:
    w, h = 300, 180
    accent1, accent2 = profile["accent_primary"], profile["accent_secondary"]

    css = reveal_css([(".repo-name", 0.1), (".repo-desc", 0.25)]) + static_opacity_override(
        [".repo-name", ".repo-desc"]
    )

    desc_lines = wrap_text(repo.get("description") or "No description provided.", 34)[:3]

    body = f"""
    <text class="repo-name" x="24" y="40" font-size="16" font-weight="700" fill="{TEXT_PRIMARY}">{esc(repo['name'])}</text>
    """
    y = 64
    for line in desc_lines:
        body += f'<text class="repo-desc" x="24" y="{y}" font-size="12" fill="{TEXT_SECONDARY}">{esc(line)}</text>\n'
        y += 18

    footer_y = h - 28
    body += f'<circle cx="32" cy="{footer_y}" r="5" fill="url(#accentGrad)"/>\n'
    body += f'<text x="44" y="{footer_y + 4}" font-size="11.5" fill="{TEXT_SECONDARY}">{esc(repo.get("language") or "—")}</text>\n'
    body += f'<text x="150" y="{footer_y + 4}" font-size="11.5" fill="{TEXT_SECONDARY}">★ {repo.get("stars", 0)}</text>\n'
    body += f'<text x="210" y="{footer_y + 4}" font-size="11.5" fill="{TEXT_SECONDARY}">⑂ {repo.get("forks", 0)}</text>\n'

    write_svg(filename, card_shell(w, h, body, accent1, accent2, css))


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

    render_nav_tile(
        "tile-projects.svg", "🗂️", "Projects",
        "Explore my GitHub repositories", profile,
    )
    render_nav_tile(
        "tile-skills.svg", "🧠", "Experience & Skills",
        "What I've worked on and built with", profile,
    )
    render_nav_tile(
        "tile-connect.svg", "🔗", "Connect",
        "Let's get in touch on LinkedIn", profile,
    )

    write_svg("experience.svg", render_experience(profile))
    write_svg("education.svg", render_education(profile))
    write_svg("tech-stack.svg", render_tech_stack(profile))

    for repo_name in profile.get("featured_repos", []):
        repo = repos_by_name.get(repo_name, {"name": repo_name, "description": "", "language": "", "stars": 0, "forks": 0})
        safe_name = repo_name.lower().replace("_", "-")
        render_repo_card(f"repo-{safe_name}.svg", repo, profile)

    print("Done." + (" (static preview mode)" if STATIC else ""))


if __name__ == "__main__":
    main()
