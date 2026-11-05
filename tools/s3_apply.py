#!/usr/bin/env python3
"""S3 (D-17): apply the region edit files to the manuscript and the bibliography in one pass.

Usage: python3 -B tools/s3_apply.py [--approved CODE,CODE,...] [--dry-run]
Reads manuscript/revisione_n2/S3/edits_R*.csv. Every `vecchio` must occur exactly once in the
file as it was BEFORE this run (spans are located on the original text, then replaced from the
end, so no edit sees another edit's output). Overlapping spans, spans outside the region's line
range and non-unique anchors abort the run. Edits with a non-empty `scelta_pi` are applied only
if their code is in --approved. Writes manuscript/revisione_n2/S3/apply_log.json and rebuilds
manuscript/revisione_n2/piano/IMPL_diario.csv from diario_R*.csv. Standard library only.
"""
import argparse, csv, glob, hashlib, json, os, re, sys, datetime
S3 = "manuscript/revisione_n2/S3"
RANGES = {"R1": (1, 46), "R2": (47, 175), "R3": (176, 323), "R4": (410, 463)}
ap = argparse.ArgumentParser()
ap.add_argument("--approved", default="")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--out-suffix", default="", help="write <file><suffix> instead of overwriting (preview)")
ap.add_argument("--base-md5", default=None, help="expected md5 of the manuscript before applying")
a = ap.parse_args()
approved = {x.strip() for x in a.approved.split(",") if x.strip()}
ALL = "ALL" in approved
md5s = lambda b: hashlib.md5(b).hexdigest()
edits = []
for f in sorted(glob.glob(f"{S3}/edits_R*.csv")):
    reg = re.search(r"edits_(R\d)", f).group(1)
    with open(f, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            row["_region"] = reg; edits.append(row)
by_file = {}
for e in edits: by_file.setdefault(e["file"], []).append(e)
log = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "approved": sorted(approved),
       "files": {}, "applied": [], "pending": [], "errors": []}
for path, es in by_file.items():
    raw = open(path, "rb").read(); text = raw.decode("utf-8")
    if a.base_md5 and path.endswith(".md") and md5s(raw) != a.base_md5:
        log["errors"].append(f"{path}: md5 {md5s(raw)} != expected {a.base_md5}")
    line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
    def line_of(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos: lo = mid
            else: hi = mid - 1
        return lo + 1
    spans = []
    for e in es:
        old = e["vecchio"]
        n = text.count(old) if old else 0
        if n != 1:
            log["errors"].append(f"{e['edit_id']}: anchor occurs {n} times in {path}"); continue
        s = text.index(old); t = s + len(old)
        ln = line_of(s)
        if path.endswith(".md"):
            lo, hi = RANGES[e["_region"]]
            if not (lo <= ln <= hi and lo <= line_of(max(t - 1, s)) <= hi):
                log["errors"].append(f"{e['edit_id']}: span lines {ln}-{line_of(t-1)} outside {e['_region']} {lo}-{hi}")
            if e.get("riga") and str(e["riga"]).strip() not in ("", "0") and int(float(e["riga"])) != ln:
                log["errors"].append(f"{e['edit_id']}: declared line {e['riga']} but anchor starts at line {ln}")
        spans.append((s, t, e, ln))
    spans.sort(key=lambda x: x[0])
    for (s1, t1, e1, _), (s2, t2, e2, _) in zip(spans, spans[1:]):
        if s2 < t1: log["errors"].append(f"overlap: {e1['edit_id']} [{s1},{t1}) and {e2['edit_id']} [{s2},{t2})")
    keep = []
    for s, t, e, ln in spans:
        code = (e.get("scelta_pi") or "").strip()
        codes = {x.strip() for x in code.split(";") if x.strip()}
        if codes and not ALL and not codes <= approved:
            log["pending"].append({"edit_id": e["edit_id"], "scelta_pi": code, "line": ln}); continue
        keep.append((s, t, e, ln))
    spans = keep
    new = text
    for s, t, e, ln in sorted(spans, key=lambda x: -x[0]):
        rep = e["nuovo"]
        # removing a whole line: also drop its newline
        if rep == "" and (s == 0 or new[s - 1] == "\n") and new[t:t + 1] == "\n":
            t += 1
        new = new[:s] + rep + new[t:]
        log["applied"].append({"edit_id": e["edit_id"], "voci": e["voci"], "line": ln, "file": path})
    if path.endswith(".md"):
        new = re.sub(r"\n{3,}", "\n\n", new)
    log["files"][path] = {"md5_before": md5s(raw), "md5_after": md5s(new.encode("utf-8")), "n_applied": sum(1 for x in log["applied"] if x["file"] == path)}
    if not a.dry_run and not log["errors"]:
        open(path + a.out_suffix, "w", encoding="utf-8").write(new)
# diary
rows = []
for f in sorted(glob.glob(f"{S3}/diario_R*.csv")):
    with open(f, newline="", encoding="utf-8") as fh: rows += list(csv.DictReader(fh))
cols = ["id", "livello", "esito", "valore_inserito", "convenzione", "fonte_riletta", "riga", "data", "note"]
if not a.dry_run and not log["errors"] and not a.out_suffix:
    with open("manuscript/revisione_n2/piano/IMPL_diario.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(sorted(rows, key=lambda r: r["id"]))
log["n_diary_rows"] = len(rows)
log["dry_run"] = a.dry_run
json.dump(log, open(f"{S3}/apply_log{'_dry' if a.dry_run else ('_preview' if a.out_suffix else '')}.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({"errors": log["errors"][:30], "n_errors": len(log["errors"]), "applied": len(log["applied"]),
                  "pending": len(log["pending"]), "files": log["files"]}, indent=1, ensure_ascii=False))
sys.exit(1 if log["errors"] else 0)
