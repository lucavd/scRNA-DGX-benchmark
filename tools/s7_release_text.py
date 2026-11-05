#!/usr/bin/env python3
"""S7: repository address and archive DOI in the chapter and in the supplement (PI choice, decision D-25).

Exact replacements with a declared number of occurrences; stops without writing if a count differs.
Usage: python3 -B tools/s7_release_text.py --doi 10.5281/zenodo.NNN
"""
import argparse, hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--doi", required=True); a = ap.parse_args()
NEW = "https://github.com/lucavd/scRNA-DGX-benchmark"
DOIURL = "https://doi.org/" + a.doi
edits = [
    ("manuscript/full_paper_LNBI.md",
     "are available at <https://github.com/lucavd/2026.scRNA_DGX>. The Supplementary Material (extended methods, results and discussion, Supplementary Tables S1-S8 and Figures S1-S3) is archived with the code.",
     "are available at <%s> (release v1.0.0) and archived on Zenodo (<%s>). The Supplementary Material (extended methods, results and discussion, Supplementary Tables S1-S8 and Figures S1-S3) is included in the archive." % (NEW, DOIURL)),
    ("manuscript/supplementary_LNBI.md",
     "result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX>.",
     "result JSON files are available at <%s> (release v1.0.0) and archived on Zenodo (<%s>)." % (NEW, DOIURL)),
]
log = []
texts = {}
for path, old, new in edits:
    p = os.path.join(REPO, path)
    t = texts.get(p) or open(p, encoding="utf-8").read()
    if t.count(old) != 1:
        sys.exit("%s: expected 1 occurrence, found %d" % (path, t.count(old)))
    m0 = hashlib.md5(t.encode()).hexdigest()
    t = t.replace(old, new)
    texts[p] = t
    log.append({"file": path, "old": old, "new": new, "md5": [m0, hashlib.md5(t.encode()).hexdigest()]})
for p, t in texts.items():
    if "\u2013" in t or "\u2014" in t:
        sys.exit(p + ": dash characters")
    open(p, "w", encoding="utf-8").write(t)
json.dump({"doi": a.doi, "edits": log}, open(os.path.join(REPO, "results_v2/S7/s7_release_text.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(log, ensure_ascii=False, indent=1))
