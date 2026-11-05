#!/usr/bin/env python3
"""S7 gate G4 (second part): a provenance for every number of the final chapter and supplement.

Each number token of manuscript/full_paper_LNBI.md and manuscript/supplementary_LNBI.md
(same tokeniser as tools/s7_check.py, References excluded) gets the first class
that applies:
  receipt     the token is a value written with a receipt in step S3
              (manuscript/revisione_n2/S3/ricevute_R*.csv, valore_scritto), re-read
              from the JSON by valori_R*.py (rerun in S7)
  figure      it equals, at its decimals (or as a percentage), a value recomputed from
              the raw JSON by tools/s4_check.py or tools/s5_check.py
              (results_v2/S4/figure_values.csv, results_v2/S5/figure_values.csv,
              results_v2/S5/s5_numbers.json) or a value of the step S1 spatial outputs
              (SPATIAL/results_v2: s1_step_stats.csv, s1_speedups.csv, top-level,
              concordance_reference and cooc_check JSON); tokens with at least 3
              significant digits or 2 decimals; shorter tokens are counted as
              "figure (short token)", a weaker match reported separately
  review      it occurs in the claimed value of a PASS row of the review n.2 log
              (manuscript/revisione_n2/revisione_n2_log.csv), whose value was
              recomputed from the data in the review
  structural  not a measured quantity: year, date, version, identifier, seed,
              pipeline parameter, figure/table/section number, count of items
              named in the sentence; the rule that applied is recorded
  manual      listed in results_v2/S7/provenance_manual.csv with file and value
Tokens with no class are reported as unresolved.

Usage: python3 -B tools/s7_provenance.py --out results_v2/S7/provenance.json
"""
import argparse, csv, glob, json, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r"(?<![A-Za-z0-9_.\-])\d[\d,]*(?:\.\d+)?")


def plain(md):
    body = re.sub(r"(?s)^---\n.*?\n---\n", "", md, count=1).split("\n# References")[0]
    body = re.sub(r"\[[^\[\]]*@[^\[\]]*\]", " ", body)
    body = re.sub(r"\]\([^)]*\)", "]", body)
    body = re.sub(r"\^[0-9,]+\^", " ", body)
    body = re.sub(r"`[^`]*`", " ", body)
    body = re.sub(r"<https?://[^>]*>|https?://\S+", " ", body)
    body = re.sub(r"(?m)^\|[-|: ]+\|\s*$", " ", body)
    return body.replace("&nbsp;", " ")


def tokens(md):
    out = []
    for ln in plain(md).split("\n"):
        for m in NUM.finditer(ln):
            t = m.group(0).rstrip(",")
            out.append((t, ln, m.start()))
    return out


def val(t):
    return float(t.replace(",", ""))


def dec(t):
    return len(t.split(".")[1]) if "." in t else 0


def sig(t):
    return len(t.replace(",", "").replace(".", "").lstrip("0"))


STRUCT = [
    ("figure/table/section number", re.compile(r"(?:Table|Tables|Fig\.|Figure|Figures|Section|S)\s*$")),
    ("figure/table range end", re.compile(r"(?:Tables?|Figures?|Fig\.)\s+S?\d+\s*(?:-|and|,)\s*S?$")),
    ("date or year", None),
    ("version", None),
    ("identifier or grant code", re.compile(r"(?:CUP|code|PNC|D\.D\.|job|jobs|node|poddgx|SID|BIRD|seed|seeds|seed =)\s*:?\s*$", re.I)),
]
VERSION_CTX = re.compile(r"(?:Scanpy|scanpy|Squidpy|rapids-singlecell|RAPIDS|CuPy|RMM|cuGraph|cuML|Dask|Dask-CUDA|Python|Space Ranger|Seurat|driver|CUDA|version|v|anndata|AnnData|pynndescent|igraph|leidenalg|numba|Numba|NumPy|SciPy|Singularity|Docker|NVLink|PCIe|DDR|NVIDIA|Platinum|Threadripper PRO|RTX|H100|A100|B200|B300|V100|DGX|release|Census|CELLxGENE|PR Veneto FESR|Priority|Objective|Action|PNC-I\.|CIBB|Claude Opus)\s*$")


def structural(t, ln, pos):
    before = ln[:pos]
    after = ln[pos + len(t):]
    for name, rx in STRUCT:
        if rx is not None and rx.search(before):
            return name
    if re.match(r"^\d{4}$", t) and 1980 <= int(t) <= 2026:
        return "date or year"
    if re.search(r"\d{4}-\d{2}-$", before + "") or re.match(r"^-\d{2}", after) or re.search(r"\d{2}/$", before) or re.match(r"^/\d{2}/", after):
        return "date or year"
    if t.count(".") >= 1 and re.match(r"^\.\d", after):
        return "version"
    if re.search(r"\d\.$", before) and re.search(r"\d+\.\d+\.$", before[-8:] + ""):
        return "version"
    if VERSION_CTX.search(before):
        return "version or hardware model"
    if re.match(r"^(?:\.\d+)*-(?:cuda|py)", after) or re.search(r"(?:cuda|py)$", before):
        return "version"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.chdir(REPO)
    receipt = set()
    for f in sorted(glob.glob("manuscript/revisione_n2/S3/ricevute_R*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            receipt |= {m.group(0).rstrip(",") for m in NUM.finditer(r["valore_scritto"])}
    vals = []
    for f in ("results_v2/S4/figure_values.csv", "results_v2/S5/figure_values.csv"):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            try:
                vals.append(float(r["value"]))
            except ValueError:
                pass
    def harvest(o):
        if isinstance(o, bool):
            return
        if isinstance(o, (int, float)):
            vals.append(float(o))
        elif isinstance(o, str):
            vals.extend(float(m.group(0).replace(",", "")) for m in NUM.finditer(o))
        elif isinstance(o, dict):
            for v in o.values():
                harvest(v)
        elif isinstance(o, list):
            for v in o:
                harvest(v)
    harvest(json.load(open("results_v2/S5/s5_numbers.json")))
    # step S1 outputs re-read by tools/s5_check.py (spatial)
    S1 = "SPATIAL/results_v2"
    for f in ("s1_step_stats.csv", "s1_speedups.csv"):
        for r in csv.DictReader(open(os.path.join(S1, f), encoding="utf-8")):
            for v in r.values():
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
    for f in (glob.glob(os.path.join(S1, "*.json")) + glob.glob(os.path.join(S1, "concordance_reference/*.json"))
              + glob.glob(os.path.join(S1, "cooc_check/*.json"))):
        harvest(json.load(open(f)))
    review = set()
    for r in csv.DictReader(open("manuscript/revisione_n2/revisione_n2_log.csv", encoding="utf-8")):
        if r["status"] == "PASS":
            review |= {m.group(0).rstrip(",") for m in NUM.finditer(r["claimed"] + " " + r["recomputed"])}
    manual = {}
    mf = "results_v2/S7/provenance_manual.csv"
    if os.path.exists(mf):
        for r in csv.DictReader(open(mf, encoding="utf-8")):
            if r["ok"] == "True":  # value recomputed by tools/s7_provenance_manual.py equals the token
                manual[(r["doc"], r["token"], r["context"])] = r

    def figure_match(t):
        x, d = val(t), dec(t)
        tol = 0.5 * 10 ** (-d) + 1e-9
        hit = any(abs(abs(v) - x) <= tol or abs(abs(v) * 100 - x) <= tol for v in vals)
        if not hit:
            return None
        return "figure" if (sig(t) >= 3 or dec(t) >= 2) else "figure (short token)"

    out = {"classes": {}, "by_doc": {}, "unresolved": []}
    for doc, path in (("chapter", "manuscript/full_paper_LNBI.md"), ("supplement", "manuscript/supplementary_LNBI.md")):
        cnt = {}
        for t, ln, pos in tokens(open(path, encoding="utf-8").read()):
            ctx = ln[max(0, pos - 50): pos + len(t) + 30]
            if t in receipt:
                c = "receipt"
            elif figure_match(t) == "figure":
                c = "figure"
            elif t in review:
                c = "review"
            else:
                s = structural(t, ln, pos)
                if s:
                    c = "structural: " + s
                elif figure_match(t):
                    c = "figure (short token)"
                elif any(k[0] == doc and k[1] == t and k[2] in ln for k in manual):
                    c = "manual"
                else:
                    c = None
            if c is None:
                out["unresolved"].append({"doc": doc, "token": t, "context": ctx})
                c = "unresolved"
            cnt[c] = cnt.get(c, 0) + 1
        out["by_doc"][doc] = dict(sorted(cnt.items(), key=lambda kv: -kv[1]))
    out["n_unresolved"] = len(out["unresolved"])
    out["pass"] = out["n_unresolved"] == 0
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"by_doc": out["by_doc"], "n_unresolved": out["n_unresolved"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
