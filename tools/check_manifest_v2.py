#!/usr/bin/env python3
"""Compare SPATIAL/results_v2 against its own md5 manifest (written in step S1).

Usage: python3 -B tools/check_manifest_v2.py [--out JSON]
Exit code 0 only if every listed file that is present has the same size and
md5, and no missing file was ever tracked by git. The S1 manifest was written
on the full output set; 65 .log files (ignored by .gitignore) and the cluster
CSVs of later repeats were never committed, so they are absent from the
checkout by construction: they are reported as missing_never_tracked.
"""
import subprocess
import argparse, hashlib, json, os, sys, time
from pathlib import Path

ROOT = Path("SPATIAL/results_v2")
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=None); a = ap.parse_args()

def md5(p, bs=1 << 22):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(bs), b""):
            h.update(b)
    return h.hexdigest()

rows = [l.rstrip("\n").split("\t") for l in open(ROOT / "manifest_md5.tsv") if l.strip()]
diff = []
for rel, nbytes, m in rows:
    p = ROOT / rel
    if not p.exists():
        diff.append({"path": rel, "problem": "missing"}); continue
    if p.stat().st_size != int(nbytes):
        diff.append({"path": rel, "problem": "size"}); continue
    if md5(p) != m:
        diff.append({"path": rel, "problem": "md5"})
tracked_ever = set(subprocess.run(
    ["git", "log", "--all", "--name-only", "--format=", "--", str(ROOT)],
    capture_output=True, text=True, check=True).stdout.split())
for d in diff:
    if d["problem"] == "missing":
        d["ever_tracked"] = os.path.normpath(str(ROOT / d["path"])) in tracked_ever
bad = [d for d in diff if d["problem"] != "missing" or d.get("ever_tracked")]
listed = {os.path.normpath(r[0]) for r in rows}
new = sorted(os.path.normpath(os.path.relpath(os.path.join(dp, f), ROOT))
             for dp, _d, fn in os.walk(ROOT) for f in fn
             if os.path.normpath(os.path.relpath(os.path.join(dp, f), ROOT)) not in listed
             and f != "manifest_md5.tsv")
res = {"manifest": str(ROOT / "manifest_md5.tsv"), "n_files": len(rows), "n_present_checked": len(rows) - sum(d["problem"] == "missing" for d in diff),
       "n_failures": len(bad), "n_missing_never_tracked": sum(1 for d in diff if d["problem"] == "missing" and not d.get("ever_tracked")),
       "differences": diff, "n_unlisted": len(new), "unlisted": new,
       "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
print(json.dumps({k: v for k, v in res.items() if k not in ("differences", "unlisted")}))
if a.out:
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
sys.exit(0 if not bad else 1)
