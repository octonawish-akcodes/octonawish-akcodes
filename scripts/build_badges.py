"""Render self-hosted social badges and stack tags (no external services).

Usage: python scripts/build_badges.py
"""
import os
from html import escape

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CHAR_W = 7.9  # approx advance of 13px monospace

ICONS = {
    "x": '<path d="M2 2h4.4L14 14H9.6z" fill="#e6edf3"/>'
         '<path d="M13.6 2.2 2.4 13.8" stroke="#e6edf3" stroke-width="1.7" stroke-linecap="round"/>',
    "linkedin": '<rect width="16" height="16" rx="3" fill="#0A66C2"/>'
                '<circle cx="4.4" cy="4.2" r="1.45" fill="#fff"/>'
                '<rect x="3.1" y="6.3" width="2.6" height="6.9" fill="#fff"/>'
                '<path d="M7.2 6.3h2.4v1c.5-.8 1.4-1.2 2.4-1.2 1.9 0 2.8 1.2 2.8 3.3v3.8h-2.6V9.8c0-1-.3-1.6-1.2-1.6-.9 0-1.3.7-1.3 1.7v3.3H7.2z" fill="#fff"/>',
    "email": '<rect x="1" y="3" width="14" height="10.5" rx="2" fill="none" stroke="#ff7b72" stroke-width="1.6"/>'
             '<path d="M1.8 4.2 8 9l6.2-4.8" fill="none" stroke="#ff7b72" stroke-width="1.6" stroke-linejoin="round"/>',
    "blog": '<rect x="2.5" y="1.5" width="11" height="13" rx="2" fill="none" stroke="#79c0ff" stroke-width="1.6"/>'
            '<path d="M5.2 5.5h5.6M5.2 8.2h5.6M5.2 10.9h3.4" stroke="#79c0ff" stroke-width="1.6" stroke-linecap="round"/>',
}

BADGES = [("x", "@logsofabhi"), ("linkedin", "LinkedIn"), ("email", "Email"), ("blog", "Blog")]

TAGS = [
    ("LLM Evals", "#7ee787"), ("AI Agents", "#79c0ff"), ("RAG", "#d2a8ff"),
    ("Vector DBs", "#ffa657"), ("Claude Code", "#d97757"), ("Apache Airflow", "#58a6ff"),
    ("PySpark", "#f0883e"), ("Redshift", "#a371f7"), ("SageMaker", "#e3b341"),
]


def badge(icon, label):
    h, pad, icon_w, gap = 36, 14, 16, 10
    w = round(pad + icon_w + gap + len(label) * CHAR_W + pad)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(label)}">'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="8" fill="#161b22" stroke="#30363d"/>'
            f'<g transform="translate({pad} {(h-16)/2})">{ICONS[icon]}</g>'
            f'<text x="{pad+icon_w+gap}" y="{h/2+4.5}" fill="#e6edf3" font-family="{FONT}" '
            f'font-size="13" font-weight="600">{escape(label)}</text></svg>')


def tags(width=880):
    h, gap, pad, char_w = 28, 8, 12, 7.3
    chips = [(t, c, round(pad + 14 + len(t) * char_w + pad)) for t, c in TAGS]
    half = (len(chips) + 1) // 2  # two balanced rows
    rows = [chips[:half], chips[half:]]
    total_h = len(rows) * h + (len(rows) - 1) * gap
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}" '
         f'font-family="{FONT}" role="img" aria-label="{escape(", ".join(t for t, _ in TAGS))}">']
    for r, row in enumerate(rows):
        x = (width - (sum(c[2] for c in row) + gap * (len(row) - 1))) / 2
        y = r * (h + gap)
        for t, c, w in row:
            o.append(f'<rect x="{x+.5:.1f}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="14" fill="#161b22" stroke="#30363d"/>'
                     f'<circle cx="{x+pad+4:.1f}" cy="{y+h/2}" r="4" fill="{c}"/>'
                     f'<text x="{x+pad+14:.1f}" y="{y+h/2+4}" fill="#c9d1d9" font-size="12">{escape(t)}</text>')
            x += w + gap
    o.append("</svg>")
    return "".join(o)


if __name__ == "__main__":
    os.makedirs("assets/badges", exist_ok=True)
    for icon, label in BADGES:
        with open(f"assets/badges/{icon}.svg", "w") as f:
            f.write(badge(icon, label))
    with open("assets/tags.svg", "w") as f:
        f.write(tags())
    print("wrote assets/badges/*.svg and assets/tags.svg")
