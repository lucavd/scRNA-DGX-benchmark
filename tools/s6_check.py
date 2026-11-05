#!/usr/bin/env python3
"""S6 independent check (standard library only).

Reads the manuscript before the cut, the new chapter text and the supplement, and
checks the pre-registered gates G2, G3, G5 (text part) and predictions P2, P3.
Page counts (G4, P1, P4) are read from the receipts of tools/lncs_pages.py.
Usage: python3 -B tools/s6_check.py --pre PRE.md --main MAIN.md --sup SUP.md
       --pages-main pages.json --pages-sup pages.json --bib-md5 MD5 --out OUT.json
"""
import argparse, hashlib, json, re, statistics, os

CITE = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")
KEY = re.compile(r"@([A-Za-z0-9_:-]+)")
LABEL = re.compile(r"\b(?:Tables?|Fig\.|Figures?)\s+S?\d+|\bS\d+(?:-S\d+)?\b|\*\*(?:Table|Figure) S?\d+\.\*\*")
NUM = re.compile(r"(?<![A-Za-z0-9_.\-])\d[\d,]*(?:\.\d+)?")
OPENERS = ("Moreover", "Additionally", "Notably", "Importantly", "Furthermore", "Interestingly", "Overall")
LISTED = ("landscape", "dramatically", "impressive", "fundamental", "actually")

def body(t):
    i = t.index("\n# ")
    return t[i + 1:]

def numbers(t):
    t = LABEL.sub(" ", t)
    t = re.sub(r"\]\([^)]*\)", "]", t)          # figure paths
    t = re.sub(r"<https?://[^>]*>", " ", t)       # URLs
    t = re.sub(r"`[^`]*`", lambda m: " " if re.search(r"[A-Za-z]", m.group(0)) and not re.search(r"=", m.group(0)) else m.group(0), t)
    out = set()
    for n in NUM.findall(t):
        n = n.rstrip(",.")
        if n: out.add(n)
    return out

def table_rows(t):
    return [l for l in t.split("\n") if l.startswith("|")]

def keys(t):
    return sorted({k for g in CITE.findall(t) for k in KEY.findall(g)})

def prose_blocks(t):
    t = t[t.index("# Introduction"):t.index("# Conflict of Interest")] if "# Introduction" in t else t
    for b in t.split("\n\n"):
        s = b.strip()
        if not s or s.startswith(("#", "|", ": **", "![")):
            continue
        yield CITE.sub("", s)

def sentences(blocks):
    out = []
    for b in blocks:
        b = " ".join(b.split())
        for s in re.split(r"(?<=[.?!])\s+(?=[A-Z(`\[])", b):
            if s.strip():
                out.append(s.strip())
    return out

def main():
    ap = argparse.ArgumentParser()
    for a in ("pre", "main", "sup", "pages_main", "pages_sup", "bib", "bib_md5", "out"):
        ap.add_argument("--" + a.replace("_", "-"), required=True)
    a = ap.parse_args()
    pre, mn, sp = (open(p, encoding="utf-8").read() for p in (a.pre, a.main, a.sup))
    res = {"inputs": {k: hashlib.md5(open(p, "rb").read()).hexdigest() for k, p in
                      (("pre", a.pre), ("main", a.main), ("sup", a.sup), ("bib", a.bib))}}
    # G2 numbers and tables
    pre_n = numbers(body(pre))
    new_main_n, new_sup_n = numbers(body(mn)), numbers(body(sp))
    res["G2_numbers_not_in_pre_main"] = sorted(new_main_n - pre_n)
    res["G2_numbers_not_in_pre_sup"] = sorted(new_sup_n - pre_n)
    res["info_pre_numbers_absent_from_both"] = sorted(pre_n - new_main_n - new_sup_n)
    rows_new = set(table_rows(mn)) | set(table_rows(sp))
    res["G2_table_rows_pre"] = len(table_rows(pre))
    # a row may differ only by the renumbered cross-reference (old label -> Sn / "n of the chapter")
    inv_t = {"S1": "1", "S2": "2", "S3": "3", "S4": "5", "S5": "6", "S6": "7", "S7": "9", "S8": "10"}
    def unlabel(r):
        r = re.sub(r"\bTable (\d+) of the chapter", lambda m: "Table " + {"1": "4", "2": "8"}[m.group(1)], r)
        return re.sub(r"\bTable (S\d+)\b", lambda m: "Table " + inv_t[m.group(1)], r)
    relabelled = {unlabel(r): r for r in rows_new if unlabel(r) != r}
    res["G2_table_rows_relabelled_only"] = [[r, relabelled[r]] for r in table_rows(pre) if r not in rows_new and r in relabelled]
    res["G2_table_rows_missing"] = [r for r in table_rows(pre) if r not in rows_new and r not in relabelled]
    res["G2_pass"] = not res["G2_numbers_not_in_pre_main"] and not res["G2_numbers_not_in_pre_sup"] and not res["G2_table_rows_missing"]
    # G3 citations
    kp, km, ks = keys(pre), keys(mn), keys(sp)
    res["G3_keys_pre"] = len(kp); res["G3_keys_main"] = len(km); res["G3_keys_sup"] = len(ks)
    res["G3_keys_lost"] = sorted(set(kp) - set(km) - set(ks))
    res["G3_keys_only_in_sup"] = sorted(set(ks) - set(km))
    res["G3_bib_unchanged"] = res["inputs"]["bib"] == a.bib_md5
    pm, ps = json.load(open(a.pages_main)), json.load(open(a.pages_sup))
    res["G3_undefined_main"], res["G3_undefined_sup"] = pm["undefined_citations"], ps["undefined_citations"]
    res["G3_pass"] = not res["G3_keys_lost"] and res["G3_bib_unchanged"] and not pm["undefined_citations"] and not ps["undefined_citations"]
    # G4 pages (receipts)
    res["G4_pages_main"], res["G4_latex_errors_main"], res["G4_abstract_words"] = pm["pages_total"], pm["latex_errors"], pm["abstract_words"]
    res["G4_src_md5_matches"] = pm["src_md5"] == res["inputs"]["main"] and ps["src_md5"] == res["inputs"]["sup"]
    res["G4_pass"] = 13 <= pm["pages_total"] <= 17 and pm["latex_errors"] == 0 and 150 <= pm["abstract_words"] <= 250 and res["G4_src_md5_matches"]
    # G5 text
    dash = {n: [i + 1 for i, l in enumerate(t.split("\n")) if "\u2013" in l or "\u2014" in l] for n, t in (("main", mn), ("sup", sp))}
    res["G5_dash_lines"] = dash
    sents = sentences(prose_blocks(mn))
    res["G5_openers_main"] = [s[:80] for s in sents if s.split()[0].rstrip(",") in OPENERS]
    low = mn.lower()
    res["G5_listed_words_main"] = {w: low.count(w) for w in LISTED if w in low}
    res["G5_text_pass"] = not dash["main"] and not dash["sup"] and not res["G5_openers_main"] and not res["G5_listed_words_main"]
    # P2, P3, P4
    res["P2_keys_main"] = len(km)
    lens = [len(s.split()) for s in sents]
    q = statistics.quantiles(lens, n=10)
    res["P3_sentences"] = len(lens); res["P3_median_words"] = statistics.median(lens); res["P3_p90_words"] = q[8]; res["P3_max_words"] = max(lens)
    res["P4_pages_sup"] = ps["pages_total"]
    res["P1_pages_main"] = pm["pages_total"]
    res["prose_words_main"] = sum(len(b.split()) for b in prose_blocks(mn))
    json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k.endswith("pass") or k.startswith(("P", "G4_pages"))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
