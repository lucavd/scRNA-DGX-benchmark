#!/usr/bin/env python3
"""Definitive LNCS LaTeX source from the Markdown manuscript (step S7).

Converts manuscript/full_paper_LNBI.md (chapter) or manuscript/supplementary_LNBI.md
(--supplement) into a llncs 2.26 document, with:
  - ASCII transcriptions of the .md turned into LaTeX symbols (ledger R0729):
    "8 um" -> 8~\\textmu{}m, rho -> $\\rho$, |rho| -> $|\\rho|$, +/- -> ~$\\pm$~ (no line break around it),
    >= / <= -> $\\geq$ / $\\leq$, "12.0x" / "1xH100" / "8 x NVIDIA" -> $\\times$;
    text inside \\texttt, \\url, \\href, \\cite, \\label and \\includegraphics is left alone;
  - Acknowledgements, Funding and Disclosure of Interests in the credits
    environment (ledger R0734); Funding is a second paragraph of the
    acknowledgements, as in Springer's instructions;
  - "**Figure N.**" / "**Table N.**" removed from the start of captions (llncs
    prints "Fig. N." / "Table N." itself) and replaced by \\label{fig:N} / \\label{tab:N};
  - ORCID identifiers from the YAML field `orcid:` of the .md, as \\orcidID after the author;
  - figure files copied to <out>/figures/ under the number of their caption
    (fig1.pdf ... or figS1.pdf ...), md5 recorded (ledger R0735, decision D-23);
  - tables set in \\footnotesize with 2 pt column separation, \\emergencystretch 1em; long e-mail
    and \\texttt strings allowed to break.
It then compiles in <build> with pdflatex + bibtex (splncs04) and writes a JSON
receipt: pages, page where the references start, LaTeX errors, undefined
citations and references, overfull boxes (with width), figure map, md5 of every
input and output. The .tex, .bbl and figures are copied to <out>.

Usage: python3 -B tools/s7_md2lncs.py [--supplement] [--doi DOI]
Standard library only; pandoc 3.1 on PATH; TeX from ~/.TinyTeX. lmodern gives Type 1
fonts in T1 encoding (without it TinyTeX falls back to bitmap Type 3 fonts).
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from lncs_pages import split_md, pandoc, fix_cites, md5, words, TEX  # noqa: E402

RUNNING = {"chapter": "GPU-accelerated single-cell and spatial transcriptomics",
           "supplement": "Supplementary Material"}  # llncs suppresses running titles wider than the head line

PROTECT = re.compile(r"\\(?:texttt|nolinkurl|url|href|cite|label|ref|includegraphics|email)(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}")


def symbols(tex):
    """ASCII transcriptions -> LaTeX symbols, outside protected commands."""
    keep = []
    def stash(m):
        keep.append(m.group(0))
        return "\x00%d\x00" % (len(keep) - 1)
    t = PROTECT.sub(stash, tex)
    t = re.sub(r"\\textbar\{?\}?\s*rho\s*\\textbar\{?\}?", r"$|\\rho|$", t)
    t = re.sub(r"(\d)\s+um\b", r"\1~\\textmu{}m", t)
    t = re.sub(r"(?<!\\)\brho\b", r"$\\rho$", t)
    t = re.sub(r"\s*\+/-\s*", r"~$\\pm$~", t)
    t = re.sub(r"(?:>|\\textgreater\{\})=", r"$\\geq$", t)
    t = re.sub(r"(?:<|\\textless\{\})=", r"$\\leq$", t)
    t = re.sub(r"(\d)x(?=\b|H100)(?!\s+Genomics)", r"\1$\\times$", t)  # not "10x Genomics"
    t = re.sub(r"(?<=\s)x(?=\s)", r"$\\times$", t)
    return re.sub("\x00(\\d+)\x00", lambda m: keep[int(m.group(1))], t)


def breakable(tex):
    """Allow line breaks inside \\texttt at underscores and in the e-mail list."""
    def tt(m):
        s = m.group(1)
        if "/" in s and not re.search(r"[\\{}]", s):
            return r"\nolinkurl{" + s + "}"  # paths and image names: url-style breaks at / . :
        return r"\texttt{" + s.replace(r"\_", r"\_\allowbreak{}") + "}"
    tex = re.sub(r"\\texttt\{((?:[^{}]|\{[^{}]*\})*)\}", tt, tex)
    # long hexadecimal digests (sha256): a break point every 16 characters
    tex = re.sub(r"\b[0-9a-f]{32,}\b",
                 lambda m: r"\allowbreak{}".join(m.group(0)[i:i + 16] for i in range(0, len(m.group(0)), 16)), tex)
    return re.sub(r"\\email\{(.*)\}\s*$",
                  lambda m: r"\email{" + m.group(1).replace(",", r",\allowbreak{}") + "}", tex, flags=re.M)


def captions(tex):
    """Drop the leading bold label of captions and add \\label; return the caption order."""
    order = []
    def cap(m):
        kind, num = m.group(1), m.group(2)
        order.append([kind, num])
        return r"\caption{\label{%s}" % (("fig:" if kind == "Figure" else "tab:") + num)
    tex = re.sub(r"\\caption\{\\textbf\{(Figure|Table) (S?\d+)\.\}\s*", cap, tex)
    return tex, order


def tables(tex):
    """\\footnotesize for tables up to 7 columns, \\scriptsize for wider ones; 2 pt column separation."""
    def one(m):
        ncol = len(re.findall(r"\\real\{", m.group(1))) or len(re.sub(r"[^lrcp]", "", m.group(1).split("}")[0]))
        size = "\\scriptsize" if ncol >= 8 else "\\footnotesize"
        return "{" + size + "\\setlength{\\tabcolsep}{2pt}\n\\begin{longtable}" + m.group(1)
    tex = re.sub(r"\\begin\{longtable\}(\[\]\{@\{\}(?:[^@]|@(?!\{\}\}))*@\{\}\})", one, tex)
    return tex.replace("\\end{longtable}", "\\end{longtable}\n}")


def section(body, name):
    """Return (text of top-level section `name`, body without it)."""
    m = re.search(r"(?ms)^# %s\s*\n(.*?)(?=^# |\Z)" % re.escape(name), body)
    if not m:
        return None, body
    return m.group(1).strip(), body[:m.start()] + body[m.end():]


def build(src, out, build_dir, supplement, doi, tag):
    md = open(src, encoding="utf-8").read()
    title, authors, insts, abstract, keywords, body = split_md(md)
    body = re.sub(r"\s*\{#tbl:[^}]*\}", "", body)
    body_main, _, _ = body.partition("\n# References")
    credits = ""
    conv = lambda s: symbols(fix_cites(pandoc(s))).strip()
    if not supplement:
        ack, body_main = section(body_main, "Acknowledgements")
        fund, body_main = section(body_main, "Funding")
        disc, body_main = section(body_main, "Disclosure of Interests")
        if not (ack and fund and disc):
            sys.exit("chapter must have Acknowledgements, Funding and Disclosure of Interests sections")
        credits = ("\\begin{credits}\n\\subsubsection{\\ackname} " + conv(ack) + "\n\n" + conv(fund) +
                   "\n\n\\subsubsection{\\discintname} " + conv(disc) + "\n\\end{credits}\n")
    if doi:
        body_main = body_main.replace("@@REPO_DOI@@", doi)
    figmap, srcs = [], {}
    def fig(mm):
        cap, p = mm.group(1), mm.group(2)
        num = re.match(r"\*\*Figure (S?\d+)\.\*\*", cap).group(1)
        q = os.path.normpath(os.path.join(os.path.dirname(src), p))
        pdf = os.path.splitext(q)[0] + ".pdf"
        if not os.path.exists(pdf):
            sys.exit("missing vector figure " + pdf)
        name = "fig%s.pdf" % num
        srcs[name] = pdf
        figmap.append({"number": num, "file": "figures/" + name, "source": os.path.relpath(pdf, REPO),
                       "md5": md5(pdf)})
        return "![%s](figures/%s)" % (cap, name)
    body_main = re.sub(r"!\[(.*?)\]\(([^)]+\.png)\)", fig, body_main, flags=re.S)
    btex = fix_cites(pandoc(body_main))
    btex, caporder = captions(btex)
    btex = tables(symbols(breakable(btex)))
    orcid = dict(re.findall(r"(?m)^  ([^:\n]+):\s*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\s*$",
                            (re.search(r"(?ms)^orcid:\s*\n((?:  .*\n)+)", md.split("\n---\n", 1)[0] + "\n") or re.match("", "")).group(1) or ""))
    alist = [a.strip() for a in re.split(r",\s+(?:and\s+)?(?=[A-Z])|\s+and\s+(?=[A-Z])", authors) if a.strip()]
    atex = []
    for a in alist:
        nm = re.sub(r"\^([0-9,]+)\^", "", a).strip()
        sup = re.search(r"\^([0-9,]+)\^", a)
        atex.append(nm + (r"\inst{%s}" % sup.group(1) if sup else "") + (r"\orcidID{%s}" % orcid[nm] if nm in orcid else ""))
    itex = []
    for p in insts:
        t = re.sub(r"^\^[0-9]+\^\s*", "", p)
        t = pandoc(t).strip()
        t = re.sub(r"\\texttt\{(.*?)\}\s*$", lambda m: r"\\ \email{" + m.group(1) + "}", t)
        itex.append(breakable(t))
    abs_txt = abstract.replace("**Abstract.**", "").strip()
    kw = keywords.replace("**Keywords:**", "").strip().replace("·", r"\and")
    absblock = ("\\begin{abstract}\n" + conv(abs_txt) + "\n\\keywords{" + kw + "}\n\\end{abstract}\n") if abs_txt else ""
    supnum = ("\\renewcommand{\\thetable}{S\\arabic{table}}\n\\renewcommand{\\thefigure}{S\\arabic{figure}}\n"
              if supplement else "")
    bibsrc = os.path.join(os.path.dirname(src), re.search(r"bibliography:\s*(\S+)", md).group(1))
    stem = os.path.splitext(os.path.basename(src))[0]
    bibname = os.path.splitext(os.path.basename(bibsrc))[0]
    doc = ("\\documentclass[runningheads]{llncs}\n"
           "\\usepackage[T1]{fontenc}\n\\usepackage[utf8]{inputenc}\n\\usepackage{lmodern}\n"
           "\\usepackage{graphicx,booktabs,longtable,array,calc,amsmath,amssymb}\n"
           "\\usepackage[hidelinks]{hyperref}\n"
           "\\providecommand{\\tightlist}{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n"
           "\\def\\LTcaptype{table}\n\\makeatletter\\setlength{\\LTcapwidth}{\\textwidth}\n"
           "\\def\\LT@makecaption#1#2#3{\\LT@mcol\\LT@cols c{\\hbox to\\z@{\\hss\\parbox[t]\\LTcapwidth{\\small\\textbf{#2.} #3\\par\\vskip0.4\\baselineskip}\\hss}}}\n\\makeatother\n\\setlength{\\emergencystretch}{1em}\n" + supnum +
           "\\begin{document}\n"
           "\\title{%s}\n\\titlerunning{%s}\n\\author{%s}\n\\authorrunning{L. Vedovelli et al.}\n\\institute{%s}\n\\maketitle\n"
           "%s\n%s\n%s\n\\typeout{REFSTART \\thepage}\n"
           "\\bibliographystyle{splncs04}\n\\bibliography{%s}\n\\typeout{DOCEND \\thepage}\n\\end{document}\n"
           ) % (symbols(pandoc(title).strip()), RUNNING[tag], r" \and ".join(atex), " \\and\n".join(itex),
                absblock, btex, credits, bibname)
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(os.path.join(build_dir, "figures"))
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    open(os.path.join(build_dir, stem + ".tex"), "w", encoding="utf-8").write(doc)
    for f in ("llncs.cls", "splncs04.bst"):
        shutil.copy(os.path.join(REPO, "manuscript/lncs_latex", f), build_dir)
    for f in sorted(os.listdir(os.path.join(REPO, "tools/lncs_support"))):
        shutil.copy(os.path.join(REPO, "tools/lncs_support", f), build_dir)
    shutil.copy(bibsrc, os.path.join(build_dir, bibname + ".bib"))
    for name, pdf in srcs.items():
        shutil.copy(pdf, os.path.join(build_dir, "figures", name))
    env = dict(os.environ, PATH=TEX + ":" + os.environ["PATH"])
    log = []
    for cmd in (["pdflatex", "-interaction=nonstopmode", stem + ".tex"], ["bibtex", stem],
                ["pdflatex", "-interaction=nonstopmode", stem + ".tex"],
                ["pdflatex", "-interaction=nonstopmode", stem + ".tex"]):
        r = subprocess.run(cmd, cwd=build_dir, env=env, capture_output=True, text=True)
        log.append([" ".join(cmd), r.returncode])
    texlog = open(os.path.join(build_dir, stem + ".log"), encoding="latin-1").read()
    pdf = os.path.join(build_dir, stem + ".pdf")
    if not os.path.exists(pdf):
        sys.exit("no PDF produced; see " + os.path.join(build_dir, stem + ".log"))
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True,
                text=True).stdout).group(1))
    over = [(float(w), int(ln)) for w, ln in
            re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\) [^\n]*?lines? (\d+)", texlog)]
    blg = open(os.path.join(build_dir, stem + ".blg"), encoding="latin-1").read()
    aux = open(os.path.join(build_dir, stem + ".aux"), encoding="latin-1").read()
    labels = dict(re.findall(r"\\newlabel\{((?:fig|tab):S?\d+)\}\{\{([^}]*)\}", aux))
    rec = {
        "tag": tag, "at": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "src": os.path.relpath(src, REPO), "src_md5": md5(src), "bib_md5": md5(bibsrc),
        "llncs_md5": md5(os.path.join(build_dir, "llncs.cls")), "bst_md5": md5(os.path.join(build_dir, "splncs04.bst")),
        "pandoc": subprocess.run(["pandoc", "--version"], capture_output=True, text=True).stdout.split("\n")[0],
        "pdftex": subprocess.run(["pdflatex", "--version"], env=env, capture_output=True, text=True).stdout.split("\n")[0],
        "pages_total": pages, "refs_start_page": int(re.findall(r"REFSTART (\d+)", texlog)[-1]),
        "latex_errors": len(re.findall(r"^! ", texlog, re.M)),
        "undefined_citations": sorted(set(re.findall(r"Citation `([^']+)' .*undefined", texlog))),
        "undefined_references": sorted(set(re.findall(r"Reference `([^']+)' .*undefined", texlog))),
        "bibtex_warnings": re.findall(r"^Warning--.*$", blg, re.M),
        "overfull_hbox": len(over), "overfull_over_1pt": [{"pt": w, "tex_line": l} for w, l in over if w > 1.0],
        "abstract_words": words(abs_txt), "caption_order": caporder, "aux_labels": labels,
        "figures": figmap, "commands": log, "doi": doi,
    }
    shutil.copy(os.path.join(build_dir, stem + ".tex"), out)
    shutil.copy(os.path.join(build_dir, stem + ".bbl"), out)
    shutil.copy(pdf, out)
    shutil.copy(bibsrc, os.path.join(out, bibname + ".bib"))
    for name in srcs:
        shutil.copy(os.path.join(build_dir, "figures", name), os.path.join(out, "figures", name))
    rec["outputs"] = {f: md5(os.path.join(out, f)) for f in
                      [stem + ".tex", stem + ".bbl", stem + ".pdf", bibname + ".bib"] + ["figures/" + n for n in srcs]}
    json.dump(rec, open(os.path.join(build_dir, "receipt.json"), "w"), indent=1, ensure_ascii=False)
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplement", action="store_true")
    ap.add_argument("--doi", default=None)
    ap.add_argument("--out", default=os.path.join(REPO, "manuscript/lncs_latex"))
    ap.add_argument("--build", default=None)
    a = ap.parse_args()
    src = os.path.join(REPO, "manuscript", "supplementary_LNBI.md" if a.supplement else "full_paper_LNBI.md")
    tag = "supplement" if a.supplement else "chapter"
    bd = a.build or os.path.join(REPO, "results_v2/S7/build", tag)
    r = build(src, os.path.abspath(a.out), os.path.abspath(bd), a.supplement, a.doi, tag)
    print(json.dumps({k: r[k] for k in ("tag", "src_md5", "pages_total", "refs_start_page", "latex_errors",
          "undefined_citations", "undefined_references", "overfull_hbox", "overfull_over_1pt", "abstract_words",
          "caption_order", "aux_labels")}, ensure_ascii=False))
