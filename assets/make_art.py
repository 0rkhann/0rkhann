"""Generate the static SVGs for the profile README: hero, divider and the vendored toolbox.

Run: uv run --with rdkit python assets/make_art.py
"""
import math
import os
import random
import re
import urllib.request

from rdkit import Chem
from rdkit.Chem import rdDepictor

BG, PANEL, TEAL, DIM, TEXT, MUTED, EDGE = "#0d1117", "#111a24", "#4FD1C5", "#1f6f6a", "#e6edf3", "#8b949e", "#21262d"
ATOM_COLOR = {"N": "#7aa2ff", "O": "#ff7b72", "S": "#e3b341"}
SMILES = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # caffeine
W, H = 1200, 320
SANS = '-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# hero timing: one SMILES token every STEP seconds, whole loop lasts PERIOD seconds
STEP, PERIOD = 0.22, 18
TOKEN_RE = re.compile(r"(\[[^\]]+]|Br|Cl|[BCNOSPFIbcnosp]|\(|\)|\.|=|#|-|\+|\\|/|:|~|@|\*|\$|%\d{2}|\d)")
ATOM_TOKEN = re.compile(r"^(\[.*]|Br|Cl|[BCNOSPFIbcnosp])$")


def tokens_with_atoms(smiles):
    """Return [(token, atom_index_or_None)] in SMILES order; RDKit numbers atoms in that order."""
    toks = TOKEN_RE.findall(smiles)
    assert "".join(toks) == smiles, "tokenizer dropped characters"
    out, k = [], 0
    for t in toks:
        if ATOM_TOKEN.match(t):
            out.append((t, k))
            k += 1
        else:
            out.append((t, None))
    return out


def de_novo(cx, cy, scale, text_y):
    mol = Chem.MolFromSmiles(SMILES)
    Chem.Kekulize(mol, clearAromaticFlags=True)
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    pts = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
    mx = sum(p.x for p in pts) / len(pts)
    my = sum(p.y for p in pts) / len(pts)
    xy = [(cx + (p.x - mx) * scale, cy - (p.y - my) * scale) for p in pts]

    toks = tokens_with_atoms(SMILES)
    assert sum(a is not None for _, a in toks) == mol.GetNumAtoms()
    atom_t = {a: i * STEP for i, (_, a) in enumerate(toks) if a is not None}

    out = []
    # SMILES string typed out under the molecule, one token at a time
    cw = 10.2
    x0 = cx - len(SMILES) * cw / 2
    out.append(f'<text x="{x0 - 14:.1f}" y="{text_y}" class="smi" style="fill:{TEAL}" text-anchor="end">▸</text>')
    col = 0
    for i, (t, _) in enumerate(toks):
        out.append(
            f'<text x="{x0 + col * cw:.1f}" y="{text_y}" class="smi gen" textLength="{len(t) * cw:.1f}" '
            f'style="animation-delay:{i * STEP:.2f}s">{t}</text>'
        )
        col += len(t)

    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        (x1, y1), (x2, y2) = xy[i], xy[j]
        delay = max(atom_t[i], atom_t[j]) + 0.05
        out.append(f'<path class="bond" d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" style="animation-delay:{delay:.2f}s"/>')
        if b.GetBondTypeAsDouble() == 2:
            # second line of a double bond, offset towards the ring centre (or the molecule centre)
            ring = next((r for r in mol.GetRingInfo().AtomRings() if i in r and j in r), None)
            ref = ring or range(mol.GetNumAtoms())
            rx = sum(xy[k][0] for k in ref) / len(ref)
            ry = sum(xy[k][1] for k in ref) / len(ref)
            dx, dy = x2 - x1, y2 - y1
            n = (dx * dx + dy * dy) ** 0.5
            ox, oy = -dy / n * 8, dx / n * 8
            if (rx - (x1 + x2) / 2) * ox + (ry - (y1 + y2) / 2) * oy < 0:
                ox, oy = -ox, -oy
            d2 = f"M{x1 + ox + dx * .15:.1f},{y1 + oy + dy * .15:.1f} L{x2 + ox - dx * .15:.1f},{y2 + oy - dy * .15:.1f}"
            out.append(f'<path class="bond thin" d="{d2}" style="animation-delay:{delay + .08:.2f}s"/>')

    for a in mol.GetAtoms():
        i = a.GetIdx()
        x, y = xy[i]
        sym = a.GetSymbol()
        delay = f"{atom_t[i]:.2f}"
        if sym == "C":
            out.append(f'<circle class="atom" cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{TEAL}" style="animation-delay:{delay}s"/>')
        else:
            c = ATOM_COLOR.get(sym, TEAL)
            out.append(
                f'<g class="atom" style="animation-delay:{delay}s">'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="{PANEL}" stroke="{c}" stroke-width="2"/>'
                f'<text x="{x:.1f}" y="{y + 5.5:.1f}" fill="{c}" class="sym">{sym}</text></g>'
            )
    return "\n    ".join(out)


def space_dots(n, seed):
    rnd = random.Random(seed)
    dots = []
    for _ in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([1.2, 1.6, 2.2])
        dur = rnd.uniform(6, 14)
        delay = rnd.uniform(0, 6)
        dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" class="dot" style="animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s"/>')
    return "\n    ".join(dots)


def hero():
    taglines = ["Teaching machines to read molecules", "LLM agents for chemistry", "De novo design: molecules that don't exist yet"]
    tl = "\n    ".join(
        f'<text x="560" y="232" class="tag" style="animation-delay:{4 * i}s">&gt; {t}<tspan class="caret">_</tspan></text>'
        for i, t in enumerate(taglines)
    )
    # each element shares one looping keyframe; its delay sets when it is "generated"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Orkhan Abdullayev, Chemoinformatics and AI Engineering. Caffeine generated token by token from its SMILES.">
  <style>
    .bond {{ fill:none; stroke:{TEAL}; stroke-width:3; stroke-linecap:round; stroke-dasharray:120; stroke-dashoffset:120; animation:draw {PERIOD}s ease-out infinite backwards; }}
    .thin {{ stroke-width:2; stroke-opacity:.7; }}
    .atom, .gen {{ opacity:0; animation:gen {PERIOD}s ease-out infinite backwards; }}
    .sym {{ font:700 15px {MONO}; text-anchor:middle; }}
    .smi {{ font:500 17px {MONO}; fill:{TEXT}; }}
    .dot {{ fill:{DIM}; animation:drift ease-in-out infinite alternate; }}
    .name {{ font:700 54px {SANS}; fill:{TEXT}; }}
    .role {{ font:500 24px {SANS}; fill:{TEAL}; letter-spacing:3px; }}
    .meta {{ font:400 18px {MONO}; fill:{MUTED}; }}
    .tag {{ font:400 20px {MONO}; fill:{TEXT}; opacity:0; animation:cycle 12s linear infinite; }}
    .caret {{ fill:{TEAL}; animation:blink 1s steps(1) infinite; }}
    @keyframes gen {{ 0% {{ opacity:0; }} 2.5%, 74% {{ opacity:1; }} 78%, 100% {{ opacity:0; }} }}
    @keyframes draw {{ 0% {{ stroke-dashoffset:120; opacity:1; }} 3%, 74% {{ stroke-dashoffset:0; opacity:1; }} 78%, 100% {{ stroke-dashoffset:0; opacity:0; }} }}
    @keyframes drift {{ from {{ transform:translate(0,0); opacity:.25; }} to {{ transform:translate(14px,-10px); opacity:.9; }} }}
    @keyframes cycle {{ 0% {{ opacity:0; }} 3%, 30% {{ opacity:1; }} 33%, 100% {{ opacity:0; }} }}
    @keyframes blink {{ 50% {{ opacity:0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} .bond {{ stroke-dashoffset:0; }} .atom, .gen, .tag:first-of-type {{ opacity:1; }} }}
  </style>
  <rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="none" stroke="{EDGE}"/>
  <g>
    {space_dots(70, 7)}
  </g>
  <g>
    {de_novo(300, 140, 56, 292)}
  </g>
  <text x="560" y="118" class="name">Orkhan Abdullayev</text>
  <text x="562" y="158" class="role">CHEMOINFORMATICS · AI ENGINEERING</text>
  <text x="562" y="190" class="meta">Strasbourg, FR  ·  SMILES in, insight out</text>
  <g>
    {tl}
  </g>
</svg>
'''


def divider():
    # a polyacene-like zigzag of hexagon edges with a pulse travelling along it
    pts, x, up = [], 0.0, True
    while x <= W:
        pts.append(f"{x:.1f},{14 if up else 26}")
        x += 17.3
        up = not up
    path = "M" + " L".join(pts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 40" width="{W}" height="40" role="img" aria-label="divider">
  <style>
    .base {{ fill:none; stroke:#8b949e; stroke-opacity:.3; stroke-width:1.5; }}
    .pulse {{ fill:none; stroke:{TEAL}; stroke-width:2.5; stroke-linecap:round; stroke-dasharray:90 2400; animation:run 6s linear infinite; }}
    @keyframes run {{ from {{ stroke-dashoffset:90; }} to {{ stroke-dashoffset:-2400; }} }}
    @media (prefers-reduced-motion: reduce) {{ .pulse {{ animation:none; }} }}
  </style>
  <path class="base" d="{path}"/>
  <path class="pulse" d="{path}"/>
</svg>
'''


def glyphs():
    """Teal line icons for the project table, one per project."""
    def tile(body):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
                f'<rect width="32" height="32" rx="8" fill="{BG}"/>'
                f'<g fill="none" stroke="{TEAL}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>')

    def pt(cx, cy, r, deg):
        a = math.radians(deg)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    # chemlit: a paper under a magnifier
    chemlit = ('<path d="M8,6 H18 L23,11 V26 H8 Z"/><path d="M18,6 V11 H23"/><path d="M11,15 H19 M11,19 H15"/>'
               f'<circle cx="21" cy="22" r="4" fill="{BG}"/><path d="M24,25 L27.5,28.5"/>')

    # MicroKatc: a catalytic cycle, three intermediates joined by arrows
    nodes = [pt(16, 16, 9, a) for a in (-90, 30, 150)]
    arcs = "".join(f'<path d="M{pt(16, 16, 9, a + 18)[0]:.1f},{pt(16, 16, 9, a + 18)[1]:.1f} A9,9 0 0 1 {pt(16, 16, 9, a + 102)[0]:.1f},{pt(16, 16, 9, a + 102)[1]:.1f}"/>'
                   for a in (-90, 30, 150))
    heads = ""
    for a in (-90, 30, 150):
        x, y = pt(16, 16, 9, a + 102)
        t = math.radians(a + 102 + 90)  # tangent direction
        for side in (-1, 1):
            hx = x - 3.2 * math.cos(t) + side * 2.2 * math.cos(t + math.pi / 2)
            hy = y - 3.2 * math.sin(t) + side * 2.2 * math.sin(t + math.pi / 2)
            heads += f'<path d="M{x:.1f},{y:.1f} L{hx:.1f},{hy:.1f}"/>'
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{TEAL}" stroke="none"/>' for x, y in nodes)
    microkatc = arcs + heads + dots

    # BO project: an N-heterocyclic carbene (imidazol-2-ylidene) with its lone pair
    ring = [pt(16, 18.5, 7.5, a) for a in (-90, -18, 54, 126, 198)]
    poly = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ring) + " Z"
    (x3, y3), (x4, y4) = ring[2], ring[3]
    inner = f'<path d="M{x3 - 1.2:.1f},{y3 - 2:.1f} L{x4 + 1.2:.1f},{y4 - 2:.1f}" stroke-width="1.3"/>'
    ns = "".join(f'<circle cx="{ring[i][0]:.1f}" cy="{ring[i][1]:.1f}" r="2.4" fill="#7aa2ff" stroke="none"/>' for i in (1, 4))
    subs = f'<path d="M{ring[1][0]:.1f},{ring[1][1]:.1f} l4,-2.5 M{ring[4][0]:.1f},{ring[4][1]:.1f} l-4,-2.5"/>'
    pair = f'<circle cx="14.4" cy="7" r="1.2" fill="{TEAL}" stroke="none"/><circle cx="17.6" cy="7" r="1.2" fill="{TEAL}" stroke="none"/>'
    bo = f'<path d="{poly}"/>' + inner + subs + ns + pair

    # neptune: a peptide backbone with side chains
    zig = [(5, 19), (10, 14), (15, 19), (20, 14), (25, 19), (28, 15)]
    backbone = "M" + " L".join(f"{x},{y}" for x, y in zig)
    side = "".join(f'<path d="M{x},{y} V{y - 5 if y < 17 else y + 5}"/><circle cx="{x}" cy="{y - 7 if y < 17 else y + 7}" r="1.8" fill="{TEAL}" stroke="none"/>'
                   for x, y in zig[1:5])
    neptune = f'<path d="{backbone}"/>' + side

    # CoLiNN: a GTM chemical space map with density contours
    colinn = ('<rect x="5" y="5" width="22" height="22" rx="3"/>'
              '<path d="M10,20 C9,14 15,10 20,12 C25,14 24,22 18,23 C14,24 11,23 10,20 Z" stroke-opacity=".55"/>'
              '<path d="M14,19 C13.5,16 17,14.5 19,16 C21,17.5 19.5,20.5 17,20.5 C15.5,20.5 14.3,20 14,19 Z"/>'
              + "".join(f'<circle cx="{x}" cy="{y}" r="1.1" fill="{TEAL}" stroke="none"/>' for x, y in ((9, 9), (23, 9), (8, 24), (24, 25), (17, 18))))

    return {"chemlit": tile(chemlit), "microkatc": tile(microkatc), "bo": tile(bo), "neptune": tile(neptune), "colinn": tile(colinn)}


SKILLICONS = "https://skillicons.dev/icons?i=python,pytorch,sklearn,linux,bash,docker,git&theme=dark&perline=7"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-art"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def toolbox():
    """Skill icons vendored into one SVG, with the Claude tile first: one request instead of third-party ones."""
    icon_pitch = 300 / 256 * 48  # skillicons spacing
    icons = get(SKILLICONS).strip()
    icons_w = float(re.search(r'width="([\d.]+)"', icons).group(1))
    claude = open("assets/claude-tile.svg").read()
    tw = icon_pitch + icons_w

    def nest(svg, x):
        return re.sub(r"^\s*<svg", f'<svg x="{x:.2f}" y="0"', svg, count=1)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {tw:.0f} 48" width="{tw:.0f}" height="48" role="img" aria-label="Toolbox: Claude, Python, PyTorch, scikit-learn, Linux, Bash, Docker, Git">
{nest(claude, 0)}{nest(icons, icon_pitch)}
</svg>
'''


if __name__ == "__main__":
    files = [("hero.svg", hero()), ("divider.svg", divider()), ("toolbox.svg", toolbox())]
    files += [(f"glyphs/{k}.svg", v) for k, v in glyphs().items()]
    os.makedirs("assets/glyphs", exist_ok=True)
    for name, svg in files:
        with open(f"assets/{name}", "w") as f:
            f.write(svg)
        print("wrote", name)
