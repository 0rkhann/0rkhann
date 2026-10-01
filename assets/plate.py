"""Render the last year of GitHub contributions as an assay plate read (stdlib only, runs in the profile workflow).

One well per day: rows A-G are weekdays (Sun-Sat), columns are weeks. Well signal is the day's contribution count.
Run: GITHUB_TOKEN=... python3 assets/plate.py [username] [out.svg]
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date weekday contributionCount } } }
    }
  }
}"""

BG, PLATE, EDGE, TEAL, TEXT, MUTED, EMPTY = "#0d1117", "#111820", "#2a3440", "#4FD1C5", "#e6edf3", "#8b949e", "#1a222c"
# signal ramp from a faint hit to a saturated well
RAMP = ["#12403d", "#1c6b65", "#2a9f95", "#4FD1C5"]
SANS = '-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
W, PITCH, R = 1200, 19.6, 7.4
X0, Y0 = 101, 112  # centre of well A1


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
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def longest_run(counts):
    best = run = 0
    for c in counts:
        run = run + 1 if c else 0
        best = max(best, run)
    return best


def level(count, cuts):
    """0 for an empty well, else 1-4 by quartile of the non-zero days."""
    if not count:
        return 0
    return 1 + sum(count > c for c in cuts)


def quartile_cuts(counts):
    hits = sorted(c for c in counts if c)
    if not hits:
        return [0, 0, 0]
    return [hits[len(hits) * q // 4] for q in (1, 2, 3)]


def render(login, cal):
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    cuts = quartile_cuts(counts)
    active = sum(1 for c in counts if c)
    hit_rate = 100 * active / len(days) if days else 0
    first, last = days[0]["date"], days[-1]["date"]
    ncol = len(weeks)

    out = []
    # column numbers on top, row letters on the left, like a real plate
    for j in range(ncol):
        x = X0 + j * PITCH
        out.append(f'<text x="{x:.1f}" y="{Y0 - 20}" class="cn">{j + 1}</text>')
    for i, letter in enumerate("ABCDEFG"):
        out.append(f'<text x="{X0 - 26}" y="{Y0 + i * PITCH + 4:.1f}" class="rn">{letter}</text>')

    # hit wells only; empty wells come from one pattern-filled rect. The scan reveals column j at j * step seconds
    step = 0.035
    seen_month = None
    for j, w in enumerate(weeks):
        x = X0 + j * PITCH
        for d in w["contributionDays"]:
            y = Y0 + d["weekday"] * PITCH
            c = d["contributionCount"]
            lv = level(c, cuts)
            if lv:
                out.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R}" fill="{RAMP[lv - 1]}" class="hit{" top" * (lv == 4)}" '
                    f'style="animation-delay:{j * step + .2:.2f}s"/>'
                )
            month = d["date"][:7]
            if d["weekday"] == 0 and month != seen_month and int(d["date"][8:]) <= 7:
                label = dt.date.fromisoformat(d["date"]).strftime("%b")
                out.append(f'<text x="{x - R:.1f}" y="{Y0 + 6 * PITCH + 30:.1f}" class="mo">{label}</text>')
                seen_month = month

    px0, py0 = X0 - 44, Y0 - 44
    px1, py1 = X0 + (ncol - 1) * PITCH + 22, Y0 + 6 * PITCH + 44
    scan_x1 = X0 + (ncol - 1) * PITCH + 12
    legend_x = px1 - 230
    legend = "".join(
        f'<circle cx="{legend_x + 70 + k * 24}" cy="{py1 + 32}" r="{R}" '
        + (f'fill="{RAMP[k - 1]}"' if k else 'class="well"')
        + "/>"
        for k in range(5)
    )
    span = f'{dt.date.fromisoformat(first).strftime("%b %Y")} – {dt.date.fromisoformat(last).strftime("%b %Y")}'
    h = py1 + 58
    stats = (
        f'<tspan class="v">{cal["totalContributions"]:,}</tspan> contributions   '
        f'<tspan class="v">{hit_rate:.0f}%</tspan> hit rate   '
        f'<tspan class="v">{longest_run(counts)}d</tspan> longest run'
    )
    body = "\n  ".join(out)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h:.0f}" width="{W}" height="{h:.0f}" role="img" aria-label="{escape(login)}'s contributions from {span} drawn as an assay plate: {cal["totalContributions"]:,} contributions, {active} active days.">
  <style>
    .title {{ font:700 15px {MONO}; fill:{TEXT}; letter-spacing:2px; }}
    .sub {{ font:400 13px {MONO}; fill:{MUTED}; }}
    .stat {{ font:400 14px {SANS}; fill:{MUTED}; white-space:pre; }}
    .v {{ font:700 15px {MONO}; fill:{TEAL}; }}
    .cn {{ font:400 9px {MONO}; fill:{MUTED}; text-anchor:middle; }}
    .rn {{ font:700 12px {MONO}; fill:{MUTED}; text-anchor:middle; }}
    .mo {{ font:400 11px {MONO}; fill:{MUTED}; }}
    .well {{ fill:{EMPTY}; stroke:{EDGE}; stroke-width:1; }}
    .top {{ stroke:#a7f3ec; stroke-width:1.5; }}
    .hit {{ opacity:0; animation:read .5s ease-out forwards; }}
    .scan {{ fill:url(#beam); animation:sweep {ncol * step + .4:.2f}s linear .2s forwards; opacity:0; }}
    @keyframes read {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
    @keyframes sweep {{ 0% {{ opacity:1; transform:translateX(0); }} 92% {{ opacity:1; }} 100% {{ opacity:0; transform:translateX({scan_x1 - X0:.0f}px); }} }}
    @media (prefers-reduced-motion: reduce) {{ .hit {{ animation:none; opacity:1; }} .scan {{ display:none; }} }}
  </style>
  <defs>
    <pattern id="wells" x="{X0 - PITCH / 2:.1f}" y="{Y0 - PITCH / 2:.1f}" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse"><circle cx="{PITCH / 2}" cy="{PITCH / 2}" r="{R}" class="well"/></pattern>
    <linearGradient id="beam" x1="0" x2="1"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/><stop offset=".85" stop-color="{TEAL}" stop-opacity=".28"/><stop offset="1" stop-color="{TEAL}" stop-opacity=".9"/></linearGradient>
  </defs>
  <rect width="{W}" height="{h:.0f}" rx="14" fill="{BG}"/>
  <text x="{px0}" y="34" class="title">PLATE READ · {escape(login)}</text>
  <text x="{px0 + 250}" y="34" class="sub">{span} · 1 well = 1 day</text>
  <text x="{px1:.0f}" y="34" class="stat" text-anchor="end">{stats}</text>
  <path d="M{px0 + 18},{py0} H{px1 - 12} a12,12 0 0 1 12,12 V{py1 - 12} a12,12 0 0 1 -12,12 H{px0 + 12} a12,12 0 0 1 -12,-12 V{py0 + 18} Z" fill="{PLATE}" stroke="{EDGE}" stroke-width="1.5"/>
  <rect x="{X0 - PITCH / 2:.1f}" y="{Y0 - PITCH / 2:.1f}" width="{ncol * PITCH:.1f}" height="{7 * PITCH:.1f}" fill="url(#wells)"/>
  {body}
  <rect x="{X0 - 40}" y="{Y0 - 12}" width="40" height="{6 * PITCH + 24:.0f}" class="scan"/>
  <text x="{px0}" y="{py1 + 37}" class="sub">signal quartiles over active days · data: GitHub GraphQL</text>
  <text x="{legend_x}" y="{py1 + 37}" class="sub">none</text>{legend}<text x="{legend_x + 70 + 4 * 24 + 16}" y="{py1 + 37}" class="sub">high</text>
</svg>
'''


if __name__ == "__main__":
    login = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REPOSITORY_OWNER", "0rkhann")
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/plate.svg"
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    assert longest_run([1, 1, 0, 1, 1, 1, 0]) == 3
    assert [level(c, [1, 3, 6]) for c in (0, 1, 2, 4, 9)] == [0, 1, 2, 3, 4]
    cal = fetch(login, token)
    with open(out, "w") as f:
        f.write(render(login, cal))
    print(f"wrote {out}: {cal['totalContributions']} contributions over {len(cal['weeks'])} weeks")
