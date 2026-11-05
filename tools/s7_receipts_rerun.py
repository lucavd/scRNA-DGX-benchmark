#!/usr/bin/env python3
"""S7: re-check of the receipts that the S3/S5 checks could not recompute on the final text.

1. S3 receipts R2-R012, R2-R013, R2-R017 read Scanpy 1.12 source files from a
   temporary environment of step S2 that no longer exists. They are re-read
   here from a fresh Scanpy 1.12 installation (--scanpy-dir).
2. S3 receipts R2-R036, R2-R037, R2-R038 count rows of the concordance-metrics
   table, which step S6 moved from the chapter (Table 2) to the supplement
   (Table S2). They are recounted on Table S2.
3. The 5 text checks of tools/s5_check.py that look for sentences of the
   pre-cut text (captions shortened and summary sentences removed in S6):
   every number of each sentence must still occur, with its unit, in the final
   chapter or supplement; the sentence that now carries it is reported.

Usage: python3 -B tools/s7_receipts_rerun.py --scanpy-dir DIR --s5 results_v2/S7/rerun/s5_check.json --out OUT.json
"""
import argparse, csv, glob, json, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--scanpy-dir", required=True)
ap.add_argument("--s5", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
os.chdir(REPO)
rec = {}
for f in sorted(glob.glob("manuscript/revisione_n2/S3/ricevute_R*.csv")):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        rec[r["ricevuta_id"]] = r


def rx(path, pat):
    m = re.search(pat, open(path, encoding="utf-8").read())
    return m.group(1) if m else None


sp = os.path.join(a.scanpy_dir, "scanpy")
ver = rx(os.path.join(a.scanpy_dir, [d for d in os.listdir(a.scanpy_dir) if d.startswith("scanpy-") and d.endswith(".dist-info")][0], "METADATA"), r"(?m)^Version:\s*(\S+)")
new = {
    "R2-R012": rx(os.path.join(sp, "neighbors/__init__.py"), r"n_obs < (\d+)"),
    "R2-R013": rx(os.path.join(sp, "_settings/__init__.py"), r"_n_jobs: ClassVar = (\d+)"),
    "R2-R017": rx(os.path.join(sp, "neighbors/__init__.py"), r"n_obs < (\d+)"),
}
lines = open("manuscript/supplementary_LNBI.md", encoding="utf-8").read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith(": **Table S2.**"))
rows = []
for l in lines[i + 1:]:
    if l.startswith("|") and not l.startswith("|:") and not l.startswith("| Metric"):
        rows.append([c.strip() for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))])
    elif rows and not l.startswith("|"):
        break
new["R2-R036"] = str(len(rows))
new["R2-R037"] = str(len(set(x[-1] for x in rows)))
new["R2-R038"] = str(sum(1 for x in rows if x[-1] == "Clustering"))
receipts = []
for k, v in new.items():
    letto = rec[k]["valore_letto"].strip()
    receipts.append({"ricevuta": k, "valore_scritto": rec[k]["valore_scritto"], "valore_letto_S3": letto,
                     "riletto_S7": v, "ok": v is not None and float(v) == float(letto)})
# where the written words of R2-R036..38 now are
sup = open("manuscript/supplementary_LNBI.md", encoding="utf-8").read()
main = open("manuscript/full_paper_LNBI.md", encoding="utf-8").read()
for r in receipts:
    w = r["valore_scritto"].strip("`")
    r["written_in"] = [d for d, t in (("chapter", main), ("supplement", sup)) if w in t]

# S5 text checks on sentences cut in S6
s5 = json.load(open(a.s5))
NUMU = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(x|%| s| GiB| um)?")
final = main + "\n" + sup
sent = re.split(r"(?<=[.;])\s+|\n", final)
texts = []
for t in s5["G2_text"]:
    if t.get("ok"):
        continue
    toks = [(n, u or "") for n, u in NUMU.findall(t["string"])]
    found = []
    for n, u in toks:
        hits = [s.strip()[:160] for s in sent if re.search(r"(?<![\w.])%s%s" % (re.escape(n), re.escape(u)), s)]
        found.append({"number": n + u, "n_sentences": len(hits), "example": hits[0] if hits else None})
    texts.append({"check": t["check"], "string": t["string"], "numbers": found, "ok": all(f["n_sentences"] for f in found)})
out = {"scanpy_version": ver, "receipts": receipts, "s5_text_rechecks": texts,
       "pass": all(r["ok"] for r in receipts) and all(t["ok"] for t in texts)}
json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False)[:4000])
