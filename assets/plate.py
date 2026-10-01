"""Render every year of GitHub contributions as a stack of assay plates (stdlib only, runs in the profile workflow).

One plate per calendar year, one well per day: rows A-G are weekdays (Sun-Sat), columns are weeks.
Well signal is the day's contribution count, binned by quartiles over all active days.
Run: GITHUB_TOKEN=... python3 assets/plate.py [username] [out.svg]
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

CREATED = "query($login: String!) { user(login: $login) { createdAt } }"
YEAR = """query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions weeks { contributionDays { date weekday contributionCount } } }
    }
  }
}"""

BG, PLATE, EDGE, TEAL, TEXT, MUTED, EMPTY = "#0d1117", "#111820", "#2a3440", "#4FD1C5", "#e6edf3", "#8b949e", "#1a222c"
# signal ramp from a faint hit to a saturated well
RAMP = ["#12403d", "#1c6b65", "#2a9f95", "#4FD1C5"]
SANS = '-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
W, PITCH, R = 1200, 16, 6
NCOL = 54  # a calendar year touches at most 54 Sunday-started weeks
X0 = 135  # centre of column 1
TOP = 96  # top edge of the first plate
PAD = 9  # plate edge to first well edge
ROW_H = 7 * PITCH + 2 * PAD
STRIDE = 9 * PITCH  # plate pitch; a multiple of PITCH so one well pattern lines up on every plate
STEP = 0.02  # scan speed, seconds per column


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body or not body.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {body.get('errors')}")
    return body["data"]["user"]


def fetch_years(login, token, today):
    first = int(gql(CREATED, {"login": login}, token)["createdAt"][:4])
    years = {}
    for y in range(first, today.year + 1):
        v = {"login": login, "from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"}
        years[y] = gql(YEAR, v, token)["contributionsCollection"]["contributionCalendar"]
    return years


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


def week_col(date, year):
    """Column of `date` on its year's plate; column 0 is the week (Sunday start) holding 1 January."""
    jan1 = dt.date(year, 1, 1)
    first_sunday = jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)
    return (date - first_sunday).days // 7


def render(login, years, today):
    all_days = [d for cal in years.values() for w in cal["weeks"] for d in w["contributionDays"]]
    cuts = quartile_cuts([d["contributionCount"] for d in all_days])
    total = sum(cal["totalContributions"] for cal in years.values())
    grid_w = NCOL * PITCH
    px0, px1 = X0 - PITCH / 2 - PAD, X0 - PITCH / 2 + grid_w + PAD
    grid_top = TOP + PAD

    out = []
    # month labels once, above the stack (each year's columns differ by at most one week)
    for m in range(1, 13):
        col = week_col(dt.date(today.year, m, 1), today.year)
        out.append(f'<text x="{X0 + col * PITCH - R:.1f}" y="{TOP - 12}" class="mo">{dt.date(2000, m, 1):%b}</text>')

    for k, (year, cal) in enumerate(sorted(years.items(), reverse=True)):
        top = TOP + k * STRIDE
        y0 = top + PAD + PITCH / 2  # centre of row A
        days = [d for w in cal["weeks"] for d in w["contributionDays"] if d["date"][:4] == str(year)]
        elapsed = [d for d in days if d["date"] <= today.isoformat()]
        active = sum(1 for d in elapsed if d["contributionCount"])
        rate = 100 * active / len(elapsed) if elapsed else 0

        # plate with a chamfered A1 corner, then empty wells from the shared pattern
        out.append(
            f'<path d="M{px0 + 10:.1f},{top} H{px1 - 8:.1f} a8,8 0 0 1 8,8 V{top + ROW_H - 8} a8,8 0 0 1 -8,8 '
            f'H{px0 + 8:.1f} a8,8 0 0 1 -8,-8 V{top + 10} Z" fill="{PLATE}" stroke="{EDGE}" stroke-width="1.2"/>'
        )
        out.append(f'<rect x="{X0 - PITCH / 2:.1f}" y="{top + PAD}" width="{grid_w}" height="{7 * PITCH}" fill="url(#wells)"/>')
        for i, letter in enumerate("ABCDEFG"):
            out.append(f'<text x="{px0 - 12:.1f}" y="{y0 + i * PITCH + 3.5:.1f}" class="rn">{letter}</text>')
        out.append(f'<text x="30" y="{top + ROW_H / 2 + 8:.1f}" class="yr{" now" * (year == today.year)}">{year}</text>')

        for d in days:
            lv = level(d["contributionCount"], cuts)
            if not lv:
                continue
            col = week_col(dt.date.fromisoformat(d["date"]), year)
            out.append(
                f'<circle cx="{X0 + col * PITCH:.1f}" cy="{y0 + d["weekday"] * PITCH:.1f}" r="{R}" fill="{RAMP[lv - 1]}" '
                f'class="hit{" top" * (lv == 4)}" style="animation-delay:{k * .15 + col * STEP + .2:.2f}s"/>'
            )
        if year == today.year:
            # wells after this week have not been read yet
            col = week_col(today, year) + 1
            if col < NCOL:
                out.append(
                    f'<rect x="{X0 + col * PITCH - PITCH / 2:.1f}" y="{top + PAD}" width="{(NCOL - col) * PITCH}" '
                    f'height="{7 * PITCH}" fill="{PLATE}" opacity=".75"/>'
                )
        sx = px1 + 30
        out.append(f'<text x="{sx:.0f}" y="{top + ROW_H / 2 - 2:.1f}" class="big">{cal["totalContributions"]:,}</text>')
        out.append(f'<text x="{sx:.0f}" y="{top + ROW_H / 2 + 20:.1f}" class="sub">{rate:.0f}% hit rate</text>')

    h = TOP + (len(years) - 1) * STRIDE + ROW_H + 64
    legend_x = W - 230
    legend = "".join(
        f'<circle cx="{legend_x + 55 + k * 20}" cy="{h - 30}" r="{R}" ' + (f'fill="{RAMP[k - 1]}"' if k else 'class="well"') + "/>"
        for k in range(5)
    )
    span = f"{min(years)}–{max(years)}"
    body = "\n  ".join(out)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h:.0f}" width="{W}" height="{h:.0f}" role="img" aria-label="{escape(login)}'s contributions {span} as a stack of assay plates, one per year: {total:,} contributions in total.">
  <style>
    .title {{ font:700 19px {MONO}; fill:{TEXT}; letter-spacing:2px; }}
    .sub {{ font:400 14px {MONO}; fill:{MUTED}; }}
    .big {{ font:700 22px {MONO}; fill:{TEXT}; }}
    .yr {{ font:700 24px {MONO}; fill:{MUTED}; }}
    .now {{ fill:{TEAL}; }}
    .rn {{ font:700 10px {MONO}; fill:{MUTED}; text-anchor:middle; }}
    .mo {{ font:400 14px {MONO}; fill:{MUTED}; }}
    .well {{ fill:{EMPTY}; stroke:{EDGE}; stroke-width:1; }}
    .top {{ stroke:#a7f3ec; stroke-width:1.2; }}
    .hit {{ opacity:0; animation:read .5s ease-out forwards; }}
    @keyframes read {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
    @media (prefers-reduced-motion: reduce) {{ .hit {{ animation:none; opacity:1; }} }}
  </style>
  <defs>
    <pattern id="wells" x="{X0 - PITCH / 2:.1f}" y="{grid_top}" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse"><circle cx="{PITCH / 2}" cy="{PITCH / 2}" r="{R}" class="well"/></pattern>
  </defs>
  <rect width="{W}" height="{h:.0f}" rx="14" fill="{BG}"/>
  <text x="40" y="44" class="title">PLATE STACK · {escape(login)}</text>
  <text x="{W - 40}" y="44" class="sub" text-anchor="end">1 plate = 1 year · 1 well = 1 day · <tspan style="fill:{TEAL};font-weight:700">{total:,}</tspan> contributions since {min(years)}</text>
  {body}
  <text x="40" y="{h - 25}" class="sub">signal quartiles over all active days · data: GitHub GraphQL</text>
  <text x="{legend_x}" y="{h - 25}" class="sub">none</text>{legend}<text x="{legend_x + 55 + 4 * 20 + 14}" y="{h - 25}" class="sub">high</text>
</svg>
'''


if __name__ == "__main__":
    login = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REPOSITORY_OWNER", "0rkhann")
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/plate.svg"
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    assert longest_run([1, 1, 0, 1, 1, 1, 0]) == 3
    assert [level(c, [1, 3, 6]) for c in (0, 1, 2, 4, 9)] == [0, 1, 2, 3, 4]
    assert week_col(dt.date(2022, 1, 1), 2022) == 0 and week_col(dt.date(2022, 12, 31), 2022) == 52
    assert STRIDE % PITCH == 0 and STRIDE > ROW_H
    today = dt.date.today()
    years = fetch_years(login, token, today)
    with open(out, "w") as f:
        f.write(render(login, years, today))
    print(f"wrote {out}: {len(years)} plates, {sum(c['totalContributions'] for c in years.values())} contributions")
