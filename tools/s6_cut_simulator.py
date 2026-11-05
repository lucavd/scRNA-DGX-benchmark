#!/usr/bin/env python3
"""S6 cut-option simulator (measurement only; the manuscript is not modified).

For an option: keep the listed tables and figures, bring each top-level section's
prose to a word budget by truncating every paragraph proportionally (all citation
keys of a paragraph are kept, so the reference list is not shortened), compile with
tools/lncs_pages.py and report pages. The truncated text is a length proxy, not a draft.
"""
import json, os, re, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "manuscript/full_paper_LNBI.md")
OUT = os.path.join(REPO, "results_v2/S6/pages/options")
CITE = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")

def blocks(md):
    return md.split("\n\n")

def kind(b):
    s = b.strip()
    if not s: return "empty"
    if s.startswith("#"): return "heading"
    if s.startswith("!["): return "figure"
    if s.startswith(": **Table"): return "tcap"
    if all(l.startswith("|") for l in s.split("\n")): return "table"
    return "prose"

def tnum(b): return int(re.match(r": \*\*Table (\d+)", b.strip()).group(1))
def fnum(b): return int(re.search(r"\*\*Figure (\d+)", b).group(1))

def simulate(md, keep_tables, keep_figs, budgets):
    m = re.match(r"---\n.*?\n---\n", md, re.S)
    head_end = md.index("\n# Introduction")
    head, body = md[:head_end], md[head_end + 1:]
    bl = blocks(body)
    kinds = [kind(b) for b in bl]
    # pair each table caption with the adjacent table block
    drop = set()
    for i, k in enumerate(kinds):
        if k == "tcap" and tnum(bl[i]) not in keep_tables:
            drop.add(i)
            for j in (i - 1, i + 1):
                if 0 <= j < len(bl) and kinds[j] == "table": drop.add(j)
        if k == "figure" and fnum(bl[i]) not in keep_figs:
            drop.add(i)
    # section of each block
    sec, cur = [], None
    for b, k in zip(bl, kinds):
        if k == "heading" and re.match(r"# ", b.strip()): cur = b.strip()[2:].split("\n")[0].strip()
        sec.append(cur)
    words = {}
    for i, (b, k) in enumerate(zip(bl, kinds)):
        if k == "prose" and i not in drop:
            words[sec[i]] = words.get(sec[i], 0) + len(CITE.sub("", b).split())
    out = []
    for i, (b, k) in enumerate(zip(bl, kinds)):
        if i in drop: continue
        if k == "prose" and sec[i] in budgets and words.get(sec[i]):
            bud = budgets[sec[i]]
            f = bud if bud <= 1 else min(1.0, bud / words[sec[i]])  # <= 1 means a fraction
            cites = CITE.findall(b)
            plain = re.sub(r"[*`$]", "", CITE.sub("", b)).split()
            n = max(6, round(len(plain) * f))
            b = " ".join(plain[:n]) + (" " + " ".join(cites) if cites else "")
        out.append(b)
    return head + "\n" + "\n\n".join(out), words

def run(name, keep_tables, keep_figs, budgets):
    md = open(SRC, encoding="utf-8").read()
    txt, words = simulate(md, keep_tables, keep_figs, budgets)
    p = os.path.join(os.path.dirname(SRC), "_s6_option_%s.md" % name)
    open(p, "w", encoding="utf-8").write(txt)
    try:
        r = subprocess.run([sys.executable, "-B", os.path.join(REPO, "tools/lncs_pages.py"), "--src", p,
                            "--out", os.path.join(OUT, name), "--tag", name], capture_output=True, text=True)
        rec = json.loads(r.stdout.strip().split("\n")[-1])
    finally:
        os.remove(p)
    rec.update(keep_tables=keep_tables, keep_figs=keep_figs, budgets=budgets, prose_words_before=words)
    return rec

if __name__ == "__main__":
    opts = json.load(open(sys.argv[1]))
    res = {k: run(k, **v) for k, v in opts.items()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "options.json"), "w"), indent=1, ensure_ascii=False)
    for k, r in res.items():
        print(k, "pages", r["pages_total"], "refs_from", r["refs_start_page"], "err", r["latex_errors"],
              "words", r["body_words_intro_to_end"])
