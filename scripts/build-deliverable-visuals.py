from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "livrables" / "visuals"
CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
)

NAVY = "#0B1F3A"
INK = "#17243B"
BLUE = "#2D65F2"
CYAN = "#06A6B5"
GREEN = "#28B487"
ORANGE = "#F59E0B"
PURPLE = "#7165E3"
RED = "#E35D6A"
MUTED = "#66758A"
PALE = "#F4F7FB"
WHITE = "#FFFFFF"
LINE = "#DCE4EF"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def shell(title: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}} html,body{{margin:0;width:1600px;height:900px;overflow:hidden;background:{PALE};font-family:'Segoe UI',Arial,sans-serif;color:{INK}}}
svg{{display:block;width:1600px;height:900px}} .title{{font-size:44px;font-weight:800;fill:{NAVY}}}.sub{{font-size:21px;font-weight:500;fill:{MUTED}}}
.h{{font-size:20px;font-weight:750;fill:{NAVY}}}.b{{font-size:16px;font-weight:500;fill:{MUTED}}}.small{{font-size:14px;font-weight:700;fill:{MUTED}}}
.white{{fill:{WHITE}}}.muted{{fill:{MUTED}}}.node{{fill:{WHITE};stroke:{LINE};stroke-width:2}}.shadow{{filter:url(#shadow)}}
</style></head><body><svg viewBox="0 0 1600 900" role="img" aria-label="{esc(title)}">
<defs><filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#0B1F3A" flood-opacity=".10"/></filter>
<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#91A2B6"/></marker></defs>
<rect width="1600" height="900" fill="{PALE}"/><rect x="0" y="0" width="18" height="900" fill="{CYAN}"/>
<text x="86" y="86" class="title">{esc(title)}</text><text x="88" y="126" class="sub">{esc(subtitle)}</text>{body}</svg></body></html>"""


def card(x: int, y: int, w: int, h: int, color: str, title: str, lines: list[str], icon: str) -> str:
    parts = [
        f'<g class="shadow"><rect class="node" x="{x}" y="{y}" width="{w}" height="{h}" rx="24"/>',
        f'<rect x="{x}" y="{y}" width="10" height="{h}" rx="5" fill="{color}"/>',
        f'<circle cx="{x+52}" cy="{y+48}" r="24" fill="{color}"/>',
        f'<text x="{x+52}" y="{y+55}" text-anchor="middle" font-size="18" font-weight="800" fill="white">{esc(icon)}</text>',
        f'<text x="{x+90}" y="{y+53}" class="h">{esc(title)}</text>',
    ]
    for i, line in enumerate(lines):
        parts.append(f'<text x="{x+34}" y="{y+98+i*27}" class="b">{esc(line)}</text>')
    parts.append('</g>')
    return "".join(parts)


def architecture() -> str:
    body = []
    nodes = [
        (70, 260, 250, 220, BLUE, "HAICOP", ["Données publiques", "Pages détail", "Documents"], "1"),
        (365, 210, 285, 320, CYAN, "Acquisition", ["Collecteur Python", "Validation HTTP", "PDF · DOCX · DOC", "OCR Tesseract"], "2"),
        (700, 225, 260, 290, GREEN, "PostgreSQL", ["Faits officiels", "Hashes & textes", "Analyses", "Registres d’envoi"], "3"),
        (1010, 190, 260, 360, PURPLE, "Intelligence", ["OpenClaw", "Profil OneTech", "Scoring Go/No-Go", "Skills + MCP", "Phi-4 Mini"], "4"),
        (1320, 260, 230, 220, ORANGE, "Diffusion", ["n8n", "Gmail", "Telegram"], "5"),
    ]
    for x, y, w, h, c, t, lines, icon in nodes:
        body.append(card(x, y, w, h, c, t, lines, icon))
    for x1, y1, x2, y2 in [(320,370,365,370),(650,370,700,370),(960,370,1010,370),(1270,370,1320,370)]:
        body.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#91A2B6" stroke-width="5" fill="none" marker-end="url(#arrow)"/>')
    body.append(f'<rect x="290" y="650" width="1020" height="105" rx="28" fill="{NAVY}"/>')
    body.append('<text x="800" y="696" text-anchor="middle" font-size="22" font-weight="800" fill="white">Une source de vérité · une analyse traçable · une diffusion sans doublon</text>')
    body.append('<text x="800" y="728" text-anchor="middle" font-size="16" font-weight="500" fill="#B8C8DC">Chaque étape conserve ses preuves et peut être rejouée sans dupliquer les données.</text>')
    return shell("Architecture de bout en bout", "De la publication HAICOP à la décision diffusée", "".join(body))


def documents() -> str:
    body = []
    stages = [
        (70, 250, BLUE, "Télécharger", "Domaine public + limites"),
        (350, 250, CYAN, "Identifier", "Type réel + SHA-256"),
        (630, 250, GREEN, "Extraire", "PDF texte + DOCX"),
        (910, 250, ORANGE, "Récupérer", "OCR scans + conversion DOC"),
        (1190, 250, PURPLE, "Persister", "Texte + statut PostgreSQL"),
    ]
    for i, (x, y, c, t, s) in enumerate(stages):
        body.append(f'<g class="shadow"><rect class="node" x="{x}" y="{y}" width="235" height="170" rx="24"/><circle cx="{x+42}" cy="{y+42}" r="24" fill="{c}"/><text x="{x+42}" y="{y+49}" text-anchor="middle" font-size="18" font-weight="800" fill="white">{i+1}</text><text x="{x+28}" y="{y+98}" class="h">{esc(t)}</text><text x="{x+28}" y="{y+132}" class="b">{esc(s)}</text></g>')
        if i < len(stages)-1:
            body.append(f'<path d="M{x+235} {y+85} L{x+275} {y+85}" stroke="#91A2B6" stroke-width="5" marker-end="url(#arrow)"/>')
    metrics = [("41","PDF",BLUE),("74","DOCX",CYAN),("35","anciens DOC",ORANGE),("2","images OCR",PURPLE),("152 / 152","textes extraits",GREEN)]
    for i,(v,l,c) in enumerate(metrics):
        x=75+i*300
        body.append(f'<g class="shadow"><rect class="node" x="{x}" y="550" width="255" height="155" rx="22"/><text x="{x+127}" y="610" text-anchor="middle" font-size="38" font-weight="850" fill="{c}">{esc(v)}</text><text x="{x+127}" y="653" text-anchor="middle" class="h">{esc(l)}</text></g>')
    return shell("Pipeline documentaire", "Une stratégie adaptée à chaque format, avec reprise idempotente", "".join(body))


def traceability() -> str:
    body = []
    lanes = [
        (195, BLUE, "Faits officiels", "appels_offres", ["tender_id", "organisme", "dates", "payload JSONB"]),
        (385, GREEN, "Preuves documentaires", "documents_ao", ["URL", "SHA-256", "texte extrait", "statut"]),
        (575, PURPLE, "Décision expliquée", "analyses_ao", ["contexte hashé", "score /100", "Go/No-Go", "fiche sourcée"]),
    ]
    for y,c,title,table,items in lanes:
        body.append(f'<rect x="80" y="{y}" width="255" height="128" rx="22" fill="{c}"/><text x="112" y="{y+45}" font-size="21" font-weight="800" fill="white">{esc(title)}</text><text x="112" y="{y+83}" font-size="16" font-weight="650" fill="#E9F0FA">{esc(table)}</text>')
        for i,item in enumerate(items):
            x=390+i*220
            body.append(f'<g class="shadow"><rect class="node" x="{x}" y="{y+8}" width="190" height="112" rx="20"/><circle cx="{x+24}" cy="{y+39}" r="8" fill="{c}"/><text x="{x+43}" y="{y+46}" font-size="17" font-weight="750" fill="{INK}">{esc(item)}</text></g>')
        body.append(f'<path d="M335 {y+64} L372 {y+64}" stroke="#91A2B6" stroke-width="5" marker-end="url(#arrow)"/>')
    body.append(f'<rect x="1290" y="195" width="250" height="508" rx="30" fill="{NAVY}"/>')
    body.append('<text x="1415" y="252" text-anchor="middle" font-size="22" font-weight="800" fill="white">Bénéfice</text>')
    for i,t in enumerate(["Audit possible","Rejeu sans doublon","Sources retrouvables","Historique conservé"]):
        y=325+i*83
        body.append(f'<circle cx="1330" cy="{y}" r="17" fill="{GREEN}"/><path d="M1322 {y} l7 7 l12 -15" stroke="white" stroke-width="4" fill="none"/><text x="1363" y="{y+7}" font-size="16" font-weight="700" fill="white">{esc(t)}</text>')
    return shell("Traçabilité des données", "Les faits, les preuves et le raisonnement restent séparés mais reliés", "".join(body))


def automation() -> str:
    body = []
    body.append(f'<rect x="80" y="200" width="1440" height="130" rx="32" fill="{NAVY}"/>')
    flow=[("08:00","n8n",ORANGE),("API","ao-worker",BLUE),("Mission","OpenClaw",PURPLE),("Pipeline","Python",CYAN),("État","PostgreSQL",GREEN)]
    for i,(k,t,c) in enumerate(flow):
        x=115+i*285
        body.append(f'<circle cx="{x+40}" cy="265" r="29" fill="{c}"/><text x="{x+40}" y="272" text-anchor="middle" font-size="14" font-weight="800" fill="white">{esc(k)}</text><text x="{x+82}" y="272" font-size="20" font-weight="800" fill="white">{esc(t)}</text>')
        if i<4: body.append(f'<path d="M{x+225} 265 L{x+265} 265" stroke="#8FA3BE" stroke-width="4" marker-end="url(#arrow)"/>')
    channels=[(120,470,BLUE,"Mailpit","preuve locale"),(550,470,RED,"Gmail","digest multi-destinataires"),(980,470,CYAN,"Telegram","digest + réponse aux mentions")]
    for x,y,c,t,s in channels:
        body.append(card(x,y,360,180,c,t,[s,"registre anti-doublon"],t[:2].upper()))
    body.append(f'<rect x="355" y="715" width="890" height="80" rx="22" fill="#E8F8F2" stroke="#BEE9D8" stroke-width="2"/><text x="800" y="765" text-anchor="middle" font-size="20" font-weight="800" fill="{GREEN}">Même relance → aucune notification envoyée deux fois</text>')
    return shell("Automatisation multicanale", "Un workflow planifié, traçable et rejouable", "".join(body))


def results() -> str:
    body=[]
    metrics=[("100","AO centralisées",BLUE),("152 / 152","documents traités",GREEN),("0","doublon détecté",CYAN),("67 / 67","tests Python",PURPLE),("6 / 6","scripts SQL",ORANGE),("5 / 5","outils MCP",BLUE)]
    for i,(v,l,c) in enumerate(metrics):
        row,col=divmod(i,3); x=85+col*505; y=190+row*235
        body.append(f'<g class="shadow"><rect class="node" x="{x}" y="{y}" width="445" height="190" rx="28"/><rect x="{x}" y="{y}" width="12" height="190" rx="6" fill="{c}"/><text x="{x+42}" y="{y+82}" font-size="48" font-weight="850" fill="{c}">{esc(v)}</text><text x="{x+42}" y="{y+130}" class="h">{esc(l)}</text></g>')
    body.append(f'<rect x="250" y="705" width="1100" height="82" rx="24" fill="{NAVY}"/><text x="800" y="756" text-anchor="middle" font-size="21" font-weight="800" fill="white">Collecter · comprendre · décider · diffuser — avec une preuve à chaque étape</text>')
    return shell("Résultats validés", "Un MVP complet, mesuré sur des données et documents réels", "".join(body))


VISUALS = {
    "architecture_v2": architecture,
    "pipeline_documents": documents,
    "traceability_data": traceability,
    "automation_channels": automation,
    "results_dashboard": results,
}


def render(html_path: Path, png_path: Path, chrome: Path) -> None:
    subprocess.run(
        [str(chrome), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=1", "--window-size=1600,900",
         f"--screenshot={png_path}", html_path.as_uri()],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    chrome = next((p for p in CHROME_CANDIDATES if p.exists()), None)
    if chrome is None:
        raise RuntimeError("Google Chrome est requis pour rendre les visuels.")
    for name, builder in VISUALS.items():
        html_path = OUT / f"{name}.html"
        png_path = OUT / f"{name}.png"
        html_path.write_text(builder(), encoding="utf-8")
        render(html_path, png_path, chrome)
        print(png_path)
    # Keep legacy links valid while serving the corrected architecture.
    legacy_html = OUT.parent / "architecture_onetech_tender_agent.html"
    legacy_png = OUT.parent / "architecture_onetech_tender_agent.png"
    legacy_html.write_text(architecture(), encoding="utf-8")
    shutil.copyfile(OUT / "architecture_v2.png", legacy_png)


if __name__ == "__main__":
    main()
