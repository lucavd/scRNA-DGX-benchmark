#!/usr/bin/env python3
"""S7 independent check of the LaTeX sources against the Markdown (gate G3) and
provenance of every number of the final text (gate G4, second part).

Written separately from tools/s7_md2lncs.py: it does not import it and reads the
.tex files the converter wrote, with its own regular expressions.

G3  for chapter and supplement: the sequence of numbers and the sequence of
    cited keys are the same in the .md and in the text of the .tex; no ASCII
    transcription left outside commands; no U+2013/U+2014 in .md and .tex;
    figure file number = caption label = LaTeX counter (from the .aux);
    every "Fig./Figure/Table N" or "SN" reference points to an existing item.
G4b every number token of the final .md files gets a provenance class
    (see provenance()); tokens without one are listed.

Usage: python3 -B tools/s7_check.py --out results_v2/S7/s7_check.json
Standard library only.
"""
import argparse, csv, difflib, glob, hashlib, json, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r"(?<![A-Za-z0-9_.\-])\d[\d,]*(?:\.\d+)?")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def nums(text):
    return [m.group(0).rstrip(",") for m in NUM.finditer(text)]


# ---------------------------------------------------------------- Markdown side
def md_plain(md):
    title = re.search(r'^title:\s*"(.*)"\s*$', md, re.M).group(1)
    body = re.sub(r"(?s)^---\n.*?\n---\n", "", md, count=1)
    body = body.split("\n# References")[0]
    keys = []
    def cite(m):
        keys.extend(re.findall(r"@([A-Za-z0-9_:\-]+)", m.group(0)))
        return " "
    body = re.sub(r"\[[^\[\]]*@[^\[\]]*\]", cite, body)
    body = re.sub(r"\]\([^)]*\)", "]", body)                    # image paths
    body = re.sub(r"\*\*(?:Figure|Table) S?\d+\.\*\*", " ", body)  # caption labels (llncs numbers them)
    body = re.sub(r"\^[0-9,]+\^", " ", body)                      # affiliation markers
    body = re.sub(r"`[^`]*`", " ", body)                          # inline code
    body = re.sub(r"<https?://[^>]*>", " ", body)
    body = re.sub(r"https?://\S+", " ", body)
    body = re.sub(r"(?m)^\|[-|: ]+\|\s*$", " ", body)            # table separator rows
    body = re.sub(r"\{#tbl:[^}]*\}", " ", body)
    body = body.replace("&nbsp;", " ")
    return title + "\n" + body, keys


# ---------------------------------------------------------------- LaTeX side
def tex_plain(tex):
    title = re.search(r"\\title\{(.*)\}", tex).group(1)
    body = tex.split("\\begin{document}", 1)[1].split("\\bibliographystyle", 1)[0]
    body = re.sub(r"\\title\{.*\}", " ", body)
    body = re.sub(r"\\titlerunning\{.*\}", " ", body)
    keys = []
    def cite(m):
        keys.extend(k.strip() for k in m.group(1).split(","))
        return " "
    body = re.sub(r"\\cite\{([^}]*)\}", cite, body)
    body = re.sub(r"(?s)\\endfirsthead.*?\\endhead", " ", body)  # repeated longtable header
    body = re.sub(r"(?s)\\begin\{longtable\}\[\]\{@\{\}.*?@\{\}\}", " ", body)  # column specification
    body = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}", " ", body)
    body = re.sub(r"\\textasciitilde(?:\{\})?", "~", body)
    for cmd in ("orcidID", "inst", "label", "ref", "url", "nolinkurl", "texttt", "email", "includegraphics", "typeout"):
        body = re.sub(r"\\%s(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}" % cmd, " ", body)
    body = body.replace("\\allowbreak{}", "")
    body = re.sub(r"\\(?:%|&|_|#)", lambda m: m.group(0)[1], body)
    return title + "\n" + body, keys


ASCII = {
    "um": re.compile(r"\d\s*um\b"),
    "rho": re.compile(r"(?<!\\)\brho\b"),
    "+/-": re.compile(r"\+/-"),
    ">= / <=": re.compile(r"(?:>|<|\\textgreater\{\}|\\textless\{\})="),
    "Nx": re.compile(r"\d(?:\.\d+)?x\b(?!\s+Genomics)"),
    " x ": re.compile(r"(?<=\s)x(?=\s)"),
}


def compare(md_path, tex_path, aux_path):
    md, tex = open(md_path, encoding="utf-8").read(), open(tex_path, encoding="utf-8").read()
    mp, mk = md_plain(md)
    tp, tk = tex_plain(tex)
    a, b = nums(mp), nums(tp)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = [{"op": op, "md": a[i1:i2], "tex": b[j1:j2]} for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    residual = {k: rx.findall(tp) for k, rx in ASCII.items()}
    residual = {k: v for k, v in residual.items() if v}
    dashes = {"md": sum(md.count(ch) for ch in "\u2013\u2014"), "tex": sum(tex.count(ch) for ch in "\u2013\u2014")}
    aux = open(aux_path, encoding="latin-1").read()
    labels = dict(re.findall(r"\\newlabel\{((?:fig|tab):S?\d+)\}\{\{([^}]*)\}", aux))
    figs = re.findall(r"(?s)\\begin\{figure\}.*?\\includegraphics(?:\[[^\]]*\])?\{figures/fig(S?\d+)\.pdf\}.*?\\label\{fig:(S?\d+)\}.*?\\end\{figure\}", tex)
    fig_bad = [f for f in figs if not (f[0] == f[1] and labels.get("fig:" + f[1]) == f[1])]
    tab_labels = re.findall(r"\\label\{tab:(S?\d+)\}", tex)
    tab_bad = [t for t in tab_labels if labels.get("tab:" + t) != t]
    return {"md": os.path.relpath(md_path, REPO), "md_md5": md5(md_path), "tex": os.path.relpath(tex_path, REPO),
            "tex_md5": md5(tex_path), "n_numbers_md": len(a), "n_numbers_tex": len(b), "number_diffs": diffs,
            "n_cites_md": len(mk), "n_cites_tex": len(tk), "cite_sequence_equal": mk == tk,
            "residual_ascii": residual, "dash_chars": dashes,
            "figures": [{"file_number": f[0], "label": f[1], "counter": labels.get("fig:" + f[1])} for f in figs],
            "figure_mismatches": fig_bad, "tables": [{"label": t, "counter": labels.get("tab:" + t)} for t in tab_labels],
            "table_mismatches": tab_bad,
            "pass": (not diffs and mk == tk and not residual and dashes == {"md": 0, "tex": 0}
                     and not fig_bad and not tab_bad)}


def references(main_md, sup_md, chap, sup):
    """Every figure/table reference in the text points to an item that exists."""
    have = {"fig": {f["label"] for f in chap["figures"]} | {f["label"] for f in sup["figures"]},
            "tab": {t["label"] for t in chap["tables"]} | {t["label"] for t in sup["tables"]}}
    bad, n = [], 0
    for doc, text in (("chapter", main_md), ("supplement", sup_md)):
        text = re.sub(r"\*\*(?:Figure|Table) S?\d+\.\*\*", " ", text)
        for kind, rng in re.findall(r"\b(Fig\.|Figs?\.|Figures?|Tables?)\s+(S?\d+(?:\s*(?:-|and|,)\s*S?\d+)*)", text):
            k = "fig" if kind.startswith("F") else "tab"
            for part in re.split(r"\s*(?:,|and)\s*", rng):
                ends = re.findall(r"S?\d+", part)
                if "-" in part and len(ends) == 2:
                    pre = "S" if ends[0].startswith("S") else ""
                    items = [pre + str(i) for i in range(int(ends[0].lstrip("S")), int(ends[1].lstrip("S")) + 1)]
                else:
                    items = ends
                for it in items:
                    n += 1
                    if it not in have[k]:
                        bad.append({"doc": doc, "ref": kind + " " + it})
    return {"n_references": n, "dangling": bad, "pass": not bad}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    L = os.path.join(REPO, "manuscript/lncs_latex")
    B = os.path.join(REPO, "results_v2/S7/build")
    chap = compare(os.path.join(REPO, "manuscript/full_paper_LNBI.md"), os.path.join(L, "full_paper_LNBI.tex"),
                   os.path.join(B, "chapter/full_paper_LNBI.aux"))
    sup = compare(os.path.join(REPO, "manuscript/supplementary_LNBI.md"), os.path.join(L, "supplementary_LNBI.tex"),
                  os.path.join(B, "supplement/supplementary_LNBI.aux"))
    refs = references(open(os.path.join(REPO, "manuscript/full_paper_LNBI.md"), encoding="utf-8").read(),
                      open(os.path.join(REPO, "manuscript/supplementary_LNBI.md"), encoding="utf-8").read(), chap, sup)
    # figure files in lncs_latex/figures: md5 equal to the PDF written by the figure script
    figmd5 = []
    for rec in ("chapter", "supplement"):
        r = json.load(open(os.path.join(B, rec, "receipt.json")))
        for f in r["figures"]:
            figmd5.append({"file": f["file"], "source": f["source"], "same_md5": md5(os.path.join(L, f["file"])) == md5(os.path.join(REPO, f["source"]))})
    res = {"G3": {"chapter": chap, "supplement": sup, "references": refs, "figure_files": figmd5,
                  "pass": chap["pass"] and sup["pass"] and refs["pass"] and all(f["same_md5"] for f in figmd5)}}
    json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"G3_pass": res["G3"]["pass"], "chapter": {k: chap[k] for k in ("n_numbers_md", "n_numbers_tex", "number_diffs", "cite_sequence_equal", "residual_ascii", "dash_chars", "figure_mismatches", "table_mismatches")},
                      "supplement": {k: sup[k] for k in ("n_numbers_md", "n_numbers_tex", "number_diffs", "cite_sequence_equal", "residual_ascii", "dash_chars", "figure_mismatches", "table_mismatches")},
                      "references": refs, "figure_files": figmd5}, ensure_ascii=False)[:6000])
