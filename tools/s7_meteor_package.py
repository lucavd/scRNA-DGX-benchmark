#!/usr/bin/env python3
"""S7: METEOR submission package of the LNBI chapter (gate G5).

From the outputs of tools/s7_md2lncs.py (manuscript/lncs_latex/) it builds
manuscript/meteor/:
  full_paper_LNBI_source.zip   .tex, .bbl, cibb2026_references.bib, llncs.cls, splncs04.bst,
                               aliascnt.sty, figures/fig1.pdf ... fig4.pdf
  full_paper_LNBI.pdf          compiled chapter
  figures/fig1.pdf ...         figure files named after their number
  disclosure_of_interests.txt  the sentence of the .tex, to paste in METEOR
  zenodo/supplementary_LNBI.pdf  Supplementary Material for the archived release
  package.json                 md5 of every file and the clean-build test
The zip is then extracted into an empty temporary directory and compiled from
scratch (pdflatex, bibtex, pdflatex x2): 0 errors, 0 undefined citations or
references, same page count as the build receipt.

Usage: python3 -B tools/s7_meteor_package.py
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.expanduser("~/.TinyTeX/bin/x86_64-linux")
L = os.path.join(REPO, "manuscript/lncs_latex")
M = os.path.join(REPO, "manuscript/meteor")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


rec = json.load(open(os.path.join(REPO, "results_v2/S7/build/chapter/receipt.json")))
srec = json.load(open(os.path.join(REPO, "results_v2/S7/build/supplement/receipt.json")))
for r in (rec, srec):
    for f, h in r["outputs"].items():
        if md5(os.path.join(L, f)) != h:
            sys.exit("lncs_latex/%s changed after the build receipt" % f)
if os.path.isdir(M):
    for sub in ("figures", "zenodo"):
        shutil.rmtree(os.path.join(M, sub), ignore_errors=True)
os.makedirs(os.path.join(M, "figures"), exist_ok=True)
os.makedirs(os.path.join(M, "zenodo"), exist_ok=True)
stem = "full_paper_LNBI"
src_files = [stem + ".tex", stem + ".bbl", "llncs.cls", "splncs04.bst"]
zp = os.path.join(M, stem + "_source.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in src_files:
        z.write(os.path.join(L, f), f)
    z.write(os.path.join(L, "cibb2026_references.bib"), "cibb2026_references.bib")
    z.write(os.path.join(REPO, "tools/lncs_support/aliascnt.sty"), "aliascnt.sty")
    for f in rec["figures"]:
        z.write(os.path.join(L, f["file"]), f["file"])
shutil.copy(os.path.join(L, stem + ".pdf"), M)
for f in rec["figures"]:
    shutil.copy(os.path.join(L, f["file"]), os.path.join(M, f["file"]))
shutil.copy(os.path.join(L, "supplementary_LNBI.pdf"), os.path.join(M, "zenodo"))
tex = open(os.path.join(L, stem + ".tex"), encoding="utf-8").read()
disc = re.search(r"\\subsubsection\{\\discintname\}\s*(.*?)\s*\\end\{credits\}", tex, re.S).group(1).strip()
md = open(os.path.join(REPO, "manuscript/full_paper_LNBI.md"), encoding="utf-8").read()
disc_md = re.search(r"(?ms)^# Disclosure of Interests\s*\n(.*?)(?=^# )", md).group(1).strip()
open(os.path.join(M, "disclosure_of_interests.txt"), "w", encoding="utf-8").write(disc + "\n")
# clean build from the zip
tmp = tempfile.mkdtemp(prefix="lnbi_meteor_")
with zipfile.ZipFile(zp) as z:
    z.extractall(tmp)
os.remove(os.path.join(tmp, stem + ".bbl"))  # rebuilt by bibtex
env = dict(os.environ, PATH=TEX + ":" + os.environ["PATH"])
cmds = []
for cmd in (["pdflatex", "-interaction=nonstopmode", stem + ".tex"], ["bibtex", stem],
            ["pdflatex", "-interaction=nonstopmode", stem + ".tex"], ["pdflatex", "-interaction=nonstopmode", stem + ".tex"]):
    r = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True)
    cmds.append([" ".join(cmd), r.returncode])
log = open(os.path.join(tmp, stem + ".log"), encoding="latin-1").read()
pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", os.path.join(tmp, stem + ".pdf")],
            capture_output=True, text=True).stdout).group(1))
clean = {"dir": tmp, "commands": cmds, "pages": pages, "latex_errors": len(re.findall(r"^! ", log, re.M)),
         "undefined_citations": sorted(set(re.findall(r"Citation `([^']+)' .*undefined", log))),
         "undefined_references": sorted(set(re.findall(r"Reference `([^']+)' .*undefined", log))),
         "bbl_identical": md5(os.path.join(tmp, stem + ".bbl")) == md5(os.path.join(L, stem + ".bbl"))}
clean["pass"] = (clean["latex_errors"] == 0 and not clean["undefined_citations"] and not clean["undefined_references"]
                 and pages == rec["pages_total"] and clean["bbl_identical"])
shutil.rmtree(tmp)
# alternative texts: every number of the draft occurs in the chapter
NUM = re.compile(r"(?<![A-Za-z0-9_.\-])\d[\d,]*(?:\.\d+)?")
alt = open(os.path.join(M, "alt_text_draft.md"), encoding="utf-8").read().split("## Figure 1", 1)[1]
alt = re.sub(r"\(figures/fig\d\.pdf\)|## Figure \d", " ", alt)
chap_nums = {m.group(0).rstrip(",") for m in NUM.finditer(md)}
alt_missing = sorted({m.group(0).rstrip(",") for m in NUM.finditer(alt)} - chap_nums)
files = {}
for root, _, fs in os.walk(M):
    for f in fs:
        p = os.path.join(root, f)
        if f != "package.json":
            files[os.path.relpath(p, M)] = md5(p)
with zipfile.ZipFile(zp) as z:
    zip_list = sorted(z.namelist())
out = {"files": dict(sorted(files.items())), "zip_contents": zip_list, "clean_build": clean,
       "disclosure_tex_equals_md": disc == disc_md, "disclosure": disc,
       "figures": [{"number": f["number"], "file": f["file"], "source": f["source"],
                    "same_md5_as_source": md5(os.path.join(M, f["file"])) == md5(os.path.join(REPO, f["source"]))}
                   for f in rec["figures"]],
       "alt_text_numbers_not_in_chapter": alt_missing,
       "chapter_pages": rec["pages_total"], "supplement_pages": srec["pages_total"]}
json.dump(out, open(os.path.join(M, "package.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("zip_contents", "clean_build", "disclosure_tex_equals_md", "figures", "alt_text_numbers_not_in_chapter",
                                      "chapter_pages", "supplement_pages")}, ensure_ascii=False))
