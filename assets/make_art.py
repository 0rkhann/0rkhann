"""Generate the static SVGs for the profile README: hero, divider and periodic-table toolbox.

Run: uv run --with rdkit python assets/make_art.py
"""
import random
import re
from xml.sax.saxutils import escape

from rdkit import Chem
from rdkit.Chem import rdDepictor

# one palette per GitHub theme; build() swaps them into these module names before drawing
THEMES = {
    "dark": dict(BG="#0d1117", PANEL="#111a24", TEAL="#4FD1C5", DIM="#1f6f6a", TEXT="#e6edf3", MUTED="#8b949e",
                 EDGE="#21262d", TILE="#0d1117", NAME="#c9d1d9",
                 ATOM_COLOR={"N": "#7aa2ff", "O": "#ff7b72", "S": "#e3b341"},
                 FAM={"ml": "#7aa2ff", "chem": "#4FD1C5", "ai": "#ff9e64", "infra": "#e3b341"}),
    "light": dict(BG="#f6f8fa", PANEL="#ffffff", TEAL="#0b7285", DIM="#9fd3cd", TEXT="#1f2328", MUTED="#59636e",
                  EDGE="#d0d7de", TILE="#ffffff", NAME="#1f2328",
                  ATOM_COLOR={"N": "#3b5bdb", "O": "#d6336c", "S": "#9c6f00"},
                  FAM={"ml": "#3b5bdb", "chem": "#0b7285", "ai": "#d9480f", "infra": "#9c6f00"}),
}
globals().update(THEMES["dark"])
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
    .base {{ fill:none; stroke:{MUTED}; stroke-opacity:.3; stroke-width:1.5; }}
    .pulse {{ fill:none; stroke:{TEAL}; stroke-width:2.5; stroke-linecap:round; stroke-dasharray:90 2400; animation:run 6s linear infinite; }}
    @keyframes run {{ from {{ stroke-dashoffset:90; }} to {{ stroke-dashoffset:-2400; }} }}
    @media (prefers-reduced-motion: reduce) {{ .pulse {{ animation:none; }} }}
  </style>
  <path class="base" d="{path}"/>
  <path class="pulse" d="{path}"/>
</svg>
'''


# periodic-table toolbox: families set the tile colour
FAMILIES = {"ml": "Machine & deep learning", "chem": "Chemistry", "ai": "AI & agents", "infra": "Infrastructure"}
# (row, column, symbol, name, family) on a 7-column grid shaped like the periodic table:
# two corner tiles on top, two-and-two in the middle, a full bottom row
ELEMENTS = [
    (0, 0, "Py", "Python", "ml"), (0, 6, "Rd", "RDKit", "chem"),
    (1, 0, "Pt", "PyTorch", "ml"), (1, 1, "Sk", "scikit-learn", "ml"),
    (1, 5, "Lx", "Linux", "infra"), (1, 6, "Dk", "Docker", "infra"),
    (2, 0, "Hf", "Hugging Face", "ml"), (2, 1, "Bo", "Bayesian optimisation", "ml"),
    (2, 2, "Lm", "LLMs", "ai"), (2, 3, "Ag", "AI agents", "ai"), (2, 4, "Cl", "Claude", "ai"),
    (2, 5, "Gt", "Git", "infra"), (2, 6, "Aw", "AWS", "infra"),
]


def toolbox():
    """Tools as element tiles laid out in the periodic table's silhouette."""
    tw, th, gap = 120, 132, 10
    ncol = 1 + max(c for _, c, *_ in ELEMENTS)
    nrow = 1 + max(r for r, *_ in ELEMENTS)
    width = ncol * (tw + gap) - gap

    def name_lines(cx, y, name):
        # names wider than a tile wrap onto two lines
        if len(name) <= 13 or " " not in name:
            return f'<text x="{cx:.0f}" y="{y + 108}" class="nm">{escape(name)}</text>'
        first, rest = name.split(" ", 1)
        return (f'<text x="{cx:.0f}" y="{y + 100}" class="nm">{escape(first)}</text>'
                f'<text x="{cx:.0f}" y="{y + 119}" class="nm">{escape(rest)}</text>')

    out = []
    # atomic numbers run row by row, like the real table
    for z, (r, c, sym, name, fam) in enumerate(sorted(ELEMENTS), start=1):
        color = FAM[fam]
        x, y = c * (tw + gap), r * (th + gap)
        out.append(
            f'<g class="el" style="animation-delay:{(z - 1) * .05:.2f}s">'
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="10" fill="{TILE}"/>'  # opaque base under the tint
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="10" fill="{color}" fill-opacity=".1" stroke="{color}" stroke-opacity=".55" stroke-width="1.5"/>'
            f'<text x="{x + 12}" y="{y + 22}" class="z">{z}</text>'
            f'<text x="{x + tw / 2:.0f}" y="{y + 74}" class="sym" fill="{color}">{sym}</text>'
            + name_lines(x + tw / 2, y, name) + "</g>"
        )
    # legend sits midway between the last row and the README divider below the image
    ly = nrow * (th + gap) + 30
    legend, lx = [], 0.0
    for key, fam in FAMILIES.items():
        color = FAM[key]
        legend.append(f'<rect x="{lx:.0f}" y="{ly - 11}" width="12" height="12" rx="3" fill="{color}" fill-opacity=".35" stroke="{color}"/>'
                      f'<text x="{lx + 20:.0f}" y="{ly}" class="lg">{escape(fam)}</text>')
        lx += 20 + 9.8 * len(fam) + 30
    shift = (width - (lx - 30)) / 2
    h = ly + 5
    names = escape(", ".join(e[3] for e in sorted(ELEMENTS)))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" width="{width}" height="{h}" role="img" aria-label="Toolbox as a periodic table: {names}">
  <style>
    .z {{ font:500 14px {MONO}; fill:{MUTED}; }}
    .sym {{ font:700 46px {SANS}; text-anchor:middle; }}
    .nm {{ font:500 16px {SANS}; fill:{NAME}; text-anchor:middle; }}
    .lg {{ font:400 16px {MONO}; fill:{MUTED}; }}
    .el {{ opacity:0; animation:in .5s ease-out forwards; }}
    @keyframes in {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:none; }} }}
    @media (prefers-reduced-motion: reduce) {{ .el {{ animation:none; opacity:1; }} }}
  </style>
  {"".join(out)}
  <g transform="translate({shift:.0f} 0)">{"".join(legend)}</g>
</svg>
'''


if __name__ == "__main__":
    for theme, palette in THEMES.items():
        globals().update(palette)
        for name, svg in [("hero", hero()), ("divider", divider()), ("toolbox", toolbox())]:
            with open(f"assets/{name}-{theme}.svg", "w") as f:
                f.write(svg)
            print(f"wrote {name}-{theme}.svg")
