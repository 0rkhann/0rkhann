"""Generate the static animated SVGs for the profile README: hero, agent trace, divider.

Run: uv run --with rdkit python assets/make_art.py
"""
import random
import re

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
    .role {{ font:500 22px {SANS}; fill:{TEAL}; letter-spacing:3px; }}
    .meta {{ font:400 16px {MONO}; fill:{MUTED}; }}
    .tag {{ font:400 18px {MONO}; fill:{TEXT}; opacity:0; animation:cycle 12s linear infinite; }}
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


def agent():
    """Terminal card replaying the chemlit pipeline steps (taken from the chemlit README)."""
    steps = [
        ("expand", "plain-language rewrites, so other fields' vocabulary still matches"),
        ("search", "OpenAlex · Semantic Scholar · PubMed · arXiv · SPECTER2 neighbours"),
        ("rerank", "cross-encoder orders every candidate, an LLM judges relevance"),
        ("read", "legal open-access full text only; retractions dropped"),
        ("resolve", "OPSIN → PubChem → ChEMBL pipeline → RDKit alerts"),
        ("answer", "PaperQA2 with claim-level citations, every DOI checked"),
    ]
    period, gap, first = 14, 1.0, 1.4
    lines = []
    y0 = 108
    for i, (verb, what) in enumerate(steps):
        y = y0 + i * 30
        d = first + i * gap
        lines.append(
            f'<g class="step" style="animation-delay:{d:.1f}s">'
            f'<text x="56" y="{y}" class="mono dim">├─</text>'
            f'<text x="88" y="{y}" class="mono verb">{verb}</text>'
            f'<text x="190" y="{y}" class="mono txt">{what}</text></g>'
            f'<text x="1140" y="{y}" class="mono ok" text-anchor="end" style="animation-delay:{d + .6:.1f}s">✓</text>'
        )
    h = y0 + len(steps) * 30 + 26
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" aria-label="Animated replay of the chemlit agent pipeline: expand, search, rerank, read, resolve, answer.">
  <style>
    .mono {{ font:400 16px {MONO}; }}
    .dim {{ fill:#484f58; }} .verb {{ fill:{TEAL}; font-weight:700; }} .txt {{ fill:#c9d1d9; }} .ok {{ fill:{TEAL}; font-weight:700; }}
    .q {{ fill:{TEXT}; }} .p {{ fill:{TEAL}; }} .title {{ font:500 13px {MONO}; fill:{MUTED}; }}
    .step, .ok {{ opacity:0; animation:show {period}s ease-out infinite backwards; }}
    .caret {{ fill:{TEAL}; animation:blink 1s steps(1) infinite; }}
    @keyframes show {{ 0% {{ opacity:0; transform:translateX(-6px); }} 3%, 85% {{ opacity:1; transform:none; }} 90%, 100% {{ opacity:0; }} }}
    @keyframes blink {{ 50% {{ opacity:0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} .step, .ok {{ opacity:1; }} }}
  </style>
  <rect width="{W}" height="{h}" rx="14" fill="{BG}"/>
  <rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="13" fill="none" stroke="{EDGE}"/>
  <path d="M1,14 a13,13 0 0 1 13,-13 H{W - 14} a13,13 0 0 1 13,13 V38 H1 Z" fill="#161b22"/>
  <circle cx="24" cy="20" r="6" fill="#ff5f57"/><circle cx="44" cy="20" r="6" fill="#febc2e"/><circle cx="64" cy="20" r="6" fill="#28c840"/>
  <text x="{W // 2}" y="24" class="title" text-anchor="middle">chemlit · example run</text>
  <text x="32" y="74" class="mono"><tspan class="p">$ </tspan><tspan class="q">chemlit ask "Which covalent warheads target KRAS G12C?"</tspan><tspan class="caret"> ▍</tspan></text>
  {"".join(lines)}
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
    for name, svg in [("hero.svg", hero()), ("agent.svg", agent()), ("divider.svg", divider())]:
        with open(f"assets/{name}", "w") as f:
            f.write(svg)
        print("wrote", name)
