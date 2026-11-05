#!/usr/bin/env python3
"""S7: build the clean public release tree (decision D-25) from a commit of the working repository.

Files are selected from `git ls-files` at --commit with an explicit allowlist (INCLUDE) and
an explicit blocklist (EXCLUDE), extracted with `git archive`, then README.md is rewritten
for the release and CITATION.cff is added. Checks written to <out>/../release_check.json:
  - no PDF under manuscript/bibliography, no excluded path, no file over 50 MB;
  - no credential-like string (GitHub/Zenodo tokens, private keys, Authorization headers);
  - every relative link of the Markdown files resolves inside the tree (dangling ones listed);
  - md5 of every file (release_manifest.tsv inside the tree).
Usage: python3 -B tools/s7_release_tree.py --commit SHA --out DIR --doi DOI
"""
import argparse, fnmatch, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = [".gitignore", "LICENSE.md", "Dockerfile", "Makefile", "constraints.txt", "requirements-squidpy.txt",
           "README.md", "scripts/*", "slurm/*", "SPATIAL/*", "results/*", "results_v2/*", "manifests/*",
           "figures/*", "tools/*", "docs/*", "reports/*",
           "manuscript/full_paper_LNBI.md", "manuscript/supplementary_LNBI.md",
           "manuscript/bibliography/cibb2026_references.bib", "manuscript/lncs_latex/*",
           "manuscript/00_LEGGIMI_revisione_n2.md", "manuscript/revisione_n2/*"]
EXCLUDE = ["*.pdf@manuscript/bibliography", "manuscript/revisione_n2/PROMPT_*", "manuscript/revisione_n2/SKILL_*",
           "CLAUDE.md", ".windsurf/*", "_view_*"]
SECRET = re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                    r"Authorization:\s*Bearer\s+\S{20,}|access_token=[A-Za-z0-9]{30,}")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def selected(path):
    for e in EXCLUDE:
        if "@" in e:
            pat, root = e.split("@")
            if path.startswith(root + "/") and fnmatch.fnmatch(os.path.basename(path), pat):
                return False
        elif fnmatch.fnmatch(path, e):
            return False
    return any(fnmatch.fnmatch(path, i) for i in INCLUDE)


def release_readme(text, doi):
    lines = text.split("\n")
    assert lines[0] == "# 2026.scRNA_DGX", lines[0]
    t = "\n".join(lines[1:])
    t = re.sub(r"\n> Working repository\..*?\n", "\n", t, count=1)
    head = ("# scRNA-DGX-benchmark\n\n"
            "Release v1.0.0, archived on Zenodo: <https://doi.org/%s>.\n\n"
            "GPU-accelerated single-cell and spatial transcriptomics benchmark: rapids-singlecell on NVIDIA H100 GPUs "
            "against Scanpy on 100 logical CPUs of a DGX H100 node (scRNA-seq), and an RTX 4090 against the same CPU "
            "reference (spatial). This is the cleaned, archived release of the working repository "
            "<https://github.com/lucavd/2026.scRNA_DGX>. The chapter extending the CIBB 2026 short paper in Springer LNBI and its "
            "Supplementary Material are in `manuscript/` (`full_paper_LNBI.md`, `supplementary_LNBI.md`; LaTeX and PDF in "
            "`manuscript/lncs_latex/`).\n" % doi)
    t, n = re.subn(r"(?s)^\s*GPU-accelerated single-cell and spatial transcriptomics benchmark on NVIDIA DGX H100,.*?\n\n", "\n", t, count=1)
    assert n == 1, "short-paper description not found"
    structure = """## Repository structure

```
.
|-- Dockerfile, Makefile, constraints.txt, requirements-squidpy.txt   # container and pinned packages
|-- scripts/          # scRNA-seq benchmarks, data download, figure scripts
|-- slurm/            # SLURM submission scripts used on the DGX H100 cluster
|-- SPATIAL/          # spatial benchmark: scripts, Dockerfiles, March 2026 results, results_v2 (chapter reference)
|-- results/          # scRNA-seq benchmark JSON outputs
|-- results_v2/       # receipts of the checks of each revision step (S2-S7)
|-- figures/          # vector PDF figures, PNG previews, LEGENDS.md (file -> figure number)
|-- manuscript/       # chapter and Supplementary Material (Markdown, LaTeX llncs 2.26, PDF), bibliography,
|                     # second internal review (revisione_n2/, in Italian): ledger, receipts, scripts
|-- tools/            # deterministic checks that re-read every number of the text from the result files
|-- manifests/        # md5 manifest of the raw results
|-- docs/, reports/   # step-by-step provenance of the revision (decisions, expectations, reports; in Italian)
`-- CITATION.cff
```
"""
    t = re.sub(r"(?s)## Repository structure\n.*?(?=\n## Requirements)", structure, t, count=1)
    t = t.replace("git clone https://github.com/lucavd/2026.scRNA_DGX.git", "git clone https://github.com/lucavd/scRNA-DGX-benchmark.git")
    t = t.replace("   cd 2026.scRNA_DGX\n", "   cd scRNA-DGX-benchmark\n")
    checks = """## How the numbers of the chapter are checked

- `tools/s7_md2lncs.py` generates the LaTeX sources in `manuscript/lncs_latex/` from the Markdown; `tools/s7_check.py` checks that the numbers and citations of the `.tex` are those of the `.md`, in the same order.
- `tools/s3_check.py` (with `manuscript/revisione_n2/S3/valori_R*.py`), `tools/s4_check.py` and `tools/s5_check.py` recompute from the result files the values written in the text and drawn in the figures; `tools/s7_provenance.py` assigns a source to every number of the chapter and of the Supplementary Material.
- `tools/check_manifest.py` compares the raw results with `manifests/raw_results_md5_2026-11-03.tsv`.
- Per-cell outputs (cluster labels, DE tables, k-NN indices) and SLURM logs are not included because of their size. The input data are public: CZ CELLxGENE Census release 2025-11-08 (`scripts/download_data.py`), 10x Genomics Visium v1 Mouse Brain Sagittal Anterior and Visium HD Mouse Brain FFPE, Space Ranger 3.0.0 (`SPATIAL/scripts/download_spatial_data.py`, which checks the md5 of the Visium HD matrices).

"""
    t = t.replace("## Citation\n", checks + "## Citation\n", 1)
    t = re.sub(r"(?s)## Citation\n.*?(?=\n## License)",
               "## Citation\n\nPlease cite the LNBI chapter once published and this archive: <https://doi.org/%s> (see `CITATION.cff`). "
               "Bibliography entries for all tools and datasets used are in `manuscript/bibliography/cibb2026_references.bib`.\n" % doi, t, count=1)
    return head + t


def citation_cff(doi):
    aff = ("Unit of Biostatistics, Epidemiology and Public Health, Department of Cardiac, Thoracic, Vascular Sciences "
           "and Public Health, University of Padova, Padova, Italy")
    authors = [("Vedovelli", "Luca"), ("Lanera", "Corrado"), ("Sabbatini", "Daniele"), ("Gregori", "Dario")]
    out = ["cff-version: 1.2.0", "message: \"If you use this software or these results, please cite them as below.\"",
           "title: \"scRNA-DGX-benchmark: code, results and Supplementary Material of a GPU versus CPU benchmark of single-cell and spatial transcriptomics\"",
           "version: 1.0.0", "doi: %s" % doi, "license: MIT", "repository-code: \"https://github.com/lucavd/scRNA-DGX-benchmark\"",
           "type: software", "authors:"]
    orcid = {"Vedovelli": "0000-0003-4847-2333"}  # checked on pub.orcid.org, 2026-11-05
    for fam, giv in authors:
        out += ["  - family-names: \"%s\"" % fam, "    given-names: \"%s\"" % giv, "    affiliation: \"%s\"" % aff]
        if fam in orcid:
            out.append("    orcid: \"https://orcid.org/%s\"" % orcid[fam])
    out += ["keywords:", "  - GPU computing", "  - single-cell RNA-seq", "  - spatial transcriptomics", "  - benchmarking", "  - rapids-singlecell"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--doi", required=True)
    a = ap.parse_args()
    files = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", a.commit], capture_output=True, text=True, check=True).stdout.split("\n")
    files = [f for f in files if f]
    keep = sorted(f for f in files if selected(f))
    dropped = sorted(f for f in files if not selected(f))
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    tar = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", a.commit, "--"] + keep, capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(a.out)
    rd = os.path.join(a.out, "README.md")
    new_readme = release_readme(open(rd, encoding="utf-8").read(), a.doi)
    open(rd, "w", encoding="utf-8").write(new_readme)
    open(os.path.join(a.out, "CITATION.cff"), "w", encoding="utf-8").write(citation_cff(a.doi))
    # checks
    allf = []
    for root, dirs, fs in os.walk(a.out):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in fs:
            allf.append(os.path.relpath(os.path.join(root, f), a.out))
    big = [f for f in allf if os.path.getsize(os.path.join(a.out, f)) > 50 * 2 ** 20]
    bad = [f for f in allf if not selected(f) and f not in ("CITATION.cff", "release_manifest.tsv")]
    secrets = []
    for f in allf:
        p = os.path.join(a.out, f)
        if os.path.getsize(p) < 20 * 2 ** 20:
            try:
                if SECRET.search(open(p, encoding="utf-8", errors="ignore").read()):
                    secrets.append(f)
            except OSError:
                pass
    dangling = []
    for f in allf:
        if f.endswith((".md", ".qmd")):
            txt = open(os.path.join(a.out, f), encoding="utf-8", errors="ignore").read()
            for link in re.findall(r"\]\(([^)\s]+)\)", txt):
                if re.match(r"^(https?:|mailto:|#|\{\{)", link):
                    continue
                target = os.path.normpath(os.path.join(os.path.dirname(f), link.split("#")[0]))
                if target and not os.path.exists(os.path.join(a.out, target)):
                    dangling.append({"file": f, "link": link})
    with open(os.path.join(a.out, "release_manifest.tsv"), "w") as fh:
        fh.write("path\tbytes\tmd5\n")
        for f in sorted(allf):
            p = os.path.join(a.out, f)
            fh.write("%s\t%d\t%s\n" % (f, os.path.getsize(p), md5(p)))
    total = sum(os.path.getsize(os.path.join(a.out, f)) for f in allf)
    rec = {"commit": a.commit, "doi": a.doi, "n_files": len(allf) + 1, "bytes": total, "n_dropped": len(dropped),
           "dropped": dropped, "over_50MB": big, "not_selected_but_present": bad, "credential_like": secrets,
           "dangling_links": dangling, "pass": not big and not bad and not secrets}
    json.dump(rec, open(os.path.join(os.path.dirname(a.out.rstrip("/")), "release_check.json"), "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 40 else v[:40] + ["..."]) for k, v in rec.items()})[:6000])


if __name__ == "__main__":
    main()
