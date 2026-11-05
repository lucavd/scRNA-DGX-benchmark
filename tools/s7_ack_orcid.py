#!/usr/bin/env python3
"""S7: ORCID of the first author and name of the language-model tool in the Acknowledgements (PI, 5 November 2026).

ORCID 0000-0003-4847-2333 checked on pub.orcid.org (record name: Luca Vedovelli, University of Padua).
Exact replacements with a declared number of occurrences; stops without writing if a count differs.
Usage: python3 -B tools/s7_ack_orcid.py
"""
import hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_OLD = "bibliography: bibliography/cibb2026_references.bib\n---\n"
YAML_NEW = "bibliography: bibliography/cibb2026_references.bib\norcid:\n  Luca Vedovelli: 0000-0003-4847-2333\n---\n"
edits = [
    ("manuscript/full_paper_LNBI.md", YAML_OLD, YAML_NEW),
    ("manuscript/supplementary_LNBI.md", YAML_OLD, YAML_NEW),
    ("manuscript/full_paper_LNBI.md",
     "The authors used a large language model-based assistant to check the analysis code",
     "The authors used a large language model-based assistant (Claude Opus 5.5, Anthropic) to check the analysis code"),
]
texts, log = {}, []
for path, old, new in edits:
    p = os.path.join(REPO, path)
    t = texts.get(p) or open(p, encoding="utf-8").read()
    if t.count(old) != 1:
        sys.exit("%s: expected 1 occurrence of %r, found %d" % (path, old[:40], t.count(old)))
    m0 = hashlib.md5(t.encode()).hexdigest()
    t = t.replace(old, new)
    texts[p] = t
    log.append({"file": path, "old": old, "new": new, "md5": [m0, hashlib.md5(t.encode()).hexdigest()]})
for p, t in texts.items():
    open(p, "w", encoding="utf-8").write(t)
json.dump({"orcid_check": "pub.orcid.org/v3.0/0000-0003-4847-2333/person: Luca Vedovelli; employment University of Padua",
           "edits": log}, open(os.path.join(REPO, "results_v2/S7/s7_ack_orcid.json"), "w"), indent=1, ensure_ascii=False)
print("ok", len(log))
