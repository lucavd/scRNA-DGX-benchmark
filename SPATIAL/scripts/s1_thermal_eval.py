#!/usr/bin/env python3
"""Pre-registered thermal criterion of S1 (stdlib only).

thermal_samples.txt rows: unix_time Tctl_C mean_MHz load1, every 5 s.
Keep 128 threads if max Tctl <= 90 C and the mean frequency of the last
2 minutes is >= 95% of the mean of minutes 1-2. Exit 0 if kept, 10 otherwise.
"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
rows = [l.split() for l in (d / "thermal_samples.txt").read_text().splitlines() if l.strip()]
rows = [(float(a), float(b), float(c), float(e)) for a, b, c, e in rows]
t0 = rows[0][0]
log = (d / "thermal_load.log").read_text().splitlines()
batches = [l for l in log if l.startswith("batch ")]
# load window from the batch log: "batch <n> <unix_end> <seconds> threads=<k>"
bt = [(float(l.split()[2]), float(l.split()[3])) for l in batches]
start = bt[1][0] - bt[1][1] if len(bt) > 1 else bt[0][0] - bt[0][1]   # skip batch 1 (JIT compile)
end = bt[-1][0]
first = [r for r in rows if start + 60 <= r[0] < start + 120]
last = [r for r in rows if end - 120 <= r[0] < end]
mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
bfirst = [d for e, d in bt[1:] if start + 60 <= e < start + 120]
blast = [d for e, d in bt[1:] if end - 120 <= e <= end]
res = {
    "n_samples": len(rows), "n_batches": len(batches),
    "tctl_max": max(r[1] for r in rows),
    "freq_mean_min1_2_mhz": mean([r[2] for r in first]),
    "freq_mean_last2_mhz": mean([r[2] for r in last]),
}
res["freq_ratio_last_over_first"] = res["freq_mean_last2_mhz"] / res["freq_mean_min1_2_mhz"]
res["batch_time_ratio_last_over_first"] = mean(blast) / mean(bfirst)  # > 1 means slower (info only)
res["load_window_s"] = end - start
res["keep_128_threads"] = bool(res["tctl_max"] <= 90.0 and res["freq_ratio_last_over_first"] >= 0.95)
print(json.dumps(res, indent=2))
sys.exit(0 if res["keep_128_threads"] else 10)
