#!/usr/bin/env python3
"""Evaluate the S1 spatial rerun: tables, gates G2-G5, predictions P1-P6, RERUN_REPORT.md.

Reads only files under SPATIAL/results_v2/ (new runs) and the March JSONs under
SPATIAL/results/ (read-only). Writes:
    SPATIAL/results_v2/s1_evaluation.json   every number with its source
    SPATIAL/results_v2/s1_step_stats.csv    per run, platform, step: mean/SD on reps 1-5 and 2-5
    SPATIAL/results_v2/RERUN_REPORT.md      report requested by the brief

    python SPATIAL/scripts/s1_rerun_report.py --root SPATIAL [--g1-before F --g1-after F]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

PLATS = [("visium", "Visium v1"), ("visium_hd_square_008um", "Visium HD 8 um"),
         ("visium_hd_square_002um", "Visium HD 2 um")]
RUNS = {"dgx_cpu": ("cpu", 100, "CPU reference, DGX poddgx02 (100 CPU)"),
        "server_gpu": ("gpu", None, "GPU, RTX 4090 workstation"),
        "server_cpu": ("cpu", 128, "CPU control, workstation (128 threads)")}
STEPS = ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca",
         "expression_neighbors", "leiden", "umap", "spatial_neighbors",
         "spatial_autocorr_moran", "spatial_autocorr_geary", "co_occurrence",
         "nhood_enrichment", "ligrec", "total"]
GSTEPS = ["pca", "leiden", "umap", "spatial_autocorr_moran", "spatial_autocorr_geary"]
REPS = [1, 2, 3, 4, 5]
B, SEED = 2000, 20261103
SAFE = ("top", "dockerd", "containerd", "ps")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def load_run(root, run, plat):
    dev = RUNS[run][0]
    d = root / "results_v2" / run
    out = {}
    for r in REPS:
        p = d / f"spatial_{dev}_{plat}_r{r}_results.json"
        if p.exists():
            out[r] = {"json": json.loads(p.read_text()), "path": str(p), "md5": md5(p)}
            co = d / f"spatial_{dev}_{plat}_r{r}_co_occurrence.npy"
            nh = d / f"spatial_{dev}_{plat}_r{r}_nhood_enrichment.npy"
            out[r]["co"] = np.load(co) if co.exists() else None
            out[r]["nh"] = np.load(nh) if nh.exists() else None
    return out


def t(rec, step):
    v = rec["json"]["timings"].get(step, -1)
    return np.nan if v is None or v < 0 else float(v)


def boot_ratio(num, den, rng, den_const=None):
    num = np.asarray(num, float)
    est = num.mean() / (den_const if den_const is not None else np.mean(den))
    bs = []
    for _ in range(B):
        a = rng.choice(num, len(num), replace=True).mean()
        b = den_const if den_const is not None else rng.choice(np.asarray(den, float), len(den), replace=True).mean()
        bs.append(a / b)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def verdict(lo, hi, a, b):
    if a <= lo and hi <= b:
        return "confermata"
    if hi < a or lo > b:
        return "smentita"
    return "indeterminata"


def parse_snapshot(p):
    s = Path(p).read_text() if Path(p).exists() else ""
    la = re.search(r"loadavg: ([\d.]+)", s)
    nj = re.search(r"node_jobs: (.*)", s)
    procs = []
    lines = s.split("top_processes:")[-1].strip().splitlines() if "top_processes:" in s else []
    for ln in lines:
        f = ln.split()
        if len(f) >= 12 and f[0].isdigit():          # top: PID USER .. %CPU(8) .. COMMAND(11)
            procs.append((f[11], float(f[8].replace(",", "."))))
        elif len(f) >= 5 and f[0].isdigit():         # ps: PID USER %CPU ETIME COMM
            try:
                procs.append((f[4], float(f[2])))
            except ValueError:
                pass
    return {"exists": bool(s), "load1": float(la.group(1)) if la else None,
            "node_jobs": nj.group(1).split() if nj else None, "procs": procs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="SPATIAL")
    ap.add_argument("--g1-before")
    ap.add_argument("--g1-after")
    a = ap.parse_args()
    root = Path(a.root)
    rng = np.random.default_rng(SEED)
    ev = {"gates": {}, "predictions": {}, "tables": {}, "sources": {}}

    data = {(run, p): load_run(root, run, p) for run in RUNS for p, _ in PLATS}
    march = {}
    for p, _ in PLATS:
        for dev in ("cpu", "gpu"):
            for r in REPS:
                f = root / "results" / f"spatial_{dev}_{p}_r{r}_results.json"
                march[(dev, p, r)] = json.loads(f.read_text())["timings"]

    # ---- per-step statistics
    rows = []
    for (run, p), recs in data.items():
        for s in STEPS:
            v = {r: t(recs[r], s) for r in recs}
            all5 = np.array([v[r] for r in REPS if r in v])
            r25 = np.array([v[r] for r in REPS[1:] if r in v])
            med = np.nanmedian(all5) if len(all5) else np.nan
            rows.append({"run": run, "platform": p, "step": s, "n": int(np.sum(~np.isnan(all5))),
                         **{f"r{r}": v.get(r) for r in REPS},
                         "mean_1_5": np.nanmean(all5) if len(all5) else np.nan,
                         "sd_1_5": np.nanstd(all5, ddof=1) if np.sum(~np.isnan(all5)) > 1 else np.nan,
                         "mean_2_5": np.nanmean(r25) if len(r25) else np.nan,
                         "sd_2_5": np.nanstd(r25, ddof=1) if np.sum(~np.isnan(r25)) > 1 else np.nan,
                         "max_rel_dev_from_median": float(np.nanmax(np.abs(all5 - med)) / med) if len(all5) and med > 0 else np.nan})
    st = pd.DataFrame(rows)
    st.to_csv(root / "results_v2" / "s1_step_stats.csv", index=False)

    def mean(run, p, s, conv="1_5"):
        x = st[(st.run == run) & (st.platform == p) & (st.step == s)]
        return float(x[f"mean_{conv}"].iloc[0]) if len(x) else np.nan

    def vals(run, p, s, reps=REPS):
        return [t(data[(run, p)][r], s) for r in reps if r in data[(run, p)]]

    # ---- speedups
    sp = []
    for p, lab in PLATS:
        for s in STEPS:
            for ref, cpu_run in (("reference_dgx", "dgx_cpu"), ("control_server", "server_cpu")):
                for conv, reps in (("1_5", REPS), ("2_5", REPS[1:])):
                    c, g = vals(cpu_run, p, s, reps), vals("server_gpu", p, s, reps)
                    if c and g and not np.isnan(c).any() and not np.isnan(g).any():
                        e, lo, hi = boot_ratio(c, g, rng)
                        sp.append({"platform": p, "step": s, "cpu": ref, "convention": conv,
                                   "speedup": e, "ci_lo": lo, "ci_hi": hi})
    spd = pd.DataFrame(sp)
    spd.to_csv(root / "results_v2" / "s1_speedups.csv", index=False)

    # ---- G2 completeness
    n_json = sum(len(v) for v in data.values())
    keys_ok = all(all(k in rec["json"]["metadata"] for k in ("system", "steps_runtime", "groups"))
                  for v in data.values() for rec in v.values())
    snaps_missing = []
    for (run, p), recs in data.items():
        dev = RUNS[run][0]
        for r in REPS:
            for e in ("start", "end"):
                f = root / "results_v2" / run / "host_snapshots" / f"spatial_{dev}_{p}_r{r}_{e}.txt"
                if not f.exists():
                    snaps_missing.append(str(f))
    conc = {}
    for kind in ("concordance_reference", "concordance_server_control"):
        for p, _ in PLATS:
            pl, _, b = p.partition("_square")
            name = f"spatial_concordance_{'visium' if p == 'visium' else 'visium_hd'}{'' if p == 'visium' else '_square' + b}.json"
            f = root / "results_v2" / kind / name
            conc[(kind, p)] = json.loads(f.read_text()) if f.exists() else None
    mech_f = root / "results_v2" / "mechanism_dgx" / "mechanism_numba_threads.json"
    mech = json.loads(mech_f.read_text()) if mech_f.exists() else None
    g2 = (n_json == 45 and keys_ok and not snaps_missing and all(v is not None for v in conc.values()) and mech is not None)
    ev["gates"]["G2"] = {"pass": bool(g2), "n_result_json": n_json, "metadata_keys_ok": keys_ok,
                         "snapshots_missing": snaps_missing[:10], "n_snapshots_missing": len(snaps_missing),
                         "concordance_files_present": sum(v is not None for v in conc.values()),
                         "mechanism_json": mech is not None}

    # ---- G3 machine free
    g3 = {"server": [], "dgx": []}
    for (run, p), recs in data.items():
        dev = RUNS[run][0]
        for r in REPS:
            sd = root / "results_v2" / run / "host_snapshots"
            s0 = parse_snapshot(sd / f"spatial_{dev}_{p}_r{r}_start.txt")
            s1 = parse_snapshot(sd / f"spatial_{dev}_{p}_r{r}_end.txt")
            if run == "dgx_cpu":
                ok = (s0["node_jobs"] is not None and len(s0["node_jobs"]) == 1
                      and s1["node_jobs"] is not None and len(s1["node_jobs"]) == 1)
                g3["dgx"].append({"platform": p, "rep": r, "ok": ok, "jobs_start": s0["node_jobs"], "jobs_end": s1["node_jobs"],
                                  "load1_start": s0["load1"]})
            else:
                foreign0 = [x for x in s0["procs"] if x[1] > 50 and not x[0].startswith(SAFE)]
                foreign1 = [x for x in s1["procs"] if x[1] > 50 and not x[0].startswith(SAFE)]
                ok = s0["exists"] and s1["exists"] and s0["load1"] is not None and s0["load1"] <= 3.0 and not foreign0 and not foreign1
                g3["server"].append({"run": run, "platform": p, "rep": r, "ok": ok, "load1_start": s0["load1"],
                                     "load1_end": s1["load1"], "foreign_start": foreign0, "foreign_end": foreign1})
    ev["gates"]["G3"] = {"pass": all(x["ok"] for x in g3["server"] + g3["dgx"]) and len(g3["server"]) == 30 and len(g3["dgx"]) == 15,
                         "detail": g3}

    # ---- G4 threads
    g4 = []
    for run, (dev, ncpu, _) in RUNS.items():
        if dev != "cpu":
            continue
        for p, _ in PLATS:
            profs = []
            for r, rec in sorted(data[(run, p)].items()):
                md = rec["json"]["metadata"]
                sr = md["steps_runtime"]
                prof = tuple((k, sr[k]["start"].get("numba_num_threads")) for k in sr)
                first = md["threads_at_start"].get("numba_num_threads")
                profs.append(prof)
                g4.append({"run": run, "platform": p, "rep": r, "numba_at_start": first,
                           "affinity": md["system"]["affinity_n_cpus"], "requested": ncpu,
                           "ok": first == ncpu and md["system"]["affinity_n_cpus"] == ncpu,
                           "profile": [list(x) for x in prof]})
            same = len(set(profs)) == 1
            for x in g4:
                if x["run"] == run and x["platform"] == p:
                    x["profile_identical_across_reps"] = same
                    x["ok"] = x["ok"] and same
    ev["gates"]["G4"] = {"pass": bool(g4) and all(x["ok"] for x in g4) and len(g4) == 30, "detail": g4}

    # ---- G5 same groups
    g5 = []
    for p, _ in PLATS:
        lab_file = root / "results_v2" / "dgx_cpu" / f"spatial_cpu_{p}_r1_clusters.csv"
        lab_md5 = md5(lab_file) if lab_file.exists() else None
        ng_ref = data[("dgx_cpu", p)].get(1, {}).get("json", {}).get("results_summary", {}).get("n_groups_spatial_steps")
        ok_lab = True
        for run in RUNS:
            for r, rec in data[(run, p)].items():
                gi = rec["json"]["metadata"]["groups"]
                if run == "dgx_cpu" and r == 1:
                    continue
                ok_lab &= gi.get("labels_md5") == lab_md5 and gi.get("n_groups_used") == ng_ref
        co_ident = {}
        for run in ("dgx_cpu", "server_cpu"):
            cos = [rec["co"] for rec in data[(run, p)].values() if rec["co"] is not None]
            co_ident[run] = (len(cos) == 5 and all(np.array_equal(cos[0], c_, equal_nan=True) for c_ in cos)) if cos else None
        shapes = {run: sorted({tuple(rec["co"].shape) for rec in data[(run, p)].values() if rec["co"] is not None}) for run in RUNS}
        shapes_nh = {run: sorted({tuple(rec["nh"].shape) for rec in data[(run, p)].values() if rec["nh"] is not None}) for run in RUNS}
        computed = any(shapes.values())
        shape_ok = (not computed) or (len({s for v in shapes.values() for s in v}) == 1 and all(len(v) == 1 for v in shapes.values()))
        nh_ok = (not any(shapes_nh.values())) or len({s for v in shapes_nh.values() for s in v}) == 1
        mism = []
        for kind in ("concordance_reference", "concordance_server_control"):
            for rr in (conc.get((kind, p)) or []):
                for key in ("co_occurrence", "nhood_enrichment"):
                    if rr.get(key, {}).get("status") == "shape_mismatch":
                        mism.append((kind, rr["repeat_id"], key))
        ok = ok_lab and shape_ok and nh_ok and not mism and (not computed or all(v for v in co_ident.values()))
        g5.append({"platform": p, "labels_md5": lab_md5, "n_groups": ng_ref, "labels_consistent": ok_lab,
                   "cpu_co_occurrence_identical_across_reps": co_ident, "co_shapes": {k: [list(s) for s in v] for k, v in shapes.items()},
                   "nhood_shapes": {k: [list(s) for s in v] for k, v in shapes_nh.items()}, "shape_mismatch": mism, "ok": ok})
    ev["gates"]["G5"] = {"pass": all(x["ok"] for x in g5), "detail": g5}

    # ---- G1 (files produced by tools/manifest check)
    if a.g1_before and a.g1_after:
        b, f = json.loads(Path(a.g1_before).read_text()), json.loads(Path(a.g1_after).read_text())
        ev["gates"]["G1"] = {"pass": b["n_diff"] == 0 and f["n_diff"] == 0 and b["n_files"] == f["n_files"] == 921,
                             "before": b, "after": f}

    # ---- predictions
    P = ev["predictions"]
    p1 = {}
    for run in ("dgx_cpu", "server_cpu"):
        v = vals(run, "visium_hd_square_008um", "co_occurrence")
        ratio = float(np.max(v) / np.min(v)) if v and not np.isnan(v).any() else None
        p1[run] = {"times": v, "max_over_min": ratio,
                   "esito": None if ratio is None else ("confermata" if ratio <= 1.20 else "smentita")}
    P["P1"] = p1
    P["P2"] = {"threads_after_nhood": [c_["numba_threads_after"] for c_ in (mech or {}).get("calls", []) if c_["call"] == "sq.gr.nhood_enrichment"],
               "n_cpus": (mech or {}).get("n_cpus_requested"),
               "esito": None if mech is None else ("confermata" if mech.get("mechanism_confirmed") else "smentita")}
    P["P3"], P["P3b_spatial_neighbors"], P["P4"], P["P5"] = {}, {}, {}, {}
    for p, _ in PLATS:
        g = [sum(t(rec, s) for s in GSTEPS) for r, rec in sorted(data[("server_gpu", p)].items())]
        m1 = sum(march[("gpu", p, 1)][s] for s in GSTEPS)
        if g:
            e, lo, hi = boot_ratio(g, None, rng, den_const=m1)
            P["P3"][p] = {"new_sums": g, "march_r1": m1, "ratio": e, "ci": [lo, hi], "rel2sd_new": float(2 * np.std(g, ddof=1) / np.mean(g)),
                          "esito": verdict(lo, hi, 0.9, 1.1)}
        sn = vals("server_gpu", p, "spatial_neighbors")
        snm = float(np.mean([march[("gpu", p, r)]["spatial_neighbors"] for r in REPS]))
        if sn:
            e, lo, hi = boot_ratio(sn, None, rng, den_const=snm)
            P["P3b_spatial_neighbors"][p] = {"ratio": e, "ci": [lo, hi], "march_mean_1_5": snm, "esito": verdict(lo, hi, 0.9, 1.1)}
        sc_ = vals("server_cpu", p, "total")
        if sc_:
            e, lo, hi = boot_ratio(sc_, None, rng, den_const=march[("cpu", p, 1)]["total"])
            P["P4"][p] = {"ratio": e, "ci": [lo, hi], "march_r1_total": march[("cpu", p, 1)]["total"],
                          "rel2sd_new": float(2 * np.std(sc_, ddof=1) / np.mean(sc_)), "esito": verdict(lo, hi, 0.9, 1.1)}
        dc = vals("dgx_cpu", p, "total")
        if sc_ and dc:
            e, lo, hi = boot_ratio(sc_, dc, rng)
            P["P5"][p] = {"server_over_dgx_cpu_total": e, "ci": [lo, hi], "esito": verdict(lo, hi, 0.9, 1.1)}
    dc, gg = vals("dgx_cpu", "visium_hd_square_008um", "total"), vals("server_gpu", "visium_hd_square_008um", "total")
    if dc and gg:
        e, lo, hi = boot_ratio(dc, gg, rng)
        P["P6"] = {"speedup": e, "ci": [lo, hi], "esito": verdict(lo, hi, 5.75, 7.03)}

    # ---- provenance
    dl = (root / "scripts" / "download_spatial_data.py").read_text()
    prov = {k: (re.search(rf'{k}\s*=\s*\(?\s*((?:"[^"]*"\s*)+)', dl) or [None, None])[1] for k in
            ("VISIUM_SAMPLE", "VISIUM_BASE_URL", "VISIUM_HD_URL", "VISIUM_HD_ARCHIVE")}
    prov = {k: ("".join(re.findall(r'"([^"]*)"', v)) if v else None) for k, v in prov.items()}
    ev["provenance"] = prov
    any_rec = next(iter(data[("server_gpu", "visium")].values()), None)
    ev["sources"]["result_json_md5"] = {rec["path"]: rec["md5"] for v in data.values() for rec in v.values()}

    (root / "results_v2" / "s1_evaluation.json").write_text(json.dumps(ev, indent=2, default=str))

    # ---- markdown report
    L = ["# Rerun del benchmark spatial: report (step S1)", "",
         "Generato da `SPATIAL/scripts/s1_rerun_report.py` dai file di `SPATIAL/results_v2/`. Tutti i numeri sono in `s1_evaluation.json`, `s1_step_stats.csv` e `s1_speedups.csv`.", "",
         "## Esito dei controlli", ""]
    for gname in ("G1", "G2", "G3", "G4", "G5"):
        if gname in ev["gates"]:
            L.append(f"- {gname}: {'superato' if ev['gates'][gname]['pass'] else 'NON superato'}")
    L += ["", "## Previsioni", ""]
    for k, v in P.items():
        L.append(f"- {k}: `{json.dumps(v, default=lambda o: round(o, 4) if isinstance(o, float) else str(o))[:600]}`")
    for p, lab in PLATS:
        L += ["", f"## {lab}", "", "Tempi in secondi: media (SD) sulle ripetizioni 1-5 e 2-5.", "",
              "| step | " + " | ".join(f"{RUNS[r][2]} 1-5 | 2-5" for r in RUNS) + " |",
              "|---|" + "---|---|" * len(RUNS)]
        for s in ["total", "co_occurrence", "nhood_enrichment", "spatial_autocorr_moran", "spatial_autocorr_geary",
                  "spatial_neighbors", "pca", "leiden", "umap", "expression_neighbors", "ligrec"]:
            cells = []
            for r in RUNS:
                x = st[(st.run == r) & (st.platform == p) & (st.step == s)]
                if len(x) and not np.isnan(x.mean_1_5.iloc[0]):
                    cells += [f"{x.mean_1_5.iloc[0]:.2f} ({x.sd_1_5.iloc[0]:.2f})", f"{x.mean_2_5.iloc[0]:.2f} ({x.sd_2_5.iloc[0]:.2f})"]
                else:
                    cells += ["skipped", "skipped"]
            L.append(f"| {s} | " + " | ".join(cells) + " |")
        L += ["", "Speedup (media CPU / media GPU; intervallo bootstrap 95%):", "",
              "| step | riferimento DGX 1-5 | riferimento DGX 2-5 | controllo server 1-5 | controllo server 2-5 |", "|---|---|---|---|---|"]
        for s in ["total", "co_occurrence", "nhood_enrichment", "spatial_autocorr_moran", "spatial_autocorr_geary", "spatial_neighbors", "umap"]:
            cells = []
            for ref in ("reference_dgx", "control_server"):
                for conv in ("1_5", "2_5"):
                    x = spd[(spd.platform == p) & (spd.step == s) & (spd.cpu == ref) & (spd.convention == conv)] if len(spd) else spd
                    cells.append(f"{x.speedup.iloc[0]:.2f} [{x.ci_lo.iloc[0]:.2f}, {x.ci_hi.iloc[0]:.2f}]" if len(x) else "n/a")
            L.append(f"| {s} | " + " | ".join(cells) + " |")
        g = next((x for x in g5 if x["platform"] == p), {})
        L += ["", f"Gruppi usati negli step spaziali: {g.get('n_groups')} (etichette: ripetizione 1 CPU del DGX, md5 {g.get('labels_md5')}).",
              f"Thread numba all'inizio di ogni step CPU (ripetizione 1): " + "; ".join(
                  f"{x['run']}: " + ", ".join(f"{k}={v}" for k, v in x["profile"]) for x in g4 if x["platform"] == p and x["rep"] == 1)]
    L += ["", "## Provenienza dei dataset", "", *(f"- {k}: `{v}`" for k, v in prov.items()), ""]
    (root / "results_v2" / "RERUN_REPORT.md").write_text("\n".join(L) + "\n")
    print(json.dumps({g: ev["gates"][g]["pass"] for g in ev["gates"]}))


if __name__ == "__main__":
    main()
