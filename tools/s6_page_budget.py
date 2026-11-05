#!/usr/bin/env python3
"""S6 page budget: build variants of the manuscript without tables / figures and count pages.
Measurement only; the manuscript is not modified."""
import json, os, re, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "manuscript/full_paper_LNBI.md")
OUT = os.path.join(REPO, "results_v2/S6/pages/budget")
md = open(SRC, encoding="utf-8").read()
lines = md.split("\n")
def drop_tables(ls):
    o=[]
    for l in ls:
        if l.startswith("|") or l.startswith(": **Table"):
            continue
        o.append(l)
    return o
def drop_figs(ls):
    return [l for l in ls if not l.startswith("![")]
variants = {"no_tables": drop_tables(lines), "no_figures": drop_figs(lines),
            "no_tables_no_figures": drop_figs(drop_tables(lines))}
os.makedirs(OUT, exist_ok=True)
res = {}
for k, ls in variants.items():
    p = os.path.join(os.path.dirname(SRC), "_s6_variant_%s.md" % k)
    open(p, "w", encoding="utf-8").write("\n".join(ls))
    try:
        r = subprocess.run([sys.executable, "-B", os.path.join(REPO, "tools/lncs_pages.py"), "--src", p,
                            "--out", os.path.join(OUT, k), "--tag", k], capture_output=True, text=True)
        res[k] = json.loads(r.stdout.strip().split("\n")[-1])
    finally:
        os.remove(p)
json.dump(res, open(os.path.join(OUT, "budget.json"), "w"), indent=1)
for k, r in res.items():
    print(k, r["pages_total"], r["refs_start_page"], r["latex_errors"], r["body_words_intro_to_end"])
