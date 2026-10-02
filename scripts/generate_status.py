"""Render assets/status.svg: a status-page view of GitHub activity.

Usage: GITHUB_TOKEN=... python scripts/generate_status.py <username> <out.svg>
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests(states: MERGED) { totalCount }
    allPRs: pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED, GREEN, AMBER = "#e6edf3", "#8b949e", "#3fb950", "#d29922"
LEVELS = ["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def streaks(days):
    today = dt.date.today().isoformat()
    counts = [d["contributionCount"] for d in days if d["date"] <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    # Today not having contributions yet shouldn't break the streak.
    for i, c in enumerate(reversed(counts)):
        if c:
            current += 1
        elif i:
            break
    return current, longest


def languages(repos, top=5):
    sizes, colors = {}, {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name == "Jupyter Notebook":  # notebooks are Python
                name = "Python"
            sizes[name] = sizes.get(name, 0) + e["size"]
            colors.setdefault(name, e["node"]["color"] or MUTED)
            if name == "Python":
                colors[name] = "#3572A5"
    total = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1])
    out = [(n, s / total, colors[n]) for n, s in ranked[:top]]
    rest = 1 - sum(p for _, p, _ in out)
    if rest > 0.005:
        out.append(("Other", rest, "#484f58"))
    return out


def level(count, peak):
    if count == 0:
        return LEVELS[0]
    return LEVELS[min(4, 1 + int(3 * count / max(peak, 1)))]


def text(x, y, s, fill=TEXT, size=13, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(s))}</text>')


def render(u):
    cc = u["contributionsCollection"]
    weeks = cc["contributionCalendar"]["weeks"][-52:]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    current, longest = streaks(days)
    last7 = sum(d["contributionCount"] for d in days[-7:])
    last_ship = max((d["date"] for d in days if d["contributionCount"]), default="—")
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    langs = languages(u["repositories"]["nodes"])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ok = last7 > 0
    status_color = GREEN if ok else AMBER
    status_text = "All systems operational" if ok else "Degraded performance (probably touching grass)"

    W, H = 880, 470
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="{FONT}" role="img" aria-label="Status page: {status_text}. '
         f'{cc["contributionCalendar"]["totalContributions"]} contributions in the last year.">',
         '<style>.pulse{animation:p 2s ease-in-out infinite}@keyframes p{50%{opacity:.25}}'
         '.bar{transform-box:fill-box;transform-origin:bottom;animation:g .6s cubic-bezier(.2,.8,.2,1) both}'
         '@keyframes g{from{transform:scaleY(0)}}</style>',
         f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{BG}" stroke="{BORDER}"/>']

    # Header
    o.append(f'<circle cx="30" cy="34" r="6" fill="{status_color}" class="pulse"/>')
    o.append(text(46, 39, "abhishek.prod", TEXT, 16, 700))
    o.append(text(186, 39, "/ status", MUTED, 16))
    o.append(text(W - 24, 39, f"updated {now}", MUTED, 12, anchor="end"))

    # Status banner
    o.append(f'<rect x="24" y="60" width="{W-48}" height="44" rx="8" fill="{status_color}" fill-opacity=".12" stroke="{status_color}" stroke-opacity=".5"/>')
    o.append(text(44, 88, f"● {status_text}", status_color, 15, 700))
    o.append(text(W - 44, 88, f"last deploy: {last_ship}", MUTED, 12, anchor="end"))

    # Uptime bars
    o.append(text(24, 138, "shipping uptime", TEXT, 13, 700))
    o.append(text(W - 24, 138, f"{cc['contributionCalendar']['totalContributions']:,} contributions · last 12 months", MUTED, 12, anchor="end"))
    peak = max(weekly) if weekly else 1
    bw, gap, x0, top, bh = 13, 3.08, 24, 150, 40
    for i, (w, wk) in enumerate(zip(weekly, weeks)):
        x = x0 + i * (bw + gap)
        h = bh if w else bh * 0.55
        title = f'week of {wk["contributionDays"][0]["date"]}: {w} contributions'
        o.append(f'<rect class="bar" style="animation-delay:{i*0.015:.3f}s" x="{x:.1f}" y="{top + bh - h:.1f}" '
                 f'width="{bw}" height="{h:.1f}" rx="2" fill="{level(w, peak)}"><title>{escape(title)}</title></rect>')
    o.append(text(24, 208, "52 weeks ago", MUTED, 11))
    o.append(text(W - 24, 208, "this week", MUTED, 11, anchor="end"))

    # Metrics grid
    metrics = [
        ("pull requests opened", u["allPRs"]["totalCount"]),
        ("PRs merged", u["pullRequests"]["totalCount"]),
        ("public repos", u["repositories"]["totalCount"]),
        ("commits / 12 mo", cc["totalCommitContributions"]),
        ("current streak", f"{current}d"),
        ("longest streak", f"{longest}d"),
        ("stars earned", stars),
        ("followers", u["followers"]["totalCount"]),
    ]
    cw, ch, gx, gy = (W - 48 - 3 * 12) / 4, 62, 24, 228
    for i, (label, val) in enumerate(metrics):
        cx, cy = gx + (i % 4) * (cw + 12), gy + (i // 4) * (ch + 12)
        o.append(f'<rect x="{cx:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>')
        o.append(text(cx + 14, cy + 34, f"{val:,}" if isinstance(val, int) else val, TEXT, 22, 700))
        o.append(text(cx + 14, cy + 52, label, MUTED, 11))

    # Languages
    ly = 396
    o.append(text(24, ly, "runtime languages", TEXT, 13, 700))
    x, bar_w = 24.0, W - 48
    for name, pct, color in langs:
        w = bar_w * pct
        o.append(f'<rect x="{x:.1f}" y="{ly + 10}" width="{max(w - 2, 1):.1f}" height="10" rx="3" fill="{color}"/>')
        x += w
    lx = 24
    for name, pct, color in langs:
        o.append(f'<circle cx="{lx + 5}" cy="{ly + 42}" r="5" fill="{color}"/>')
        label = f"{name} {pct*100:.0f}%"
        o.append(text(lx + 16, ly + 46, label, MUTED, 12))
        lx += 26 + len(label) * 7.4

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    svg = render(fetch(login, os.environ["GITHUB_TOKEN"]))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out}")
