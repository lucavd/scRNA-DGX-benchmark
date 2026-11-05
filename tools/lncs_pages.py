#!/usr/bin/env python3
"""Count LNCS pages of a Markdown manuscript (provisional llncs build, S6).

Converts manuscript/full_paper_LNBI.md (or --src) into a provisional llncs
LaTeX document with pandoc, compiles it with pdflatex + bibtex (splncs04),
and writes a JSON receipt with total pages, the page on which the reference
list starts, word counts and md5 of every input. The definitive LaTeX source
is produced in S7; this build exists only to measure length.

Usage: python3 -B tools/lncs_pages.py [--src FILE] [--out DIR] [--tag NAME]
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.expanduser("~/.TinyTeX/bin/x86_64-linux")

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

def words(s):
    return len(s.split())

def split_md(md):
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    yaml = m.group(1)
    title = re.search(r'title:\s*"(.*)"', yaml).group(1)
    rest = md[m.end():]
    i = rest.index("\n# ")  # body starts at the first top-level heading
    head, body = rest[:i], rest[i + 1:]
    paras = [p.strip() for p in head.split("\n\n") if p.strip()]
    authors = paras[0]
    insts = [p for p in paras if p.startswith("^")]
    abstract = ([p for p in paras if p.startswith("**Abstract.**")] or [""])[0]
    keywords = ([p for p in paras if p.startswith("**Keywords:**")] or [""])[0]
    return title, authors, insts, abstract, keywords, body

def pandoc(text, extra=()):
    r = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", "--natbib",
                        "--wrap=preserve", *extra], input=text, capture_output=True,
                       text=True, check=True)
    return r.stdout

def fix_cites(tex):
    # splncs04 is numeric: every natbib form becomes \cite, keys without spaces
    tex = re.sub(r"\\cite(?:p|t|alp|alt|yearpar|year)\{", r"\\cite{", tex)
    return re.sub(r"\\cite\{([^}]*)\}", lambda m: r"\cite{" + ",".join(k.strip() for k in m.group(1).split(",")) + "}", tex)

def build(src, out, tag):
    md = open(src, encoding="utf-8").read()
    title, authors, insts, abstract, keywords, body = split_md(md)
    # body: drop pandoc table attributes and the References heading
    body = re.sub(r"\s*\{#tbl:[^}]*\}", "", body)
    body_main, _, _ = body.partition("\n# References")
    # figures: use the vector PDF next to each PNG when it exists
    def figpath(mm):
        p = mm.group(1)
        q = os.path.normpath(os.path.join(os.path.dirname(src), p))
        pdf = os.path.splitext(q)[0] + ".pdf"
        return "](" + (pdf if os.path.exists(pdf) else q) + ")"
    body_main = re.sub(r"\]\(([^)]+\.png)\)", figpath, body_main)
    sec = {}
    for blk in re.split(r"\n(?=# )", body_main):
        name = blk.split("\n", 1)[0].lstrip("# ").strip()
        sec[name] = words(blk)
    btex = fix_cites(pandoc(body_main))
    # authors and institutes
    alist = [a.strip() for a in re.split(r",\s+(?:and\s+)?(?=[A-Z])|\s+and\s+(?=[A-Z])", authors) if a.strip()]
    atex = []
    for a in alist:
        nm = re.sub(r"\^([0-9,]+)\^", "", a).strip()
        sup = re.search(r"\^([0-9,]+)\^", a)
        atex.append(nm + (r"\inst{%s}" % sup.group(1) if sup else ""))
    itex = []
    for p in insts:
        t = re.sub(r"^\^[0-9]+\^\s*", "", p)
        t = pandoc(t).strip()
        t = re.sub(r"\\texttt\{(.*?)\}\s*$", lambda m: r"\\ \email{" + m.group(1) + "}", t)
        itex.append(t)
    abs_txt = abstract.replace("**Abstract.**", "").strip()
    kw = keywords.replace("**Keywords:**", "").strip().replace("·", r"\and")
    bib = os.path.join(os.path.dirname(src), re.search(r"bibliography:\s*(\S+)", md).group(1))
    doc = r"""\documentclass[runningheads]{llncs}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{graphicx,booktabs,longtable,array,calc,amsmath,amssymb,xcolor}
\usepackage[hidelinks]{hyperref}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\pandocbounded}[1]{#1}
\def\LTcaptype{table}
\setkeys{Gin}{width=\linewidth,keepaspectratio}
\begin{document}
\title{%s}
\author{%s}
\authorrunning{L. Vedovelli et al.}
\institute{%s}
\maketitle
%s
%s
\typeout{REFSTART \thepage}
\bibliographystyle{splncs04}
\bibliography{refs}
\typeout{DOCEND \thepage}
\end{document}
""" % (pandoc(title).strip(), r" \and ".join(atex), " \\and\n".join(itex),
       ("\\begin{abstract}\n" + fix_cites(pandoc(abs_txt)).strip() + "\n\\keywords{" + kw + "}\n\\end{abstract}") if abs_txt else "", btex)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    open(os.path.join(out, "paper.tex"), "w", encoding="utf-8").write(doc)
    for f in ("llncs.cls", "splncs04.bst"):
        shutil.copy(os.path.join(REPO, "manuscript/lncs_latex", f), out)
    support = os.path.join(REPO, "tools/lncs_support")
    support_md5 = {}
    for f in sorted(os.listdir(support)):  # aliascnt.sty from TeX Live 2025 oberdiek
        shutil.copy(os.path.join(support, f), out)
        support_md5[f] = md5(os.path.join(support, f))
    shutil.copy(bib, os.path.join(out, "refs.bib"))
    env = dict(os.environ, PATH=TEX + ":" + os.environ["PATH"])
    log = []
    for cmd in (["pdflatex", "-interaction=nonstopmode", "paper.tex"], ["bibtex", "paper"],
                ["pdflatex", "-interaction=nonstopmode", "paper.tex"],
                ["pdflatex", "-interaction=nonstopmode", "paper.tex"]):
        r = subprocess.run(cmd, cwd=out, env=env, capture_output=True, text=True)
        log.append((" ".join(cmd), r.returncode))
    texlog = open(os.path.join(out, "paper.log"), encoding="latin-1").read()
    pdf = os.path.join(out, "paper.pdf")
    if not os.path.exists(pdf):
        sys.exit("no PDF produced; see " + os.path.join(out, "paper.log"))
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf],
                capture_output=True, text=True).stdout).group(1))
    refstart = int(re.findall(r"REFSTART (\d+)", texlog)[-1])
    errors = len(re.findall(r"^! ", texlog, re.M))
    undef = sorted(set(re.findall(r"Citation `([^']+)' .*undefined", texlog)))
    overfull = len(re.findall(r"Overfull \\hbox", texlog))
    rec = {
        "tag": tag, "at": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "src": os.path.relpath(src, REPO), "src_md5": md5(src), "bib_md5": md5(bib),
        "llncs_md5": md5(os.path.join(out, "llncs.cls")), "support_md5": support_md5, "pandoc": subprocess.run(["pandoc", "--version"],
            capture_output=True, text=True).stdout.split("\n")[0],
        "pages_total": pages, "refs_start_page": refstart,
        "pages_before_refs": refstart, "latex_errors": errors, "undefined_citations": undef,
        "overfull_hbox": overfull, "abstract_words": words(abs_txt),
        "body_words_intro_to_end": sum(sec.values()), "section_words": sec,
        "commands": log, "pdf": os.path.relpath(os.path.join(out, "paper.pdf"), REPO),
    }
    json.dump(rec, open(os.path.join(out, "pages.json"), "w"), indent=1, ensure_ascii=False)
    return rec

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(REPO, "manuscript/full_paper_LNBI.md"))
    ap.add_argument("--out", default=os.path.join(REPO, "results_v2/S6/pages/current"))
    ap.add_argument("--tag", default="current")
    a = ap.parse_args()
    r = build(os.path.abspath(a.src), os.path.abspath(a.out), a.tag)
    print(json.dumps({k: r[k] for k in ("tag", "src_md5", "pages_total", "refs_start_page",
          "latex_errors", "undefined_citations", "overfull_hbox", "abstract_words",
          "body_words_intro_to_end")}, ensure_ascii=False))
