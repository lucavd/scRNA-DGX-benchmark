#!/usr/bin/env python3
"""S7: mutation test of tools/s7_check.py. Four deliberate errors are injected into a copy of the
chapter .tex (a changed number, an ASCII "8 um", a swapped citation, a swapped figure file); the
check must fail on each. Usage: python3 -B tools/s7_check_mutations.py"""
import importlib.util, os, json
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("c", os.path.join(REPO, "tools/s7_check.py")); c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
L = os.path.join(REPO, "manuscript/lncs_latex/full_paper_LNBI.tex"); A = os.path.join(REPO, "results_v2/S7/build/chapter/full_paper_LNBI.aux"); M = os.path.join(REPO, "manuscript/full_paper_LNBI.md")
t = open(L).read()
muts = {"number": t.replace("52,056.2", "52,065.2", 1), "ascii_um": t.replace("8~\\textmu{}m", "8 um", 1),
        "cite": t.replace("\\cite{Heumos2023}", "\\cite{Wolf2018}", 1), "figure": t.replace("figures/fig2.pdf", "figures/fig3.pdf", 1)}
out = {}
for k, v in muts.items():
    assert v != t, k
    open("/tmp/s7_mut.tex", "w").write(v); r = c.compare(M, "/tmp/s7_mut.tex", A)
    out[k] = {"check_failed": not r["pass"], "number_diffs": len(r["number_diffs"]), "cite_sequence_equal": r["cite_sequence_equal"],
              "residual_ascii": r["residual_ascii"], "figure_mismatches": r["figure_mismatches"]}
out["all_detected"] = all(v["check_failed"] for v in out.values() if isinstance(v, dict))
json.dump(out, open(os.path.join(REPO, "results_v2/S7/s7_check_mutations.json"), "w"), indent=1)
print(json.dumps(out))
