#!/usr/bin/env python3
"""Generate the S2 implementation plan from the review log and the plan entries.

Stdlib only. Inputs (all under --dir, default manuscript/revisione_n2/piano):
  righe_da_pianificare.csv  424 non-PASS rows of the review log with script anchors
  voci/voci_*.csv           plan entries written per manuscript region
  arbitrati.csv             overrides decided in arbitration (id, campo, valore, motivo)
Also reads manuscript/full_paper_LNBI.md and manuscript/revisione_n2/revisione_n2_log.csv.
Outputs (same dir): ledger.csv, mappe/*.csv, checks.json, PIANO_IMPLEMENTAZIONE.md,
IMPL_diario.csv (header only, if missing).
Usage: python3 -B tools/s2_mkplan.py [--dir DIR] [--repo .]
"""
import argparse, csv, glob, hashlib, json, os, re, sys
from collections import defaultdict, Counter

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=".")
ap.add_argument("--dir", default="manuscript/revisione_n2/piano")
ap.add_argument("--existence", default=None, help="JSON {path: true/false} from the server check")
a = ap.parse_args()
R = a.repo; D = os.path.join(R, a.dir)
MS = os.path.join(R, "manuscript/full_paper_LNBI.md")
LOG = os.path.join(R, "manuscript/revisione_n2/revisione_n2_log.csv")
MS_MD5 = "4587032be8d2905007687e0bb50d848e"

def rcsv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

ms_bytes = open(MS, "rb").read()
ms_md5 = hashlib.md5(ms_bytes).hexdigest()
ms = ms_bytes.decode("utf-8").split("\n")
rows = {r["id"]: r for r in rcsv(os.path.join(D, "righe_da_pianificare.csv"))}
log = rcsv(LOG)
V = []
for p in sorted(glob.glob(os.path.join(D, "voci", "voci_*.csv"))):
    for r in rcsv(p):
        r["_file"] = os.path.basename(p); V.append(r)
arb = rcsv(os.path.join(D, "arbitrati.csv")) if os.path.exists(os.path.join(D, "arbitrati.csv")) else []
byid = {}
dup = [k for k, n in Counter(r["id"] for r in V).items() if n > 1]
for r in V:
    byid[r["id"]] = r
for x in arb:  # arbitration overrides, applied on regeneration
    if x["id"] in byid and x["campo"] in byid[x["id"]] and x["campo"] != "target":
        byid[x["id"]][x["campo"]] = x["valore"]
        byid[x["id"]].setdefault("_arb", []).append(x["campo"])

PCODE = re.compile(r"^(P\d+|PM|PF|PL|PS)")
def pcode(s):
    m = PCODE.match(s.strip()); return m.group(1) if m else s.strip()
def lvl(s):
    m = re.search(r"L([1-5])", s); return int(m.group(1)) if m else 0
def okind(s): return s.split(":")[0].strip()

for r in byid.values():
    rr = rows.get(r["id"], {})
    r["problem"] = pcode(r["problem"]); r["lv"] = lvl(r["level"]); r["kind"] = okind(r["outcome"])
    r["anchor"] = rr.get("anchor", ""); r["quality"] = rr.get("quality", "")
    try: r["line"] = int(float(rr.get("anchor_line") or 0))
    except ValueError: r["line"] = 0
    r["status"] = rr.get("status", ""); r["severity"] = rr.get("severity", ""); r["track"] = rr.get("track", "")
    r["section"] = rr.get("section", "")
for x in arb:  # arbitration on anchor fields (anchor, line, quality, target)
    if x["id"] in byid and x["campo"] in ("anchor", "line", "quality", "target"):
        byid[x["id"]][x["campo"]] = int(x["valore"]) if x["campo"] == "line" else x["valore"]
        byid[x["id"]].setdefault("_arb", []).append(x["campo"])

# resolve absorption chains
def final_of(i, seen=None):
    seen = seen or set()
    r = byid.get(i)
    if r is None or r["kind"] != "assorbita": return i
    if i in seen: return "CICLO:" + i
    seen.add(i); tgt = r["outcome"].split(":", 1)[1].strip()
    return final_of(tgt, seen)
absorbed = defaultdict(list)
for r in byid.values():
    if r["kind"] == "assorbita":
        r["final"] = final_of(r["id"]); absorbed[r["final"]].append(r["id"])
primary = [r for r in byid.values() if r["kind"] not in ("assorbita", "non-applicabile")]
prim_ids = {r["id"] for r in primary}

# ---------- checks ----------
checks = {"manuscript_md5": ms_md5, "G2_manuscript_unchanged": ms_md5 == MS_MD5}
missing = sorted(set(rows) - set(byid)); extra = sorted(set(byid) - set(rows))
bad_abs = sorted(r["id"] for r in byid.values() if r["kind"] == "assorbita" and r["final"] not in prim_ids)
empty_instr = sorted(r["id"] for r in byid.values() if not r["instruction"].strip())
na_noreason = sorted(r["id"] for r in byid.values() if r["kind"] == "non-applicabile" and not (r["instruction"].strip() or r["note"].strip()))
checks["G3"] = {"rows": len(rows), "entries": len(byid), "duplicates": dup, "missing": missing, "extra": extra,
                "absorbed_to_nonprimary": bad_abs, "empty_instruction": empty_instr, "na_without_reason": na_noreason,
                "pass": not (dup or missing or extra or bad_abs or empty_instr or na_noreason)}
def count_occ(s): return sum(l.count(s) for l in ms) if s else 0
g4_bad, g4_nonprose, g4_vo = [], [], []
for r in byid.values():
    prose = r["target"].strip().startswith("prosa")
    if r["quality"] == "univoca":
        n = count_occ(r["anchor"])
        if not r["anchor"].strip() or n != 1: g4_bad.append((r["id"], n))
        elif r["line"] and r["anchor"] not in ms[r["line"] - 1]: g4_bad.append((r["id"], "anchor-not-on-line"))
        elif r["kind"] not in ("assorbita", "non-applicabile") and r["value_old"].strip() and r["line"]:
            win = " ".join(ms[max(0, r["line"] - 2):r["line"] + 1])
            miss = [v for v in r["value_old"].split(" | ") if v.strip() and v.strip() not in win]
            if miss: g4_vo.append((r["id"], miss[:2]))
    elif prose and r["kind"] not in ("assorbita", "non-applicabile"):
        g4_nonprose.append(r["id"])
checks["G4"] = {"unique_anchors_checked": sum(1 for r in byid.values() if r["quality"] == "univoca"),
                "unique_anchor_failures": g4_bad, "prose_target_without_unique_anchor": g4_nonprose,
                "value_old_not_near_anchor": g4_vo,
                "pass": not g4_bad and not g4_nonprose}
dash = sorted(r["id"] for r in byid.values() if any(ch in (r["instruction"] + r["note"] + r["value_new"]) for ch in "\u2013\u2014"))
checks["no_dashes"] = {"ids": dash, "pass": not dash}

# ---------- maps ----------
CITE = re.compile(r"\b[Rr]ig(?:a|he)\s+(\d{1,3})(?:\s*[-e]\s*(\d{1,3}))?(?!\s+(?:di|della|del)\s+Table)")
for r in primary:
    ls = {r["line"]} if r["line"] else set()
    for m in CITE.finditer(r["instruction"]):
        a1 = int(m.group(1)); b1 = int(m.group(2)) if m.group(2) else a1
        pre = r["instruction"][max(0, m.start() - 12):m.start()]
        if "Table" in pre or a1 > len(ms) or b1 < a1 or b1 - a1 > 12: continue
        ls |= set(range(a1, b1 + 1))
    r["lines_all"] = sorted(ls)
NUM = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{2,})(?:x|%)?(?![\w])")
def toks(s): return {m.group(1) for m in NUM.finditer(s or "")}
# 1 transactions
byline = defaultdict(list)
for r in primary:
    for ln in r["lines_all"]:
        if ms[ln - 1].strip(): byline[ln].append(r)
trans = [{"line": ln, "n": len(g), "ids": ";".join(sorted(x["id"] for x in g)),
          "steps": ";".join(sorted({x["step"] for x in g})), "levels": ";".join(sorted({x["level"] for x in g}))}
         for ln, g in sorted(byline.items()) if len(g) > 1]
# 2 value occurrences
declared = defaultdict(set)
for r in primary:
    for t in toks(r["value_old"]): declared[t].add(r["line"])
def theader(i):
    if not ms[i - 1].strip().startswith("|"): return ""
    j = i - 1
    while j > 0 and ms[j - 1].strip().startswith("|"): j -= 1
    return ms[j].strip()[:80]
occ = []
for r in primary:
    if r["kind"] not in ("correggere", "superata-da-S1", "togliere", "riformulare", "aggiungere", "verificare-in-step") or not r["value_old"].strip(): continue
    tk = toks(r["value_old"])
    if r["kind"] not in ("correggere", "superata-da-S1", "togliere"):
        QT = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+(?=\s?(?:x\b|%|-fold)))")
        tk = {m.group(1) for m in QT.finditer(r["value_old"])}
    for t in sorted(tk):
        if len(t.replace(",", "").replace(".", "")) < 2: continue
        for i, l in enumerate(ms, 1):
            if i in r["lines_all"] or not any(m.group(1) == t for m in NUM.finditer(l)): continue
            other = sorted(x["id"] for x in byline.get(i, []) if t in toks(x["value_old"]))
            occ.append({"id": r["id"], "token": t, "line": i, "covered_by": ";".join(other),
                        "action": "coperta" if other else "da-classificare",
                        "table_header": theader(i), "text": l.strip()[:120]})
ocl_p = os.path.join(D, "occorrenze_classificate.csv")
if os.path.exists(ocl_p):
    ocl = {(x["id"], x["token"], str(x["line"])): x for x in rcsv(ocl_p)}
    for o in occ:
        k = (o["id"], o["token"], str(o["line"]))
        if k in ocl and o["action"] == "da-classificare":
            o["action"] = ocl[k]["action"]; o["motivo"] = ocl[k].get("motivo", "")
# 3 PASS decay (and verification-log map: the review log is the verification log)
changed = set()
for r in primary:
    if r["kind"] in ("correggere", "superata-da-S1", "togliere", "riformulare"): changed |= toks(r["value_old"])
decay = []
for p in log:
    if p["status"] != "PASS": continue
    sh = sorted(t for t in toks(p["claimed"]) & changed if any(t in l for l in ms))
    if sh: decay.append({"pass_id": p["id"], "line": p["line"], "section": p["section"], "shared": ";".join(sh),
                         "claimed": p["claimed"][:120]})
SPAT = set(range(118, 167)) | set(range(324, 410)) | {413, 428, 429, 430, 440}
have0 = {d["pass_id"] for d in decay}
for p in log:
    if p["status"] != "PASS" or p["id"] in have0: continue
    try: pl = int(float(p["line"] or 0))
    except ValueError: pl = 0
    if "SPATIAL/results/" in p.get("source", "") or pl in SPAT:
        decay.append({"pass_id": p["id"], "line": p["line"], "section": p["section"], "shared": "spatial-marzo",
                      "claimed": p["claimed"][:120]})
pcl_p = os.path.join(D, "pass_classificati.csv")
if os.path.exists(pcl_p):
    pcl = {x["pass_id"]: x for x in rcsv(pcl_p)}
    have = {d["pass_id"] for d in decay}
    logby = {p["id"]: p for p in log}
    for pid, x in pcl.items():
        if pid not in have and pid in logby:
            p = logby[pid]
            decay.append({"pass_id": pid, "line": p["line"], "section": p["section"], "shared": x.get("shared", ""),
                          "claimed": p["claimed"][:120]})
    for d in decay:
        x = pcl.get(d["pass_id"], {}); d["esito"] = x.get("esito", "") or ("ridichiarare" if d["shared"] == "spatial-marzo" else "da-classificare"); d["motivo"] = x.get("motivo", "") or ("riga spatial o fonte SPATIAL/results/ (marzo): superata da S1" if d["shared"] == "spatial-marzo" else "")
# 4 dependencies
IDR = re.compile(r"R\d{4}|D-\d{2}|CONV|PI-S3|PI-S5|NEIGH")
deps, dep_bad = [], []
for r in primary:
    for d in sorted(set(IDR.findall(r["depends_on"] + " " + r["decision"]))):
        if d.startswith("R"):
            fd = final_of(d) if d in byid else d
            if fd not in prim_ids: dep_bad.append((r["id"], d))
            d = fd
        deps.append({"id": r["id"], "depends_on": d, "step": r["step"]})
checks["dependencies_to_missing"] = dep_bad
G = defaultdict(set)
for d in deps:
    if d["depends_on"] in prim_ids and d["depends_on"] != d["id"]: G[d["id"]].add(d["depends_on"])
cycles, color = [], {}
def dfs(u, stack):
    color[u] = 1; stack.append(u)
    for v in sorted(G[u]):
        if color.get(v) == 1: cycles.append(stack[stack.index(v):] + [v])
        elif not color.get(v): dfs(v, stack)
    stack.pop(); color[u] = 2
for u in sorted(G):
    if not color.get(u): dfs(u, [])
# mutual dependencies = entries to execute together: strongly connected components (Tarjan)
idx, low, onst, st, sccs, cnt = {}, {}, set(), [], [], [0]
def tarjan(u):
    idx[u] = low[u] = cnt[0]; cnt[0] += 1; st.append(u); onst.add(u)
    for v in sorted(G[u]):
        if v not in idx: tarjan(v); low[u] = min(low[u], low[v])
        elif v in onst: low[u] = min(low[u], idx[v])
    if low[u] == idx[u]:
        comp = []
        while True:
            w = st.pop(); onst.discard(w); comp.append(w)
            if w == u: break
        if len(comp) > 1: sccs.append(sorted(comp))
sys.setrecursionlimit(10000)
for u in sorted(G):
    if u not in idx: tarjan(u)
joint = [{"gruppo": "J%02d" % (k + 1), "ids": ";".join(c), "steps": ";".join(sorted({byid[i]["step"] for i in c}))} for k, c in enumerate(sccs)]
def compact(c):
    ls = sorted({l for i in c for l in byid[i].get("lines_all", [])})
    return len(ls) > 0 and ls[-1] - ls[0] <= max(2, len(ls))
multi_step = [j for j, c in zip(joint, sccs) if ";" in j["steps"]]
checks["dependency_cycles"] = {"n_cycles": len(cycles), "joint_groups": len(joint), "groups_across_steps": multi_step,
                               "pass": not multi_step}
# 5 sources and scripts
TOP = ("SPATIAL", "results", "scripts", "slurm", "figures", "manuscript", "tools", "reports", "docs", "manifests", "data", "logs")
PATH = re.compile(r"(?<![\w/.~-])((?:[\w.*{},-]+/)+[\w.*{},-]*[\w*}])")
src = defaultdict(set); ext = defaultdict(set)
for r in primary:
    for m in PATH.finditer(r["source"] + " " + r["instruction"]):
        p = m.group(1).rstrip(".,;:)")
        if p.split("/")[0] in TOP: src[p].add(r["id"])
        elif p.startswith("../figures/"): src["figures/" + p[len("../figures/"):]].add(r["id"])
        elif p.startswith("lncs_latex/"): src["manuscript/" + p].add(r["id"])
        elif p.startswith("stile/"): src["manuscript/revisione_n2/" + p].add(r["id"])
        elif p.startswith("tracks/"): src["manuscript/revisione_n2/script_e_calcoli.zip::" + p].add(r["id"])
        elif not re.match(r"^(https?|doi|10\.)", p) and "/" in p: ext[p].add(r["id"])
exist = json.load(open(a.existence)) if a.existence else {}
srcmap = [{"path": p, "ids": ";".join(sorted(v)), "exists": exist.get(p, "non-controllato")} for p, v in sorted(src.items())]
checks["G5"] = {"paths": len(srcmap), "missing": [s["path"] for s in srcmap if s["exists"] is False],
                "unchecked": [s["path"] for s in srcmap if s["exists"] == "non-controllato"]}
checks["G5"]["to_create"] = [s["path"] + " (" + str(s["exists"]) + ")" for s in srcmap if str(s["exists"]).startswith("da-creare")]
checks["G5"]["pass"] = bool(exist) and not checks["G5"]["missing"] and not checks["G5"]["unchecked"]

os.makedirs(os.path.join(D, "mappe"), exist_ok=True)
def wcsv(name, recs, cols):
    with open(os.path.join(D, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(recs)
LED = ["id", "track", "status", "severity", "problem", "level", "step", "decision", "target", "outcome", "final",
       "line", "quality", "anchor", "instruction", "value_old", "value_new", "source", "depends_on", "note"]
for r in byid.values(): r.setdefault("final", r["id"] if r["id"] in prim_ids else "")
wcsv("ledger.csv", sorted(byid.values(), key=lambda r: r["id"]), LED)
wcsv("mappe/transazioni.csv", trans, ["line", "n", "ids", "steps", "levels"])
wcsv("mappe/occorrenze_valore.csv", occ, ["id", "token", "line", "covered_by", "action", "motivo", "table_header", "text"])
wcsv("mappe/pass_che_decadono.csv", decay, ["pass_id", "line", "section", "shared", "esito", "motivo", "claimed"])
wcsv("mappe/dipendenze.csv", deps, ["id", "depends_on", "step"])
wcsv("mappe/gruppi_insieme.csv", joint, ["gruppo", "ids", "steps"])
wcsv("mappe/fonti_e_script.csv", srcmap, ["path", "ids", "exists"])
def ext_class(p):
    if re.search(r"\.(py|txt|csv|tex|md|json|png)$", p): return "file di un pacchetto o dell'ambiente (non del repo)"
    if p.startswith(("lucavd/", "nvcr.io/")): return "immagine container"
    if p.startswith("api.crossref.org"): return "servizio esterno"
    return "non e' un percorso (rapporto o elenco scritto con la barra)"
wcsv("mappe/riferimenti_fuori_repo.csv", [{"ref": p, "classe": ext_class(p), "ids": ";".join(sorted(v))} for p, v in sorted(ext.items())], ["ref", "classe", "ids"])
if not os.path.exists(os.path.join(D, "IMPL_diario.csv")):
    wcsv("IMPL_diario.csv", [], ["id", "livello", "esito", "valore_inserito", "convenzione", "fonte_riletta", "riga", "data", "note"])
stats = {"primary": len(primary), "by_kind": Counter(r["kind"] for r in byid.values()),
         "primary_by_step": Counter(r["step"] for r in primary), "primary_by_level": Counter(r["level"] for r in primary),
         "transactions": len(trans), "occurrences": len(occ), "occ_unclassified": sum(1 for o in occ if o["action"] == "da-classificare"),
         "pass_decay": len(decay), "refs_outside_repo": len(ext), "arbitrated_fields": sum(len(r.get("_arb", [])) for r in byid.values())}
checks["stats"] = stats
json.dump(checks, open(os.path.join(D, "checks.json"), "w"), indent=1, ensure_ascii=False, default=dict)

# ---------- plan document ----------
STEPN = {"S3": "correzioni di sostanza", "S4": "figure 1-6", "S5": "integrazione dei risultati spatial",
         "S6": "taglio e stile", "S7": "LaTeX, METEOR e verifica finale"}
PNAME = {"P1": "titolo, abstract, estensione", "P2": "dataset Census", "P3": "multi-GPU", "P4": "spatial",
         "P5": "bibliografia", "P6": "stress test replicato", "P7": "espressione differenziale",
         "P8": "peso del Wilcoxon nel 120x", "P9": "convenzione sulle ripetizioni", "P10": "concordanza",
         "P11": "ambiente e hardware", "P12": "novità e posizionamento", "P13": "affermazioni oltre i dati",
         "P14": "figure", "PM": "arrotondamenti e minori", "PF": "finanziamento", "PL": "LaTeX e METEOR", "PS": "stile"}
def blk(r):
    s = [f"#### {r['id']} · {r['step']} · {r['problem']} ({PNAME.get(r['problem'], '')}) · {r['kind']}"]
    where = f"riga {r['line']}" if r["line"] else "fuori dalla prosa"
    s.append(f"- **Bersaglio:** {r['target']} ({where}); registro: {r['status']}, {r['severity']}")
    if r["anchor"] and r["quality"] == "univoca":
        anc = r["anchor"] if len(r["anchor"]) <= 160 else r["anchor"][:157] + "..."
        s.append(f"- **Ancora (univoca nel .md):** `{anc}`")
    if r["value_old"] or r["value_new"]:
        s.append(f"- **Valore:** {r['value_old'] or 'n.d.'} → {r['value_new'] or '(da rileggere, vedi fonte)'}")
    s.append(f"- **Istruzione:** {r['instruction']}")
    if r["decision"]: s.append(f"- **Decisione o convenzione:** {r['decision']}")
    if r["source"]: s.append(f"- **Fonte:** {r['source']}")
    if r["depends_on"]:
        dd = re.sub(r"R\d{4}", lambda m: m.group(0) + (f" (assorbita in {final_of(m.group(0))})" if m.group(0) in byid and byid[m.group(0)]["kind"] == "assorbita" else ""), r["depends_on"])
        s.append(f"- **Dipende da:** {dd}")
    if absorbed.get(r["id"]): s.append(f"- **Assorbe:** {', '.join(sorted(absorbed[r['id']]))}")
    if r["note"]: s.append(f"- **Nota:** {r['note']}")
    if r.get("_arb"): s.append(f"- **Modificata in arbitrato:** {', '.join(r['_arb'])} (vedi `arbitrati.csv`)")
    return "\n".join(s)
pre = open(os.path.join(D, "PIANO_testa.md"), encoding="utf-8").read() if os.path.exists(os.path.join(D, "PIANO_testa.md")) else ""
out = [pre]
out.append("\n# Voci per difficoltà crescente\n")
out.append("Il livello misura la difficoltà, non la precedenza: l'ordine di lavoro è nella sezione «Sequenza di lavoro».\n")
LN = {1: "L1 · sostituzione di una cifra", 2: "L2 · riformulazione", 3: "L3 · tabella da aggregati",
      4: "L4 · nuovo calcolo dai grezzi", 5: "L5 · decisione strutturale"}
for L in range(1, 6):
    g = sorted((r for r in primary if r["lv"] == L), key=lambda r: (r["step"], r["line"], r["id"]))
    out.append(f"\n## {LN[L]} ({len(g)} voci)\n")
    out.extend(blk(r) + "\n" for r in g)
out.append("\n# Sequenza di lavoro per dipendenza\n")
for st in ["S3", "S4", "S5", "S6", "S7"]:
    g = [r for r in primary if r["step"] == st]
    if not g: continue
    dec = sorted({d for r in g for d in IDR.findall(r["decision"] + " " + r["depends_on"]) if not d.startswith("R")})
    tl = sorted({t["line"] for t in trans if st in t["steps"].split(";")})
    iso = sorted(r["id"] for r in g if r["line"] not in tl)
    out.append(f"\n## {st}: {STEPN[st]} ({len(g)} voci)\n")
    out.append(f"1. Decisioni da registrare prima della prima voce che ne dipende: {', '.join(dec) or 'nessuna'}.")
    jg = [j for j in joint if j["steps"] == st]
    out.append(f"   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: {'; '.join(j['gruppo'] + ' (' + j['ids'].replace(';', ', ') + ')' for j in jg) or 'nessuno'}.")
    out.append(f"2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): {len(tl)} righe ({', '.join(map(str, tl)) or 'nessuna'}).")
    out.append(f"3. Voci isolate: {len(iso)}.\n")
out.append("\n# Mappe\n")
out.append(f"- Transazioni: `mappe/transazioni.csv` ({len(trans)} righe del manoscritto).")
out.append(f"- Altre occorrenze dei valori che cambiano: `mappe/occorrenze_valore.csv` ({len(occ)} occorrenze, {stats['occ_unclassified']} da classificare come propagare, omografo o valore confermato).")
out.append(f"- Conferme del registro che decadono (il registro della revisione n.2 è il log di verifica del testo): `mappe/pass_che_decadono.csv` ({len(decay)} righe PASS).")
out.append(f"- Dipendenze: `mappe/dipendenze.csv` ({len(deps)} legami); voci da eseguire insieme: `mappe/gruppi_insieme.csv` ({len(joint)} gruppi).")
out.append(f"- Fonti e script: `mappe/fonti_e_script.csv` ({len(srcmap)} percorsi, esistenza controllata sul server: {'sì' if exist else 'no'}).")
post = open(os.path.join(D, "PIANO_coda.md"), encoding="utf-8").read() if os.path.exists(os.path.join(D, "PIANO_coda.md")) else ""
out.append(post)
open(os.path.join(D, "PIANO_IMPLEMENTAZIONE.md"), "w", encoding="utf-8").write("\n".join(out))
print(json.dumps({k: (v["pass"] if isinstance(v, dict) and "pass" in v else v) for k, v in checks.items() if k != "stats"}, default=str))
print(json.dumps(stats, default=dict))
