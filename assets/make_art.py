"""Generate the animated hero and divider SVGs for the profile README.

Run: uv run --with rdkit python assets/make_art.py
"""
import random

from rdkit import Chem
from rdkit.Chem import rdDepictor

BG, PANEL, TEAL, DIM, TEXT, MUTED = "#0d1117", "#111a24", "#4FD1C5", "#1f6f6a", "#e6edf3", "#8b949e"
ATOM_COLOR = {"N": "#7aa2ff", "O": "#ff7b72", "S": "#e3b341"}
SMILES = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # caffeine
W, H = 1200, 320


def molecule(cx, cy, scale):
    mol = Chem.MolFromSmiles(SMILES)
    Chem.Kekulize(mol, clearAromaticFlags=True)
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    pts = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
    mx = sum(p.x for p in pts) / len(pts)
    my = sum(p.y for p in pts) / len(pts)
    xy = [(cx + (p.x - mx) * scale, cy - (p.y - my) * scale) for p in pts]

    out = []
    for i, b in enumerate(mol.GetBonds()):
        (x1, y1), (x2, y2) = xy[b.GetBeginAtomIdx()], xy[b.GetEndAtomIdx()]
        d = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
        delay = 0.12 * i
        out.append(f'<path class="bond" d="{d}" style="animation-delay:{delay:.2f}s"/>')
        if b.GetBondTypeAsDouble() == 2:
            # second line of a double bond, offset towards the ring centre (or the molecule centre)
            ring = next((r for r in mol.GetRingInfo().AtomRings() if b.GetBeginAtomIdx() in r and b.GetEndAtomIdx() in r), None)
            ref = ring or range(mol.GetNumAtoms())
            rx = sum(xy[k][0] for k in ref) / len(ref)
            ry = sum(xy[k][1] for k in ref) / len(ref)
            dx, dy = x2 - x1, y2 - y1
            n = (dx * dx + dy * dy) ** 0.5
            ox, oy = -dy / n * 8, dx / n * 8
            mx2, my2 = (x1 + x2) / 2, (y1 + y2) / 2
            if (rx - mx2) * ox + (ry - my2) * oy < 0:
                ox, oy = -ox, -oy
            d2 = f"M{x1 + ox + dx * .15:.1f},{y1 + oy + dy * .15:.1f} L{x2 + ox - dx * .15:.1f},{y2 + oy - dy * .15:.1f}"
            out.append(f'<path class="bond thin" d="{d2}" style="animation-delay:{delay + .06:.2f}s"/>')
    t0 = 0.12 * mol.GetNumBonds()
    for i, a in enumerate(mol.GetAtoms()):
        x, y = xy[i]
        sym = a.GetSymbol()
        delay = t0 + 0.05 * i
        if sym == "C":
            out.append(f'<circle class="atom" cx="{x:.1f}" cy="{y:.1f}" r="4.5" style="animation-delay:{delay:.2f}s"/>')
        else:
            c = ATOM_COLOR.get(sym, TEAL)
            out.append(
                f'<g class="atom" style="animation-delay:{delay:.2f}s">'
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
    taglines = ["Teaching machines to read molecules", "LLM agents for chemistry literature", "Mapping chemical space, one embedding at a time"]
    tl = "\n    ".join(
        f'<text x="560" y="230" class="tag" style="animation-delay:{4 * i}s">&gt; {t}<tspan class="caret">_</tspan></text>'
        for i, t in enumerate(taglines)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Orkhan Abdullayev, Chemoinformatics and AI Engineering">
  <style>
    .bond {{ fill:none; stroke:{TEAL}; stroke-width:3; stroke-linecap:round; stroke-dasharray:120; stroke-dashoffset:120; animation:draw .5s ease-out forwards; }}
    .thin {{ stroke-width:2; opacity:.7; }}
    .atom {{ fill:{TEAL}; opacity:0; animation:pop .4s ease-out forwards; }}
    .sym {{ font:700 15px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; text-anchor:middle; }}
    .dot {{ fill:{DIM}; animation:drift ease-in-out infinite alternate; }}
    .mol {{ animation:float 6s ease-in-out 3s infinite; }}
    .name {{ font:700 54px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif; fill:{TEXT}; }}
    .role {{ font:500 22px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif; fill:{TEAL}; letter-spacing:3px; }}
    .meta {{ font:400 16px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; fill:{MUTED}; }}
    .tag {{ font:400 18px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; fill:{TEXT}; opacity:0; animation:cycle 12s linear infinite; }}
    .caret {{ fill:{TEAL}; animation:blink 1s steps(1) infinite; }}
    @keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
    @keyframes pop {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
    @keyframes drift {{ from {{ transform:translate(0,0); opacity:.25; }} to {{ transform:translate(14px,-10px); opacity:.9; }} }}
    @keyframes float {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-6px); }} }}
    @keyframes cycle {{ 0% {{ opacity:0; }} 3%,30% {{ opacity:1; }} 33%,100% {{ opacity:0; }} }}
    @keyframes blink {{ 50% {{ opacity:0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} .bond {{ stroke-dashoffset:0; }} .atom, .tag:first-of-type {{ opacity:1; }} }}
  </style>
  <rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="none" stroke="#21262d"/>
  <g>
    {space_dots(70, 7)}
  </g>
  <g class="mol">
    {molecule(300, 165, 68)}
  </g>
  <text x="560" y="120" class="name">Orkhan Abdullayev</text>
  <text x="562" y="160" class="role">CHEMOINFORMATICS · AI ENGINEERING</text>
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


if __name__ == "__main__":
    for name, svg in [("hero.svg", hero()), ("divider.svg", divider())]:
        with open(f"assets/{name}", "w") as f:
            f.write(svg)
        print("wrote", name)
