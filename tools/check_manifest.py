#!/usr/bin/env python3
"""Compare raw result directories against the md5 manifest (decision D-08).

Usage: python3 -B tools/check_manifest.py [--manifest PATH] [--out JSON]
Exit code 0 only if every manifest file exists with the same size and md5
and no new file appeared under results/ or SPATIAL/results/.
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--manifest", default="manifests/raw_results_md5_2026-11-03.tsv")
ap.add_argument("--out", default=None)
a = ap.parse_args()

def md5(p, bs=1 << 22):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(bs), b""):
            h.update(b)
    return h.hexdigest()

rows = [l.rstrip("\n").split("\t") for l in open(a.manifest)][1:]
t0 = time.time()
diff = []
for path, nbytes, m, _tracked in rows:
    p = Path(path)
    if not p.exists():
        diff.append({"path": path, "problem": "missing"}); continue
    if p.stat().st_size != int(nbytes):
        diff.append({"path": path, "problem": "size", "expected": int(nbytes), "found": p.stat().st_size}); continue
    got = md5(p)
    if got != m:
        diff.append({"path": path, "problem": "md5", "expected": m, "found": got})
listed = {r[0] for r in rows}
new = []
for root in ("results", "SPATIAL/results"):
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            q = os.path.join(dp, f)
            if q not in listed and f != ".gitkeep":
                new.append(q)
res = {"manifest": a.manifest, "n_files": len(rows), "n_differences": len(diff),
       "differences": diff, "n_new_files": len(new), "new_files": sorted(new),
       "seconds": round(time.time() - t0, 1),
       "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
print(json.dumps({k: v for k, v in res.items() if k not in ("differences", "new_files")}))
if a.out:
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
sys.exit(0 if not diff and not new else 1)
