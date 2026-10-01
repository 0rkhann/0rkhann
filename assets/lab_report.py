"""Render GitHub activity as an analytical lab report SVG (stdlib only, runs in the profile workflow).

Run: GITHUB_TOKEN=... python3 assets/lab_report.py [username] [out.svg]
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions totalPullRequestContributions
      totalIssueContributions totalPullRequestReviewContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount languages(first: 10) { edges { size node { name color } } } }
    }
  }
}"""

BG, EDGE, PANEL, TEAL, TEXT, MUTED, DIM = "#0d1117", "#21262d", "#161b22", "#4FD1C5", "#e6edf3", "#8b949e", "#484f58"
SANS = '-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
W, H = 1200, 500


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body or not body.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {body.get('errors')}")
    return body["data"]["user"]


def streaks(days):
    """Longest and current run of days with at least one contribution."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    # today may still be empty; the streak only breaks once a full day passes without contributions
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return longest, current


def summarise(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or MUTED))
            langs[name] = (size + e["size"], color)
    longest, current = streaks(days)
    return {
        "total": cal["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "active": sum(1 for d in days if d["contributionCount"]),
        "ndays": len(days),
        "longest": longest,
        "current": current,
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "weeks": weeks,
        "first_day": days[0]["date"] if days else "",
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0]),
    }


def spectrum(weeks, x0, y0, w, h):
    """Weekly totals drawn as an NMR-style spectrum: one Lorentzian peak per week, sqrt-scaled so quiet weeks stay visible."""
    top = max(weeks) or 1
    n = len(weeks)
    xs = [x0 + w * (i + .5) / n for i in range(n)]
    hw = w / n * .35
    pts = []
    for k in range(0, int(w) + 1, 2):
        x = x0 + k
        y = sum((c / top) ** .5 / (1 + ((x - xi) / hw) ** 2) for c, xi in zip(weeks, xs) if c)
        pts.append(f"{x:.0f},{y0 + h - min(y, 1.05) * h:.1f}")
    line = "M" + " L".join(pts)
    area = f"{line} L{x0 + w:.0f},{y0 + h} L{x0},{y0 + h} Z"
    return line, area


def fmt(n):
    return f"{n:,}"


def render(login, s, today):
    rows = [
        ("Contributions (12 mo)", fmt(s["total"])),
        ("Commits · PRs · Issues · Reviews", f'{fmt(s["commits"])} · {s["prs"]} · {s["issues"]} · {s["reviews"]}'),
        ("Active days", f'{s["active"]} / {s["ndays"]}'),
        ("Longest · current streak", f'{s["longest"]} d · {s["current"]} d'),
        ("Public repos · stars · followers", f'{s["repos"]} · {s["stars"]} · {s["followers"]}'),
    ]
    checks = [
        ("≥ 500 contributions", s["total"] >= 500),
        ("≥ 100 active days", s["active"] >= 100),
        ("streak ≥ 7 days", s["longest"] >= 7),
        ("≥ 2 languages", len(s["langs"]) >= 2),
    ]
    passed = sum(ok for _, ok in checks)

    out = []
    y = 112
    for label, value in rows:
        out.append(f'<text x="40" y="{y}" class="lab">{escape(label)}</text>')
        out.append(f'<text x="560" y="{y}" class="val" text-anchor="end">{escape(value)}</text>')
        out.append(f'<line x1="40" y1="{y + 12}" x2="560" y2="{y + 12}" class="rule"/>')
        y += 38

    # composition: language share of bytes across public, non-fork repositories
    total = sum(v[0] for _, v in s["langs"]) or 1
    shown = s["langs"][:5]
    other = total - sum(v[0] for _, v in shown)
    if other > 0:
        shown = shown + [("Other", (other, DIM))]
    bx, bw, by = 640, 520, 92
    out.append(f'<text x="{bx}" y="{by - 12}" class="head">COMPOSITION · by bytes</text>')
    x = bx
    for name, (size, color) in shown:
        seg = bw * size / total
        out.append(f'<rect x="{x:.1f}" y="{by}" width="{max(seg - 2, 1):.1f}" height="14" rx="3" fill="{color}"/>')
        x += seg
    ly = by + 48
    for i, (name, (size, color)) in enumerate(shown):
        cx = bx + (i % 2) * 270
        cy = ly + (i // 2) * 30
        out.append(f'<circle cx="{cx + 6}" cy="{cy - 5}" r="6" fill="{color}"/>')
        out.append(f'<text x="{cx + 20}" y="{cy}" class="lab">{escape(name)}</text>')
        out.append(f'<text x="{cx + 250}" y="{cy}" class="val" text-anchor="end">{100 * size / total:.1f}%</text>')

    # spectrum of weekly activity
    sx, sy, sw, sh = 40, 330, 1120, 82
    line, area = spectrum(s["weeks"], sx, sy, sw, sh)
    out.append(f'<text x="{sx}" y="{sy - 18}" class="head">ACTIVITY SPECTRUM · one peak per week</text>')
    out.append(f'<path d="{area}" fill="url(#fill)"/>')
    out.append(f'<path d="{line}" class="spec"/>')
    out.append(f'<line x1="{sx}" y1="{sy + sh}" x2="{sx + sw}" y2="{sy + sh}" class="axis"/>')
    start = dt.date.fromisoformat(s["first_day"]) if s["first_day"] else today - dt.timedelta(days=364)
    for i in range(0, 13, 2):
        d = start + dt.timedelta(days=round(i * 30.4))
        tx = sx + sw * i / 12
        out.append(f'<text x="{tx:.0f}" y="{sy + sh + 20}" class="tick" text-anchor="middle">{d.strftime("%b")}</text>')

    # pass/fail line, styled after Lipinski's rule of five
    cx = 40
    out.append(f'<text x="{cx}" y="{H - 26}" class="lab">Dev rule-of-five</text>')
    cx += 160
    for label, ok in checks:
        mark, cls = ("✓", "ok") if ok else ("✗", "bad")
        out.append(f'<text x="{cx}" y="{H - 26}" class="{cls}">{mark}</text><text x="{cx + 18}" y="{H - 26}" class="lab">{escape(label)}</text>')
        cx += 30 + 8.6 * len(label)
    verdict = "PASS" if passed == len(checks) else "PARTIAL"
    out.append(f'<text x="{W - 40}" y="{H - 26}" class="verdict" text-anchor="end">{verdict} {passed}/{len(checks)}</text>')

    body = "\n  ".join(out)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub activity of {escape(login)} as an analytical report: {fmt(s["total"])} contributions in 12 months.">
  <style>
    .title {{ font:700 20px {SANS}; fill:{TEXT}; letter-spacing:2px; }}
    .meta {{ font:400 14px {MONO}; fill:{MUTED}; }}
    .head {{ font:600 12px {MONO}; fill:{TEAL}; letter-spacing:1.5px; }}
    .lab {{ font:400 15px {SANS}; fill:#c9d1d9; }}
    .val {{ font:600 16px {MONO}; fill:{TEXT}; }}
    .rule {{ stroke:{EDGE}; }}
    .axis {{ stroke:{DIM}; }}
    .tick {{ font:400 12px {MONO}; fill:{MUTED}; }}
    .spec {{ fill:none; stroke:{TEAL}; stroke-width:1.6; stroke-dasharray:4000; stroke-dashoffset:4000; animation:trace 3s ease-out .3s forwards; }}
    .ok {{ font:700 16px {MONO}; fill:{TEAL}; }} .bad {{ font:700 16px {MONO}; fill:#ff7b72; }}
    .verdict {{ font:700 16px {MONO}; fill:{TEAL}; letter-spacing:2px; }}
    @keyframes trace {{ to {{ stroke-dashoffset:0; }} }}
    @media (prefers-reduced-motion: reduce) {{ .spec {{ animation:none; stroke-dashoffset:0; }} }}
  </style>
  <defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{TEAL}" stop-opacity=".35"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></linearGradient></defs>
  <rect width="{W}" height="{H}" rx="14" fill="{BG}"/>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="none" stroke="{EDGE}"/>
  <path d="M1,14 a13,13 0 0 1 13,-13 H{W - 14} a13,13 0 0 1 13,13 V56 H1 Z" fill="{PANEL}"/>
  <text x="40" y="37" class="title">ANALYTICAL REPORT</text>
  <text x="{W - 40}" y="36" class="meta" text-anchor="end">sample: {escape(login)} · {today.isoformat()} · GitHub GraphQL</text>
  {body}
</svg>
'''


if __name__ == "__main__":
    login = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REPOSITORY_OWNER", "0rkhann")
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/report.svg"
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    stats = summarise(fetch(login, token))
    assert streaks([{"contributionCount": c} for c in [1, 1, 0, 1, 1, 1, 0]]) == (3, 3)
    with open(out, "w") as f:
        f.write(render(login, stats, dt.date.today()))
    print(f"wrote {out}: {stats['total']} contributions, {len(stats['langs'])} languages")
