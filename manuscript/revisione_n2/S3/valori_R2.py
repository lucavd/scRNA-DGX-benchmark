#!/usr/bin/env python3
"""valori_R2.py - region R2 (Methods) receipts, step S3, LNBI chapter.
Stdlib only. Run from the repository root:  cd $REPO && python3 -B valori_R2.py
Prints ONLY a JSON object {ricevuta_id: value}. Read-only: opens files, never writes.
DGX evidence (sacct, SLURM logs) is read from $R2_EVIDENCE or results_v2/S3/R2_dgx_evidence/;
if that folder is absent, the same records are read live (read-only) from the DGX login node
over ssh (sacct and cat of the log files)."""
import glob, json, math, os, re, subprocess
EVDIR = os.environ.get("R2_EVIDENCE", "results_v2/S3/R2_dgx_evidence")
DGX = ["ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=20",
       "-i", os.path.expanduser("~/.ssh/id_ed25519_dgx"), "u0044@logindgx.hpc.ict.unipd.it"]
DGXLOGS = "/mnt/projects/dctv/dgx/u0044/sc-gpu-benchmark/logs"
_cache = {}
def J(p):
    if p not in _cache:
        with open(p) as f: _cache[p] = json.load(f)
    return _cache[p]
def rx(p, pat):
    with open(p) as f: return re.search(pat, f.read()).group(1)
def ext_rx(p, pat):
    try:
        with open(p) as f: return re.search(pat, f.read()).group(1)
    except Exception as e: return None
def docker_rx(p, pat):
    try:
        out = subprocess.run(["docker", "run", "--rm", "--entrypoint", "cat", "lucavd/sc-benchmark-spatial:latest", p],
                             capture_output=True, text=True, timeout=90).stdout
        return re.search(pat, out).group(1)
    except Exception: return None
def ev(name):
    p = os.path.join(EVDIR, name)
    if os.path.exists(p):
        with open(p, errors="replace") as f: return f.read()
    key = "ev:" + name
    if key not in _cache:
        if name.startswith("sacct_"):
            cmd = 'bash -lc "sacct -u u0044 -S 2026-02-01 -E 2026-11-04 -X --parsable2 --format=JobID,JobName%40,Partition,NodeList,AllocCPUS,AllocTRES%80,Start,End,Elapsed,State,ExitCode"'
        else:
            real = ("slurm-" + name.replace("_grep.txt", ".out")) if name.endswith("_grep.txt") else name
            cmd = "cat " + DGXLOGS + "/" + real
        _cache[key] = subprocess.run(DGX + [cmd], capture_output=True, text=True, timeout=60).stdout
    return _cache[key]
def rx_ev(name, pat): return re.search(pat, ev(name)).group(1)
def sacct_rows():
    lines = ev("sacct_u0044_2026-02-01_2026-11-04.txt").splitlines()
    hdr = lines[0].split("|")
    return [dict(zip(hdr, l.split("|"))) for l in lines[1:] if l.strip()]
def sacct_field(job, field):
    for r in sacct_rows():
        if r["JobID"] == job: return r[field]
def _cet(ts):  # sacct times are local CET (UTC+1) in March 2026
    from datetime import datetime, timedelta, timezone
    return datetime.fromisoformat(ts).replace(tzinfo=timezone(timedelta(hours=1)))
def _job_for(iso_utc):
    from datetime import datetime
    t = datetime.fromisoformat(iso_utc)
    out = []
    for r in sacct_rows():
        if r["Start"] in ("None", "Unknown") or r["End"] in ("None", "Unknown"): continue
        if _cet(r["Start"]) <= t <= _cet(r["End"]): out.append(r)
    return out
def stress_cpus():
    vals = set()
    for f in glob.glob("results/maxpower_[0-9]*_8gpu_results.json"):
        if J(f)["metadata"]["n_cells_input"] == 1700000: continue
        for r in _job_for(J(f)["metadata"]["timestamp"]): vals.add(r["AllocCPUS"])
    for r in sacct_rows():
        if r["JobName"] == "de_bench" and r["State"] == "COMPLETED": vals.add(r["AllocCPUS"])
    return ";".join(sorted(vals))
def stress_cpus_17():
    rs = _job_for(J("results/maxpower_1700000_8gpu_results.json")["metadata"]["timestamp"])
    return int(rs[0]["AllocCPUS"])
def oom_500k():
    err = ev("slurm-gpu_bench_1_16314.err"); out = ev("slurm-gpu_bench_1_16314.out")
    ok = ("rmm_cupy_allocator" in err and "Maximum pool size exceeded" in err
          and "ERROR: GPU benchmark failed for 500000 cells" in out)
    return 500000 if ok else None
def interval_mean():
    from datetime import datetime
    ts = [datetime.fromisoformat(J(f"results/gpu_10000_r{k}_results.json")["metadata"]["timestamp"]) for k in range(1, 6)]
    iv = [(ts[i + 1] - ts[i]).total_seconds() for i in range(4)]
    return sum(iv) / 4
def table2_rows():
    lines = open("manuscript/full_paper_LNBI.md", encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(": **Table 2.**"))
    rows = []
    for l in lines[i + 1:]:
        if l.startswith("|") and not l.startswith("|:") and not l.startswith("| Metric"):
            rows.append([c.strip() for c in l.strip("|").split("|")])
        elif rows and not l.startswith("|"): break
    return rows
def cpu10k_clusters():
    s = {tuple(J(f"results/cpu_10000_r{k}_results.json")["results_summary"][f"n_clusters_{x}"] for x in ("1.0", "1.5")) for k in range(1, 6)}
    return ";".join(map(str, list(s)[0])) if len(s) == 1 else None
def mp(n): return J(f"results/maxpower_{n}_8gpu_results.json")["metadata"]
def mpm(n): return J(f"results/maxpower_{n}_8gpu_results.json")["memory"]["detailed"]
def cov_files():
    return [f for f in glob.glob("results/maxpower_[0-9]*_8gpu_results.json")
            if J(f)["metadata"]["configuration"].get("pca_method") == "covariance_distributed"]
def h5_bytes(p, pat, chunk=1 << 24):
    with open(p, "rb") as f:
        prev = b""
        while True:
            b = f.read(chunk)
            if not b: return None
            m = re.search(pat, prev + b)
            if m: return m.group(1).decode()
            prev = b[-256:]
def aff():
    a = J("SPATIAL/results_v2/dgx_cpu/spatial_cpu_visium_r1_results.json")["metadata"]["system"]["affinity_cpus"]
    return a if isinstance(a, list) else json.loads(a)
def _ndistinct(cfg, n):
    fs = [f"results/{cfg}_{n}_r{k}_results.json" for k in range(1, 6)]
    if not all(os.path.exists(f) for f in fs): return None
    return max(len({J(f)["results_summary"][f"cluster_labels_hash_{x}"] for f in fs}) for x in ("0.5", "1.0", "1.5"))
def det_count(n, diff=False):
    vals = [v for v in (_ndistinct(c, n) for c in ("gpu", "gpu2", "gpu4", "gpu8")) if v is not None]
    hit = sum(1 for v in vals if (v > 1) == diff)
    return f"{hit}/{len(vals)}"
def cpu_det():
    vals = [_ndistinct("cpu", n) for n in (10000, 50000, 100000, 500000, 1300000)]
    return f"{sum(1 for v in vals if v == 1)}/{len(vals)}"

def knn_check(p):
    import zipfile, ast, struct
    z = zipfile.ZipFile(p); lens = set(); selfin = 0; n = 0
    for name in z.namelist():
        b = z.read(name)
        hl = struct.unpack("<H", b[8:10])[0] if b[6] == 1 else struct.unpack("<I", b[8:12])[0]
        off = 10 if b[6] == 1 else 12
        hdr = ast.literal_eval(b[off:off + hl].decode("latin1"))
        data = b[off + hl:]
        cnt = hdr["shape"][0]; size = int(hdr["descr"][-1]); fmt = {4: "i", 8: "q"}[size]
        vals = struct.unpack("<%d%s" % (cnt, fmt), data[:cnt * size])
        i = int(name.split("_")[1].split(".")[0]); n += 1; lens.add(cnt); selfin += int(i in vals)
    return ";".join(map(str, sorted(lens))) + ";" + f"{selfin}/{n}"
R = {}
try:
    R['R2-R001'] = rx('scripts/download_data.py',r'CENSUS_VERSION = "([^"]+)"')
except Exception as e:
    R['R2-R001'] = None
try:
    R['R2-R002'] = J('results/maxpower_limit_8gpu.json')['source_cells']
except Exception as e:
    R['R2-R002'] = None
try:
    R['R2-R003'] = J('results/cpu_1300000_r1_results.json')['metadata']['n_cells_input']
except Exception as e:
    R['R2-R003'] = None
try:
    R['R2-R004'] = int(rx('scripts/download_data.py',r'RANDOM_SEED = (\d+)'))
except Exception as e:
    R['R2-R004'] = None
try:
    R['R2-R005'] = ','.join(re.findall(r"10x 3\\\\' (v\d)",open('scripts/download_data.py').read()))
except Exception as e:
    R['R2-R005'] = None
try:
    R['R2-R006'] = J('results/cpu_50000_r1_results.json')['metadata']['n_cells_input']
except Exception as e:
    R['R2-R006'] = None
try:
    R['R2-R007'] = J('results/cpu_100000_r1_results.json')['metadata']['n_cells_input']
except Exception as e:
    R['R2-R007'] = None
try:
    R['R2-R008'] = J('results/cpu_500000_r1_results.json')['metadata']['n_cells_input']
except Exception as e:
    R['R2-R008'] = None
try:
    R['R2-R009'] = J('results/cpu_10000_r1_results.json')['metadata']['n_cells_input']
except Exception as e:
    R['R2-R009'] = None
try:
    R['R2-R010'] = int(rx('scripts/download_data.py',r'RANDOM_SEED = (\d+)'))
except Exception as e:
    R['R2-R010'] = None
try:
    R['R2-R011'] = len(eval(rx('scripts/benchmark_cpu.py',r'LEIDEN_RESOLUTIONS = (\[[^\]]*\])')))
except Exception as e:
    R['R2-R011'] = None
try:
    R['R2-R012'] = ext_rx('/tmp/lnbi_s2_p2_venv/lib/python3.12/site-packages/scanpy/neighbors/__init__.py',r'n_obs < (\d+)')
except Exception as e:
    R['R2-R012'] = None
try:
    R['R2-R013'] = ext_rx('/tmp/lnbi_s2_p2_venv/lib/python3.12/site-packages/scanpy/_settings/__init__.py',r'_n_jobs: ClassVar = (\d+)')
except Exception as e:
    R['R2-R013'] = None
try:
    R['R2-R014'] = int(rx('scripts/benchmark_cpu.py',r'n_iterations=(\d+)'))
except Exception as e:
    R['R2-R014'] = None
try:
    R['R2-R015'] = docker_rx('/opt/conda/lib/python3.12/site-packages/rapids_singlecell/tools/_clustering.py',r'n_iterations: int = (\d+)')
except Exception as e:
    R['R2-R015'] = None
try:
    R['R2-R016'] = int(J('results/cpu_10000_r1_results.json')['metadata']['configuration']['threading_vars']['OMP_NUM_THREADS'])
except Exception as e:
    R['R2-R016'] = None
try:
    R['R2-R017'] = ext_rx('/tmp/lnbi_s2_p2_venv/lib/python3.12/site-packages/scanpy/neighbors/__init__.py',r'n_obs < (\d+)')
except Exception as e:
    R['R2-R017'] = None
try:
    R['R2-R018'] = J('results/cpu_10000_r1_results.json')['metadata']['software_versions']['scanpy']
except Exception as e:
    R['R2-R018'] = None
try:
    R['R2-R019'] = J('results_v2/S2/neighbors_dgxdata/neighbors_eval.json')['per_size']['10000']['NP1_ratio_warm']
except Exception as e:
    R['R2-R019'] = None
try:
    R['R2-R020'] = J('results_v2/S2/neighbors_dgxdata/neighbors_eval.json')['per_size']['50000']['NP1_ratio_warm']
except Exception as e:
    R['R2-R020'] = None
try:
    R['R2-R021'] = J('results_v2/S2/neighbors_dgxdata/neighbors_eval.json')['per_size']['100000']['NP1_ratio_warm']
except Exception as e:
    R['R2-R021'] = None
try:
    R['R2-R022'] = J('results_v2/S2/neighbors_dgxdata/neighbors_eval.json')['runs']//6
except Exception as e:
    R['R2-R022'] = None
try:
    R['R2-R023'] = J('results_v2/S2/neighbors_dgxdata/neighbors_eval.json')['per_size']['10000']['calls_nj100'][0][0]
except Exception as e:
    R['R2-R023'] = None
try:
    R['R2-R024'] = int(J('results/gpu_10000_r1_results.json')['metadata']['configuration']['rmm_pool']['initial_pool'].split('%')[0])
except Exception as e:
    R['R2-R024'] = None
try:
    R['R2-R025'] = int(J('results/gpu_10000_r1_results.json')['metadata']['configuration']['rmm_pool']['maximum_pool'].split('%')[0])
except Exception as e:
    R['R2-R025'] = None
try:
    R['R2-R026'] = oom_500k()
except Exception as e:
    R['R2-R026'] = None
try:
    R['R2-R027'] = int(rx('scripts/benchmark_gpu.py',r'cp.random.random\(\((\d+), \d+\)'))
except Exception as e:
    R['R2-R027'] = None
try:
    R['R2-R028'] = interval_mean()
except Exception as e:
    R['R2-R028'] = None
try:
    R['R2-R029'] = sum(J(f'results/gpu_10000_r{k}_results.json')['timings']['total'] for k in range(2,6))/4
except Exception as e:
    R['R2-R029'] = None
try:
    R['R2-R030'] = '2-5'
except Exception as e:
    R['R2-R030'] = None
try:
    R['R2-R031'] = ','.join(str(J(f'results/gpu{g}_10000_r1_results.json')['metadata']['configuration']['dask_cluster']['n_workers']) for g in (2,4,8))
except Exception as e:
    R['R2-R031'] = None
try:
    R['R2-R032'] = J('results/gpu8_1300000_r1_results.json')['metadata']['configuration']['dask_cluster']['rmm_pool_size']
except Exception as e:
    R['R2-R032'] = None
try:
    R['R2-R033'] = J('results/gpu8_1300000_r1_results.json')['metadata']['configuration']['dask_cluster']['rmm_maximum_pool_size']
except Exception as e:
    R['R2-R033'] = None
try:
    R['R2-R034'] = J('results/gpu8_1300000_r1_results.json')['metadata']['software_versions']['rapids_singlecell']
except Exception as e:
    R['R2-R034'] = None
try:
    R['R2-R035'] = ';'.join(re.findall(r'ERROR: GPU benchmark failed for (\d+) cells',ev('slurm-gpu_bench_1_16314.out')))
except Exception as e:
    R['R2-R035'] = None
try:
    R['R2-R036'] = len(table2_rows())
except Exception as e:
    R['R2-R036'] = None
try:
    R['R2-R037'] = len(set(x[-1] for x in table2_rows()))
except Exception as e:
    R['R2-R037'] = None
try:
    R['R2-R038'] = sum(1 for x in table2_rows() if x[-1]=='Clustering')
except Exception as e:
    R['R2-R038'] = None
try:
    R['R2-R039'] = J('results/concordance_10000_r1.json')['metadata']['n_cells']
except Exception as e:
    R['R2-R039'] = None
try:
    R['R2-R040'] = J('results/concordance_10000_r1.json')['metadata']['cpu_timestamp'][:10]
except Exception as e:
    R['R2-R040'] = None
try:
    R['R2-R041'] = sacct_field('16139','AllocCPUS')
except Exception as e:
    R['R2-R041'] = None
try:
    R['R2-R042'] = re.search(r'gres/gpu=(\d+)',sacct_field('16139','AllocTRES')).group(1)
except Exception as e:
    R['R2-R042'] = None
try:
    R['R2-R043'] = ';'.join(str(J('results/concordance_10000_r1.json')['cluster_concordance'][f'leiden_{x}']['n_clusters_cpu']) for x in ('1.0','1.5'))
except Exception as e:
    R['R2-R043'] = None
try:
    R['R2-R044'] = cpu10k_clusters()
except Exception as e:
    R['R2-R044'] = None
try:
    R['R2-R045'] = int(rx('scripts/compare_results.py',r'cpu_g.head\((\d+)\)'))
except Exception as e:
    R['R2-R045'] = None
try:
    R['R2-R046'] = rx('scripts/compare_results.py',r'data\["gpu"\]\["clusters"\], "leiden_([0-9.]+)"')
except Exception as e:
    R['R2-R046'] = None
try:
    R['R2-R047'] = J('results/maxpower_3436470_8gpu_results.json')['metadata']['n_cells_source_file']
except Exception as e:
    R['R2-R047'] = None
try:
    R['R2-R048'] = J('results/maxpower_1700000_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R048'] = None
try:
    R['R2-R049'] = J('results/maxpower_3400000_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R049'] = None
try:
    R['R2-R050'] = int(rx('scripts/benchmark_maxpower.py',r'RANDOM_SEED = (\d+)'))
except Exception as e:
    R['R2-R050'] = None
try:
    R['R2-R051'] = J('results/maxpower_6872940_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R051'] = None
try:
    R['R2-R052'] = mp(6872940)['n_cells_input']/mp(6872940)['n_cells_source_file']
except Exception as e:
    R['R2-R052'] = None
try:
    R['R2-R053'] = J('results/maxpower_10309410_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R053'] = None
try:
    R['R2-R054'] = mp(10309410)['n_cells_input']/mp(10309410)['n_cells_source_file']
except Exception as e:
    R['R2-R054'] = None
try:
    R['R2-R055'] = J('results/maxpower_11900000_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R055'] = None
try:
    R['R2-R056'] = mp(11900000)['n_cells_input']-3*mp(11900000)['n_cells_source_file']
except Exception as e:
    R['R2-R056'] = None
try:
    R['R2-R057'] = J('results/maxpower_3436470_8gpu_results.json')['results_summary']['n_genes_after_qc']
except Exception as e:
    R['R2-R057'] = None
try:
    R['R2-R058'] = J('results/maxpower_6872940_8gpu_results.json')['results_summary']['n_genes_after_qc']
except Exception as e:
    R['R2-R058'] = None
try:
    R['R2-R059'] = J('results/maxpower_10309410_8gpu_results.json')['results_summary']['n_genes_after_qc']
except Exception as e:
    R['R2-R059'] = None
try:
    R['R2-R060'] = J('results/maxpower_3436470_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R060'] = None
try:
    R['R2-R061'] = J('results/maxpower_6872940_8gpu_results.json')['metadata']['n_cells_input']/1e6
except Exception as e:
    R['R2-R061'] = None
try:
    R['R2-R062'] = len({J(f)['results_summary']['n_genes_after_qc'] for f in glob.glob('results/maxpower_*_8gpu_results.json') if J(f)['metadata'].get('n_cells_input') and J(f)['metadata']['n_cells_input']>=10309410})
except Exception as e:
    R['R2-R062'] = None
try:
    R['R2-R063'] = ';'.join(str(x) for x in sorted(J(f)['metadata']['n_cells_input'] for f in glob.glob('results/maxpower_*_8gpu_results.json') if J(f)['metadata']['configuration'].get('clustering_algorithm')=='kmeans'))
except Exception as e:
    R['R2-R063'] = None
try:
    R['R2-R064'] = ';'.join(sorted({','.join(str(J(f'results/maxpower_{n}_8gpu_results.json')['results_summary'][f'n_clusters_{x}']) for x in ('0.5','1.0','1.5')) for n in (3436470,6872940,10309410)}))
except Exception as e:
    R['R2-R064'] = None
try:
    R['R2-R065'] = ';'.join(str(x) for x in sorted(J(f)['metadata']['n_cells_input'] for f in glob.glob('results/maxpower_[0-9]*_8gpu_results.json') if J(f)['timings'].get('de_testing',0)>0))
except Exception as e:
    R['R2-R065'] = None
try:
    R['R2-R066'] = J('results/maxpower_11900000_8gpu_results.json')['results_summary']['n_hvgs']
except Exception as e:
    R['R2-R066'] = None
try:
    R['R2-R067'] = ';'.join(sorted({J(f)['metadata']['configuration']['dask_cluster']['rmm_pool_size'] for f in cov_files()}))
except Exception as e:
    R['R2-R067'] = None
try:
    R['R2-R068'] = J('results/maxpower_11900000_8gpu_results.json')['metadata']['n_gpus']
except Exception as e:
    R['R2-R068'] = None
try:
    R['R2-R069'] = len(cov_files())
except Exception as e:
    R['R2-R069'] = None
try:
    R['R2-R070'] = min(J(f)['metadata']['n_cells_input'] for f in cov_files())/1e6
except Exception as e:
    R['R2-R070'] = None
try:
    R['R2-R071'] = max(J(f)['metadata']['n_cells_input'] for f in cov_files())/1e6
except Exception as e:
    R['R2-R071'] = None
try:
    R['R2-R072'] = J('results/maxpower_limit_8gpu.json')['first_oom_at']/1e6
except Exception as e:
    R['R2-R072'] = None
try:
    R['R2-R073'] = int(re.search(r'target=(13,[0-9,]+) cells',ev('slurm-maxpower_8gpu_16662.out')).group(1).replace(',',''))/1e6
except Exception as e:
    R['R2-R073'] = None
try:
    R['R2-R074'] = int(re.search(r'3,436,470 × (\d+) \+ 0 = 13,745,880',ev('slurm-maxpower_8gpu_16662.out')).group(1))
except Exception as e:
    R['R2-R074'] = None
try:
    R['R2-R075'] = J('results/maxpower_limit_8gpu.json')['source_cells']
except Exception as e:
    R['R2-R075'] = None
try:
    R['R2-R076'] = mpm(11900000)['qc_filtering_ram_before_gb']-mpm(11900000)['data_loading_ram_after_gb']
except Exception as e:
    R['R2-R076'] = None
try:
    R['R2-R077'] = J('results/maxpower_11900000_8gpu_results.json')['metadata']['n_gpus']
except Exception as e:
    R['R2-R077'] = None
try:
    R['R2-R078'] = rx('scripts/benchmark_maxpower.py',r'rss / \((1024\*\*3)\)')
except Exception as e:
    R['R2-R078'] = None
try:
    R['R2-R079'] = int(rx('slurm/de_benchmark.sh',r'TARGET_CELLS=(\d+)'))
except Exception as e:
    R['R2-R079'] = None
try:
    R['R2-R080'] = int(rx('scripts/test_de_benchmark.py',r'RANDOM_SEED = (\d+)'))
except Exception as e:
    R['R2-R080'] = None
try:
    R['R2-R081'] = J('results/de_benchmark_pseudobulk.json')['n_cells']
except Exception as e:
    R['R2-R081'] = None
try:
    R['R2-R082'] = J('results/de_benchmark_pseudobulk.json')['n_genes_raw']
except Exception as e:
    R['R2-R082'] = None
try:
    R['R2-R083'] = len({k for f in glob.glob('results/de_benchmark_*.json') for k,v in J(f)['results'].items() if v.get('time',-1)>0 and k!='ttest_scatter_clean'})
except Exception as e:
    R['R2-R083'] = None
try:
    R['R2-R084'] = J('results/de_benchmark_wilcoxon_scatter.json')['n_gpus']
except Exception as e:
    R['R2-R084'] = None
try:
    R['R2-R085'] = J('results/de_benchmark_pseudobulk.json')['results']['pseudobulk']['n_donors']
except Exception as e:
    R['R2-R085'] = None
try:
    R['R2-R086'] = int(rx('scripts/test_de_benchmark.py',r'n_cells_group < (\d+)'))
except Exception as e:
    R['R2-R086'] = None
try:
    R['R2-R087'] = J('results/de_benchmark_pseudobulk.json')['results']['pseudobulk']['n_pseudobulk_samples']
except Exception as e:
    R['R2-R087'] = None
try:
    R['R2-R088'] = J('results/de_benchmark_pseudobulk.json')['results']['pseudobulk']['n_clusters']
except Exception as e:
    R['R2-R088'] = None
try:
    R['R2-R089'] = h5_bytes('SPATIAL/data/visium_hd/binned_outputs/square_008um/filtered_feature_bc_matrix.h5',rb'spaceranger-(\d+\.\d+\.\d+)')
except Exception as e:
    R['R2-R089'] = None
try:
    R['R2-R090'] = h5_bytes('SPATIAL/data/visium_hd/binned_outputs/square_002um/raw_probe_bc_matrix.h5',rb'Visium Mouse Transcriptome Probe Set (v\d\.\d)')
except Exception as e:
    R['R2-R090'] = None
try:
    R['R2-R091'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_008um_r1_results.json')['metadata']['n_spots_input']
except Exception as e:
    R['R2-R091'] = None
try:
    R['R2-R092'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_002um_r1_results.json')['metadata']['n_spots_input']
except Exception as e:
    R['R2-R092'] = None
try:
    R['R2-R093'] = int(rx('SPATIAL/run_all_benchmarks.sh',r'--max-spots (\d+)'))
except Exception as e:
    R['R2-R093'] = None
try:
    R['R2-R094'] = int(rx('SPATIAL/scripts/benchmark_spatial_gpu.py',r'RANDOM_SEED = (\d+)'))
except Exception as e:
    R['R2-R094'] = None
try:
    R['R2-R095'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_002um_r1_results.json')['results_summary']['n_spots_after_qc']
except Exception as e:
    R['R2-R095'] = None
try:
    R['R2-R096'] = 100*400000/J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_002um_r1_results.json')['metadata']['n_spots_input']
except Exception as e:
    R['R2-R096'] = None
try:
    R['R2-R097'] = 2/math.sqrt(400000/J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_002um_r1_results.json')['metadata']['n_spots_input'])
except Exception as e:
    R['R2-R097'] = None
try:
    R['R2-R098'] = int(rx('SPATIAL/scripts/benchmark_spatial_cpu.py',r'if n_groups <= (\d+)'))
except Exception as e:
    R['R2-R098'] = None
try:
    R['R2-R099'] = int(rx('SPATIAL/scripts/benchmark_spatial_cpu.py',r'if n_after_qc <= ([0-9_]+) and').replace('_',''))
except Exception as e:
    R['R2-R099'] = None
try:
    R['R2-R100'] = float(rx('SPATIAL/scripts/benchmark_spatial_cpu.py',r'leiden_res = ([0-9.]+)\n'))
except Exception as e:
    R['R2-R100'] = None
try:
    R['R2-R101'] = ';'.join(str(x) for x in sorted({rec[m]['n_common_genes'] for f in glob.glob('SPATIAL/results_v2/concordance_reference/*.json') for rec in J(f) for m in ('moranI','gearyC')}))
except Exception as e:
    R['R2-R101'] = None
try:
    R['R2-R102'] = J('results/gpu8_1300000_r1_results.json')['metadata']['n_cpus']
except Exception as e:
    R['R2-R102'] = None
try:
    R['R2-R103'] = J('SPATIAL/results_v2/dgx_cpu/spatial_cpu_visium_r1_results.json')['metadata']['system']['cpu_model']
except Exception as e:
    R['R2-R103'] = None
try:
    R['R2-R104'] = J('results/gpu_10000_r1_results.json')['metadata']['gpu_info']['driver_version']
except Exception as e:
    R['R2-R104'] = None
try:
    R['R2-R105'] = J('results/gpu8_1300000_r1_results.json')['metadata']['gpu_info']['driver_version']
except Exception as e:
    R['R2-R105'] = None
try:
    R['R2-R106'] = ';'.join(sacct_field(j,'AllocCPUS') for j in ('16314','16315','16316'))
except Exception as e:
    R['R2-R106'] = None
try:
    R['R2-R107'] = int(sacct_field('16317','AllocCPUS'))
except Exception as e:
    R['R2-R107'] = None
try:
    R['R2-R108'] = J('results/cpu_10000_r1_results.json')['metadata']['n_cpus']
except Exception as e:
    R['R2-R108'] = None
try:
    R['R2-R109'] = ';'.join(sacct_field(j,'NodeList') for j in ('16314','16315','16316','16317','16161'))
except Exception as e:
    R['R2-R109'] = None
try:
    R['R2-R110'] = stress_cpus()
except Exception as e:
    R['R2-R110'] = None
try:
    R['R2-R111'] = stress_cpus_17()
except Exception as e:
    R['R2-R111'] = None
try:
    R['R2-R112'] = int(re.search(r'(\d+)-Cores',J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['system']['cpu_model']).group(1))
except Exception as e:
    R['R2-R112'] = None
try:
    R['R2-R113'] = int(J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['system']['os_cpu_count'])
except Exception as e:
    R['R2-R113'] = None
try:
    R['R2-R114'] = int(J('SPATIAL/results_v2/dgx_cpu/spatial_cpu_visium_r1_results.json')['metadata']['system']['affinity_n_cpus'])
except Exception as e:
    R['R2-R114'] = None
try:
    R['R2-R115'] = sum(1 for x in aff() if int(x)<112)
except Exception as e:
    R['R2-R115'] = None
try:
    R['R2-R116'] = J('SPATIAL/results/spatial_gpu_visium_r1_results.json')['metadata']['gpu_info']['driver_version']
except Exception as e:
    R['R2-R116'] = None
try:
    R['R2-R117'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['gpu_info']['driver_version']
except Exception as e:
    R['R2-R117'] = None
try:
    R['R2-R118'] = min(v['ratio'] for v in J('SPATIAL/results_v2/s1_evaluation.json')['predictions']['P3'].values())
except Exception as e:
    R['R2-R118'] = None
try:
    R['R2-R119'] = max(v['ratio'] for v in J('SPATIAL/results_v2/s1_evaluation.json')['predictions']['P3'].values())
except Exception as e:
    R['R2-R119'] = None
try:
    R['R2-R120'] = J('results/gpu8_1300000_r1_results.json')['metadata']['gpu_info']['driver_version']
except Exception as e:
    R['R2-R120'] = None
try:
    R['R2-R121'] = rx_ev('slurm-spatial_smoke_16951.out',r'Container:\s+\S*sc-benchmark-(\d+)\.sif')
except Exception as e:
    R['R2-R121'] = None
try:
    R['R2-R122'] = len(glob.glob('results/cpu_10000_r[0-9]_results.json'))
except Exception as e:
    R['R2-R122'] = None
try:
    R['R2-R123'] = J('results/cpu_10000_r1_results.json')['timings']['neighbors']
except Exception as e:
    R['R2-R123'] = None
try:
    R['R2-R124'] = sum(J(f'results/cpu_10000_r{k}_results.json')['timings']['neighbors'] for k in range(2,6))/4
except Exception as e:
    R['R2-R124'] = None
try:
    R['R2-R125'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['software_versions']['squidpy']
except Exception as e:
    R['R2-R125'] = None
try:
    R['R2-R126'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['steps_runtime']['ligrec']['start']['numba_num_threads']
except Exception as e:
    R['R2-R126'] = None
try:
    R['R2-R127'] = J('SPATIAL/results_v2/server_gpu/spatial_gpu_visium_r1_results.json')['metadata']['system']['image_id']
except Exception as e:
    R['R2-R127'] = None
try:
    R['R2-R128'] = J('results/gpu_10000_r1_results.json')['metadata']['software_versions']['scanpy']
except Exception as e:
    R['R2-R128'] = None
try:
    R['R2-R129'] = J('results/gpu_10000_r1_results.json')['metadata']['software_versions']['rapids_singlecell']
except Exception as e:
    R['R2-R129'] = None
try:
    R['R2-R130'] = J('results/gpu_10000_r1_results.json')['metadata']['software_versions']['cupy']
except Exception as e:
    R['R2-R130'] = None
try:
    R['R2-R131'] = J('results/gpu_10000_r1_results.json')['metadata']['software_versions']['rmm']
except Exception as e:
    R['R2-R131'] = None
try:
    R['R2-R132'] = J('results/gpu_10000_r1_results.json')['metadata']['software_versions']['numpy']
except Exception as e:
    R['R2-R132'] = None
try:
    R['R2-R133'] = J('results/cpu_10000_r1_results.json')['metadata']['software_versions']['igraph']
except Exception as e:
    R['R2-R133'] = None
try:
    R['R2-R134'] = det_count(10000)
except Exception as e:
    R['R2-R134'] = None
try:
    R['R2-R135'] = ';'.join(det_count(n,diff=True) for n in (100000,500000,1300000))
except Exception as e:
    R['R2-R135'] = None
try:
    R['R2-R136'] = det_count(50000,diff=True)
except Exception as e:
    R['R2-R136'] = None
try:
    R['R2-R137'] = cpu_det()
except Exception as e:
    R['R2-R137'] = None
try:
    R['R2-R138'] = knn_check('results/cpu_10000_r1_knn.npz')
except Exception as e:
    R['R2-R138'] = None
try:
    R['R2-R139'] = knn_check('results/gpu_10000_r1_knn.npz')
except Exception as e:
    R['R2-R139'] = None
try:
    R['R2-R140'] = int(rx('scripts/benchmark_maxpower_chunked.py',r'CELL_BATCH_SIZE = ([0-9_]+)').replace('_',''))
except Exception as e:
    R['R2-R140'] = None
try:
    R['R2-R141'] = J('results/maxpower_chunked_12000000_8gpu_results.json')['metadata']['configuration']['cell_batch_size']
except Exception as e:
    R['R2-R141'] = None
try:
    R['R2-R142'] = str(ev('slurm-maxpower_8gpu_16531.out').count('trying 12,000,000 cells'))+';'+str('TimeoutError' in ev('slurm-maxpower_8gpu_16531.err'))
except Exception as e:
    R['R2-R142'] = None
try:
    R['R2-R143'] = float(re.search(r'failed to allocate ([0-9.]+) GiB',ev('slurm-gpu_bench_1_16314.err')).group(1))
except Exception as e:
    R['R2-R143'] = None
try:
    R['R2-R144'] = 'ALL PASS' in ev('test_driver_16944_grep.txt')
except Exception as e:
    R['R2-R144'] = None
print(json.dumps(R, indent=1, default=str))
