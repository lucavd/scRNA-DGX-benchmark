"""One-page printable roadmap of the LNBI chapter (A4 landscape PDF).
Edit STATUS / dates below and rerun: python3 tools/roadmap.py  -> reports/roadmap.pdf"""
import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
mpl.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})

UPDATED = "3 novembre 2026, commit fecf686"
DAYS = ["mar\n3", "mer\n4", "gio\n5", "ven\n6", "sab\n7", "dom\n8", "lun\n9", "mar\n10"]
DONE, OPEN, WAIT = "done", "open", "wait"   # wait = aspetta il PI
# (code, label, closes-when, first day idx, last day idx, status, indent)
ROWS = [
    ("S0", "Basi del lavoro", "skill, docs, decisioni, md5", 0, 0, DONE, 0),
    ("S1", "Nuovo riferimento spatial", "controlli del brief superati", 0, 2, OPEN, 0),
    ("",   "preparare DGX: immagine e dati", "", 0, 1, OPEN, 1),
    ("",   "CPU sul DGX, nodo intero", "", 1, 2, OPEN, 1),
    ("",   "finestra server libero (PI)", "", 1, 2, WAIT, 1),
    ("",   "prova termica, CPU, GPU", "", 1, 2, OPEN, 1),
    ("",   "confronto driver, report", "", 2, 2, OPEN, 1),
    ("S2", "Piano delle correzioni", "piano approvato dal PI", 1, 1, OPEN, 0),
    ("S3", "Correzioni di sostanza, titolo e abstract", "testo approvato dal PI", 2, 2, OPEN, 0),
    ("S4", "Figure 1-6 per LNCS, con script", "figure rigenerate da script", 3, 3, OPEN, 0),
    ("S5", "Risultati spatial nuovi, figure 7-9", "numeri riletti dai nuovi JSON", 4, 4, OPEN, 0),
    ("S6", "Taglio a 15 pagine e stile", "13-17 pagine LNCS", 5, 5, OPEN, 0),
    ("S7", "LaTeX llncs, verifica finale, pacchetto", "checklist METEOR completa", 6, 6, OPEN, 0),
    ("",   "Sottomissione su METEOR (PI)", "scadenza 10 novembre", 7, 7, WAIT, 0),
]
PROBLEMS = [  # (text, step)
    ("Dataset: Census, non 10x E18; stress test su copie", "S3"),
    ("Multi-GPU: una sola GPU lavora; via 2 figure e Amdahl", "S3, S4"),
    ("Spatial: CPU rallentata, gruppi diversi, concordanza", "S1, S5"),
    ("120x dovuto al Wilcoxon di Scanpy (senza: 9,2x)", "S3"),
    ("Ripetizione 1: una convenzione unica", "S2"),
    ("Espressione differenziale solo come tempi", "S3"),
    ("Concordanza solo a 10k; via 'interchangeable'", "S3"),
    ("Bibliografia: autori inesistenti, Census, confronti", "S3, S7"),
    ("Discussione: frasi oltre il disegno", "S3"),
    ("Ambiente: nodo non dedicato, driver, downgrade RAPIDS", "S3"),
    ("Figure: caratteri < 6 pt, dpi, nomi, script", "S4, S5"),
    ("Quattro frasi sbagliate del 2 settembre", "S3"),
]
METEOR = [
    "Titolo e abstract diversi dallo short paper",
    "Stessi autori: Vedovelli, Lanera, Sabbatini, Gregori",
    "Almeno 8 pagine, formato LNCS (llncs 2.26)",
    "Credits: Acknowledgements e Disclosure of Interests",
    "Bibliografia splncs04 con DOI; CUP B53C22006440001",
    "Iniziale: PDF",
    "Finale: LaTeX, PDF, figure con i numeri giusti",
    "Finale: Excel dei testi alternativi (controllati)",
    "Finale: contenuti di terzi, licenza firmata",
]
DECISIONS = [
    "D-01 Spatial rifatto: processo per ripetizione, stessi gruppi",
    "D-02 Multi-GPU: un paragrafo, nessun nuovo run",
    "D-03 Circa 15 pagine LNCS",
    "D-04 Espressione differenziale come confronto di tempi",
    "D-05 CUP corretto B53C22006440001",
    "D-06 Lo short paper è chiuso",
    "D-07 Si lavora solo sul server",
    "D-08 Integrità dei grezzi con manifest md5",
    "D-09 Finestra spatial a server libero, la decide il PI",
    "D-10 Driver GPU: si misura l'effetto",
    "D-11 CPU spatial: DGX riferimento, server controllo",
]

INK, MID, LIGHT = "#1a1a1a", "#7a7a7a", "#d9d9d9"
BLUE, ORANGE = "#0072B2", "#E69F00"   # Okabe-Ito
FILL = {DONE: INK, OPEN: "white", WAIT: "white"}
EDGE = {DONE: INK, OPEN: BLUE, WAIT: ORANGE}


def box(fig, x, y, w, h, title):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.006",
                                      transform=fig.transFigure, fc="white", ec=MID, lw=0.6))
    fig.text(x + 0.008, y + h - 0.012, title, fontsize=9, weight="bold", va="top", color=INK)


def main(out="reports/roadmap.pdf"):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.03, 0.965, "Capitolo LNBI CIBB 2026: dove siamo e cosa manca", fontsize=15, weight="bold", va="top")
    fig.text(0.03, 0.932, "Benchmark GPU contro CPU per scRNA-seq e spatial  ·  sottomissione su Springer METEOR entro martedì 10 novembre 2026"
             f"  ·  aggiornato al {UPDATED}", fontsize=8.5, color=MID, va="top")

    # ---- Gantt -------------------------------------------------------------
    gx0, gx1, gy1 = 0.03, 0.635, 0.862
    lab_w, crit_w = 0.225, 0.125
    cx0 = gx0 + lab_w
    cx1 = gx1 - crit_w
    cw = (cx1 - cx0) / len(DAYS)
    rh = 0.0455
    for i, d in enumerate(DAYS):
        x = cx0 + i * cw
        weekend = d.startswith(("sab", "dom"))
        fig.patches.append(Rectangle((x, gy1 - rh * len(ROWS) - 0.004), cw, rh * len(ROWS) + 0.004,
                                     transform=fig.transFigure, fc="#f2f2f2" if weekend else "white", ec=LIGHT, lw=0.5, zorder=0))
        fig.text(x + cw / 2, gy1 + 0.005, d, ha="center", va="bottom", fontsize=8, linespacing=1.1, weight="bold" if i in (0, 7) else "normal",
                 color=ORANGE if i == 7 else INK)
    fig.text(cx1 + 0.006, gy1 + 0.005, "chiude quando", fontsize=8, color=MID, va="bottom")
    for r, (code, label, crit, a, b, st, ind) in enumerate(ROWS):
        y = gy1 - (r + 1) * rh
        mark = "\u2611" if st == DONE else "\u2610"
        if ind == 0:
            fig.patches.append(Rectangle((gx0, y), gx1 - gx0, 0.0006, transform=fig.transFigure, fc=LIGHT, ec="none"))
        lx = gx0 + 0.003 + 0.018 * ind
        txt = (f"{mark} {code}  {label}" if code else f"{mark} {label}")
        fig.text(lx, y + rh / 2, txt, fontsize=8.6 if ind == 0 else 7.6, va="center",
                 weight="bold" if (ind == 0 and code) else "normal", color=INK if st != DONE else MID)
        fig.text(cx1 + 0.006, y + rh / 2, crit, fontsize=7, va="center", color=MID)
        bh = rh * (0.55 if ind == 0 else 0.42)
        fig.patches.append(FancyBboxPatch((cx0 + a * cw + 0.004, y + (rh - bh) / 2), (b - a + 1) * cw - 0.008, bh,
                                          boxstyle="round,pad=0,rounding_size=0.004", transform=fig.transFigure,
                                          fc=FILL[st], ec=EDGE[st], lw=1.4 if st != DONE else 0.8,
                                          hatch="////" if st == WAIT else None))
        if st == DONE:
            fig.text(cx0 + (a + b + 1) / 2 * cw, y + rh / 2, "fatto", fontsize=7, color="white", ha="center", va="center", weight="bold")
    yb = gy1 - len(ROWS) * rh - 0.035
    # legend
    lx = gx0
    for st, name in [(DONE, "fatto"), (OPEN, "da fare (giorno previsto)"), (WAIT, "aspetta il PI")]:
        fig.patches.append(FancyBboxPatch((lx, yb), 0.022, 0.014, boxstyle="round,pad=0,rounding_size=0.003",
                                          transform=fig.transFigure, fc=FILL[st], ec=EDGE[st], lw=1.2,
                                          hatch="////" if st == WAIT else None))
        fig.text(lx + 0.027, yb + 0.007, name, fontsize=7.5, va="center")
        lx += 0.17
    fig.text(gx0, yb - 0.03, "Uno step al giorno, senza margine: se uno step slitta, chiedere la proroga agli organizzatori.\n"
             "S1 gira in parallelo a S2-S4; S5 aspetta i risultati spatial nuovi. Ogni step si chiude con il riassunto «In breve» e l'ok del PI.",
             fontsize=7.5, color=INK, va="top", linespacing=1.4)
    fig.text(gx0, yb - 0.085, "Nuova chat per ogni step: «sessione LNBI, step Sn».  Repo sul server: /mnt/wwn-0x5000039d58caca35/2026.scRNA_DGX",
             fontsize=7, color=MID, va="top")

    # ---- right column --------------------------------------------------------
    rx, rw = 0.655, 0.32
    h1 = 0.335
    y1 = 0.885 - h1 + 0.02
    box(fig, rx, y1, rw, h1, "I 12 problemi della revisione  →  step")
    for i, (t, s) in enumerate(PROBLEMS):
        yy = y1 + h1 - 0.038 - i * 0.0245
        fig.text(rx + 0.008, yy, f"\u2610 {i+1:>2}. {t}", fontsize=6.9, va="center")
        fig.text(rx + rw - 0.008, yy, s, fontsize=6.9, va="center", ha="right", color=BLUE, weight="bold")
    h2 = 0.245
    y2 = y1 - 0.012 - h2
    box(fig, rx, y2, rw, h2, "METEOR: cosa serve")
    for i, t in enumerate(METEOR):
        fig.text(rx + 0.008, y2 + h2 - 0.038 - i * 0.0225, f"\u2610 {t}", fontsize=7.2, va="center")
    h3 = y2 - 0.012 - 0.03
    y3 = 0.03
    box(fig, rx, y3, rw, h3, "Decisioni già prese (3 novembre)")
    for i, t in enumerate(DECISIONS):
        fig.text(rx + 0.008, y3 + h3 - 0.045 - i * 0.0185, t, fontsize=7, va="center", color=INK)
    fig.text(0.03, 0.03, "Rigenerare: python3 tools/roadmap.py  (stati e date in testa allo script)", fontsize=6.6, color=MID)
    fig.savefig(out)
    fig.savefig(out.replace(".pdf", ".png"), dpi=150)
    return fig


if __name__ == "__main__":
    main()
