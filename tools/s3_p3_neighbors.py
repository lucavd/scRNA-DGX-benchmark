#!/usr/bin/env python3
"""S3, prediction P3: neighbour speedup against a 100-thread CPU (pre-registered in docs/steps/S3.md).

Estimator (pre-registered): speedup_1gpu(mean r1-5 CPU / mean r1-5 GPU) / NP1, where
NP1 = mean warm time n_jobs=1 / mean warm time n_jobs=100 (S2 measurement on the DGX data).
Sensitivity (declared, not pre-registered): CPU repeat 1 kept as is (compilation does not
depend on threads), repeats 2-5 divided by NP1.
95% percentile bootstrap, B = 2000, seed 20261104, resampling the 5 repeats of each of
CPU, GPU, n_jobs=1 and n_jobs=100 independently. Standard library only.
"""
import json, hashlib, random, statistics as st, os, sys
REPO = os.environ.get("REPO", ".")
SIZES = [10000, 50000, 100000]
B, SEED = 2000, 20261104
def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
inputs = {}
def load(p):
    full = os.path.join(REPO, p); inputs[p] = md5(full)
    return json.load(open(full))
def q(xs, a):
    xs = sorted(xs); k = (len(xs) - 1) * a; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
rng = random.Random(SEED)
out = {"estimator": "speedup_1gpu_r1_5 / NP1", "B": B, "seed": SEED, "sizes": {}}
for n in SIZES:
    cpu = [load(f"results/cpu_{n}_r{k}_results.json")["timings"]["neighbors"] for k in range(1, 6)]
    gpu = [load(f"results/gpu_{n}_r{k}_results.json")["timings"]["neighbors"] for k in range(1, 6)]
    nj1 = [load(f"results_v2/S2/neighbors_dgxdata/nb_{n}_nj1_r{k}.json")["warm"]["seconds"] for k in range(1, 6)]
    nj100 = [load(f"results_v2/S2/neighbors_dgxdata/nb_{n}_nj100_r{k}.json")["warm"]["seconds"] for k in range(1, 6)]
    def est(c, g, a, b):
        np1 = st.mean(a) / st.mean(b)
        s = st.mean(c) / st.mean(g)
        sens = st.mean([c[0]] + [x / np1 for x in c[1:]]) / st.mean(g)
        return s, np1, s / np1, sens
    s, np1, adj, sens = est(cpu, gpu, nj1, nj100)
    bs_adj, bs_sens, bs_s = [], [], []
    for _ in range(B):
        r = lambda v: [v[rng.randrange(5)] for _ in range(5)]
        c, g, a, b = r(cpu), r(gpu), r(nj1), r(nj100)
        # sensitivity needs repeat identity: resample repeats 2-5 within themselves, keep r1
        cs = [cpu[0]] + [cpu[1:][rng.randrange(4)] for _ in range(4)]
        e = est(c, g, a, b); bs_adj.append(e[2]); bs_s.append(e[0])
        np1b = st.mean(a) / st.mean(b)
        bs_sens.append(st.mean([cs[0]] + [x / np1b for x in cs[1:]]) / st.mean(g))
    out["sizes"][str(n)] = {
        "cpu_neighbors_s": cpu, "gpu_neighbors_s": gpu, "warm_nj1_s": nj1, "warm_nj100_s": nj100,
        "speedup_1gpu_r1_5": s, "speedup_1gpu_ci95": [q(bs_s, .025), q(bs_s, .975)],
        "NP1": np1, "adjusted": adj, "adjusted_ci95": [q(bs_adj, .025), q(bs_adj, .975)],
        "sensitivity_r1_unadjusted": sens, "sensitivity_ci95": [q(bs_sens, .025), q(bs_sens, .975)],
    }
out["inputs_md5"] = inputs
json.dump(out, open(os.path.join(REPO, "results_v2/S3/p3_neighbors.json"), "w"), indent=1)
for n, v in out["sizes"].items():
    print(n, "1gpu %.1f [%.1f; %.1f]" % (v["speedup_1gpu_r1_5"], *v["speedup_1gpu_ci95"]),
          "NP1 %.3f" % v["NP1"], "adj %.1f [%.1f; %.1f]" % (v["adjusted"], *v["adjusted_ci95"]),
          "sens %.1f [%.1f; %.1f]" % (v["sensitivity_r1_unadjusted"], *v["sensitivity_ci95"]))
