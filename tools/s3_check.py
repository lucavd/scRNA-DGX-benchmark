#!/usr/bin/env python3
"""S3 gates G2-G4 and prediction P5 (docs/steps/S3.md). Run from the repo root.

Usage: python3 -B tools/s3_check.py [--ms manuscript/full_paper_LNBI.md] [--bib manuscript/bibliography/cibb2026_references.bib]
       [--diary manuscript/revisione_n2/piano/IMPL_diario.csv | --diary-glob 'manuscript/revisione_n2/S3/diario_R*.csv']
Writes manuscript/revisione_n2/S3/check<suffix>.json. Standard library only (pandoc via quarto).
"""
import argparse, csv, glob, hashlib, json, os, re, subprocess, sys, math
S3 = "manuscript/revisione_n2/S3"
ap = argparse.ArgumentParser()
ap.add_argument("--ms", default="manuscript/full_paper_LNBI.md")
ap.add_argument("--bib", default="manuscript/bibliography/cibb2026_references.bib")
ap.add_argument("--diary", default="manuscript/revisione_n2/piano/IMPL_diario.csv")
ap.add_argument("--diary-glob", default=None)
ap.add_argument("--suffix", default="")
a = ap.parse_args()
res = {"ms": a.ms, "ms_md5": hashlib.md5(open(a.ms, "rb").read()).hexdigest()}
ms = open(a.ms, encoding="utf-8").read()
bib = open(a.bib, encoding="utf-8").read()
def rd(f):
    with open(f, newline="", encoding="utf-8") as fh: return list(csv.DictReader(fh))
# ---------- G2: plan coverage
led = rd("manuscript/revisione_n2/piano/ledger.csv")
prim = {r["id"] for r in led if r["step"] == "S3" and r["final"] == r["id"]}
diary = []
for f in (sorted(glob.glob(a.diary_glob)) if a.diary_glob else [a.diary]): diary += rd(f)
cnt = {}
for r in diary: cnt[r["id"]] = cnt.get(r["id"], 0) + 1
ok_esiti = {"fatto", "rimandato", "non applicabile", "deciso-diversamente"}
g2 = {"n_primary": len(prim), "missing": sorted(prim - set(cnt)), "duplicated": sorted(k for k, v in cnt.items() if v > 1),
      "not_s3_primary": sorted(set(cnt) - prim),
      "bad_esito": sorted(r["id"] for r in diary if r["esito"] not in ok_esiti),
      "rimandato_without_reason": sorted(r["id"] for r in diary if r["esito"] == "rimandato" and not re.search(r"S[4-7]", r.get("note", "")))}
g2["esiti"] = {}
for r in diary: g2["esiti"][r["esito"]] = g2["esiti"].get(r["esito"], 0) + 1
g2["pass"] = not (g2["missing"] or g2["duplicated"] or g2["bad_esito"] or g2["rimandato_without_reason"])
res["G2"] = g2
# ---------- G3: receipts
def num(s):
    s = str(s).strip().replace("\u2009", "")
    m = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?", s, re.I)
    if not m: return (None, None)
    tok = m.group(0).replace(",", "")
    return (float(tok), len(tok.split(".")[1]) if "." in tok and "e" not in tok.lower() else 0)
receipts, recomputed, g3_err = [], {}, []
for f in sorted(glob.glob(f"{S3}/ricevute_R*.csv")): receipts += rd(f)
for f in sorted(glob.glob(f"{S3}/valori_R*.py")):
    p = subprocess.run([sys.executable, "-B", f], capture_output=True, text=True, timeout=600)
    if p.returncode != 0: g3_err.append(f"{f}: exit {p.returncode}: {p.stderr[-300:]}"); continue
    try: recomputed.update(json.loads(p.stdout[p.stdout.index("{"):]))
    except Exception as ex: g3_err.append(f"{f}: bad JSON ({ex})")
edits = {}
for f in sorted(glob.glob(f"{S3}/edits_R*.csv")):
    for r in rd(f): edits[r["edit_id"]] = r
scelte_txt = "".join(open(f, encoding="utf-8").read() for f in sorted(glob.glob(f"{S3}/scelte_R*.md")))
mism = []
for r in receipts:
    rid = r["ricevuta_id"]
    if rid not in recomputed: mism.append({"ricevuta": rid, "why": "not recomputed by valori script"}); continue
    v_re, v_rc = recomputed[rid], r["valore_letto"]
    a_re, _ = num(v_re); a_rc, _ = num(v_rc)
    if a_re is None or a_rc is None:
        if str(v_re).strip() != str(v_rc).strip(): mism.append({"ricevuta": rid, "why": f"letto {v_rc!r} != ricalcolato {v_re!r}"})
    elif not math.isclose(a_re, a_rc, rel_tol=1e-6, abs_tol=1e-9):
        mism.append({"ricevuta": rid, "why": f"letto {v_rc} != ricalcolato {v_re}"})
    w = r["valore_scritto"]
    if r["edit_id"].startswith("scelte:"):
        target = scelte_txt
    else:
        e = edits.get(r["edit_id"])
        if e is None: mism.append({"ricevuta": rid, "why": f"edit {r['edit_id']} not found"}); continue
        target = e["nuovo"]
    if w not in target: mism.append({"ricevuta": rid, "why": f"valore_scritto {w!r} not in edit text"})
    a_w, d_w = num(w)
    if a_w is not None and a_rc is not None and not r.get("arrotondamento", "").startswith("nessun-controllo"):
        tol = 0.5 * 10 ** (-d_w) + 1e-9
        if abs(abs(a_rc) - abs(a_w)) > tol and abs(abs(a_rc) * 100 - abs(a_w)) > tol:
            mism.append({"ricevuta": rid, "why": f"scritto {w} is not letto {a_rc} rounded to {d_w} decimals ({r.get('arrotondamento','')})"})
res["G3"] = {"n_receipts": len(receipts), "n_recomputed": len(recomputed), "script_errors": g3_err, "mismatches": mism,
             "pass": not g3_err and not mism and len(receipts) > 0}
# ---------- G4: text integrity
dashes = [i + 1 for i, l in enumerate(ms.splitlines()) if "\u2013" in l or "\u2014" in l]
keys = set(re.findall(r"@\{?([A-Za-z][\w:.-]*\w)", " ".join(re.findall(r"\[[^\]]*@[^\]]*\]", ms))))
bibkeys = set(re.findall(r"@\w+\{([^,\s]+),", bib))
missing_keys = sorted(keys - bibkeys)
pd_ok, pd_msg = None, ""
try:
    p = subprocess.run(["/usr/local/bin/quarto", "pandoc", os.path.basename(a.ms), "--citeproc", "-t", "html", "-o", "/tmp/s3_check_render.html"],
                       cwd=os.path.dirname(a.ms) or ".", capture_output=True, text=True, timeout=300)
    pd_ok = p.returncode == 0; pd_msg = (p.stderr or "")[-1500:]
except Exception as ex: pd_ok, pd_msg = False, str(ex)
res["G4"] = {"dash_lines": dashes, "cited_keys": len(keys), "missing_keys": missing_keys, "pandoc_ok": pd_ok,
             "pandoc_warnings": pd_msg, "pass": not dashes and not missing_keys and bool(pd_ok)}
# ---------- P5: words
def words(t): return len(t.split())
lines = ms.splitlines()
def idx(h): return next((i for i, l in enumerate(lines) if l.strip() == h), None)
i0, i1 = idx("# Introduction"), idx("# Conflict of Interest")
res["P5"] = {"body_words": words("\n".join(lines[i0:i1])) if i0 is not None and i1 else None, "file_words": words(ms)}
# abstract words (P1)
ab = next((l for l in lines if l.startswith("**Abstract.**")), "")
res["P1_abstract_words"] = words(ab.replace("**Abstract.**", "")) if ab else None
json.dump(res, open(f"{S3}/check{a.suffix}.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: (v.get("pass") if isinstance(v, dict) and "pass" in v else v) for k, v in res.items()}, ensure_ascii=False))
print("G2", {k: g2[k] for k in ("missing", "duplicated", "bad_esito", "rimandato_without_reason")}, g2["esiti"])
print("G3", len(mism), mism[:15], g3_err[:5])
print("G4", dashes, missing_keys, pd_ok, pd_msg[-400:])
