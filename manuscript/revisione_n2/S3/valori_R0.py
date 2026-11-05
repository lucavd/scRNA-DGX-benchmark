#!/usr/bin/env python3
"""valori_R0.py (S3, agente principale): rilegge dai file di prova nel repo le 13 ricevute della regione R4
che puntavano a fonti fuori dal repo (log SLURM del DGX, Crossref, pagina CONVECS, pacchetto della revisione).
Uso: cd $REPO && python3 -B manuscript/revisione_n2/S3/valori_R0.py -> JSON {ricevuta_id: valore}. Solo libreria standard.
"""
import glob, json, re, zipfile
EV = "results_v2/S3/evidence"
def rd(p): return open(p, encoding="utf-8", errors="replace").read()
out = {}
n_rep = len(glob.glob("results/gpu_10000_r*_results.json"))
out["R4-V045"] = "repeats 2-%d" % n_rep
t = rd(f"{EV}/slurm-maxpower_8gpu_16463.out")
last = re.findall(r"Trying ([\d,]+) cells", t)[-1]
out["R4-V092"] = "%.1f" % (int(last.replace(",", "")) / 1e6)
out["R4-V093"] = "%.1f" % (int(re.search(r"FAILED at (\d+) cells \(exit 137\)", rd(f"{EV}/slurm-chunked_single_16825.out")).group(1)) / 1e6)
codes = {re.search(r"exit code -(\d+) for target=13,745,880", rd(f"{EV}/slurm-maxpower_8gpu_{j}.err.tail25")).group(1) for j in (16463, 16662)}
out["R4-V094"] = "signal %s" % "/".join(sorted(codes))
cr = json.load(open(f"{EV}/crossref_R4.json"))
pg = lambda d: cr[d]["page"].replace("-", "--")
out["R4-X01"] = pg("10.1145/3731599.3767378")
out["R4-X02"] = "{%s}" % cr["10.1038/s41592-021-01358-2"]["issue"]
out["R4-X03"] = pg("10.1038/s41592-019-0619-0")
out["R4-X04"] = pg("10.1038/s41592-018-0229-2")
out["R4-X05"] = "{%s}" % cr["10.1186/s13059-014-0550-8"]["article-number"]
out["R4-X06"] = pg("10.1093/bioinformatics/btp616")
ack = rd(f"{EV}/convecs_ack.txt")
out["R4-X07"] = re.search(r"FESR (\d{4}-\d{4})", ack).group(1)
out["R4-X08"] = re.search(r"Action (\d+\.\d+\.\d+)", ack).group(1)
w = zipfile.ZipFile("manuscript/revisione_n2/script_e_calcoli.zip").read("tracks/E_work/web_evidence_part2.txt").decode("utf-8", "replace")
y, mth, dd = re.search(r"(20\d\d)-(\d\d)-(\d\d)", w).groups()
MON = ["January","February","March","April","May","June","July","August","September","October","November","December"]
out["R4-X09"] = "%d %s %s" % (int(dd), MON[int(mth) - 1], y)
sig = rd(f"{EV}/rsc_0.14.1_tl_leiden_signature.txt")
assert "rapids_singlecell 0.14.1" in sig
out["R4-V075"] = "up to %s" % re.search(r"n_iterations: 'int' = (\d+)", sig).group(1)
print(json.dumps(out, ensure_ascii=False))
