#!/usr/bin/env python3
"""Delivery checks for region R2 (stdlib). Usage: cd $REPO && python3 -B check_R2.py <dir with R2 files> [valori.json]"""
import csv, json, re, sys, os
D = sys.argv[1]
MS = open("manuscript/full_paper_LNBI.md", encoding="utf-8").read()
BIB = open("manuscript/bibliography/cibb2026_references.bib", encoding="utf-8").read()
keys = set(re.findall(r"^@\w+\{([^,]+),", BIB, re.M))
E = list(csv.DictReader(open(os.path.join(D, "edits_R2.csv"), encoding="utf-8")))
RC = list(csv.DictReader(open(os.path.join(D, "ricevute_R2.csv"), encoding="utf-8")))
DI = list(csv.DictReader(open(os.path.join(D, "diario_R2.csv"), encoding="utf-8")))
prim = "R0024 R0025 R0029 R0044 R0050 R0252 R0259 R0276 R0279 R0342 R0386 R0387 R0390 R0391 R0398 R0400 R0407 R0420 R0422 R0423 R0425 R0426 R0428 R0445 R0448 R0451 R0453 R0454 R0455 R0459 R0461 R0462 R0463 R0465 R0466 R0479 R0480 R0487 R0489 R0490 R0492 R0493 R0496 R0518 R0536 R0539 R0549 R0553 R0554 R0653 R0657 R0687 R0704 R0705 R0706".split()
PENDING_KEYS = {"CZCellxGene2025"}
out = {"n_edits": len(E), "n_receipts": len(RC), "n_diario": len(DI), "errors": [], "pending_bib_keys": []}
spans = []
for e in E:
    v = e["vecchio"]; c = MS.count(v)
    if c != 1: out["errors"].append(f"{e['edit_id']}: vecchio occurs {c} times")
    i = MS.find(v); spans.append((i, i + len(v), e["edit_id"]))
    line = MS[:i].count("\n") + 1
    if str(line) != e["riga"]: out["errors"].append(f"{e['edit_id']}: line {line} != {e['riga']}")
    if not 47 <= line <= 175: out["errors"].append(f"{e['edit_id']}: outside region")
    if "\u2013" in e["nuovo"] or "\u2014" in e["nuovo"]: out["errors"].append(f"{e['edit_id']}: dash")
    for br in re.findall(r"\[[^\]]*@[^\]]*\]", e["nuovo"]):
        for k in re.findall(r"@([A-Za-z0-9_]+)", br):
            if k not in keys:
                (out["pending_bib_keys"] if k in PENDING_KEYS else out["errors"]).append(f"{e['edit_id']}: key {k} not in .bib")
spans.sort()
for a, b in zip(spans, spans[1:]):
    if a[1] > b[0]: out["errors"].append(f"overlap {a[2]} {b[2]}")
nuovo = {e["edit_id"]: e["nuovo"] for e in E}
for r in RC:
    if r["valore_scritto"] not in nuovo.get(r["edit_id"], ""): out["errors"].append(f"{r['ricevuta_id']}: valore_scritto not in nuovo")
ids = {d["id"] for d in DI}
for p in prim:
    if p not in ids: out["errors"].append(f"diario missing {p}")
for d in DI:
    if d["esito"] not in ("fatto", "rimandato", "non applicabile", "deciso-diversamente", "in-attesa-PI"): out["errors"].append(f"bad esito {d['id']}")
if len(sys.argv) > 2:
    V = json.load(open(sys.argv[2]))
    for r in RC:
        v = V.get(r["ricevuta_id"])
        if str(v) != r["valore_letto"]: out["errors"].append(f"{r['ricevuta_id']}: valori {v!r} != ricevuta {r['valore_letto']!r}")
        if not r["arrotondamento"].startswith("nessun-controllo"):
            s = r["valore_scritto"].replace(",", ""); dec = len(s.split(".")[1]) if "." in s else 0
            if round(float(v), dec) != float(s): out["errors"].append(f"{r['ricevuta_id']}: rounding")
print(json.dumps(out, indent=1))
