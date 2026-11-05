#!/usr/bin/env python3
"""Open Knowledge Format v0.2 tooling for the LNBI chapter documentation bundle (docs/).

Adapted from the MMM project tool (lucavd/MMM, tools/okf.py) on 2026-11-03.

  python3 tools/okf.py check --bundle docs
      Rebuilds every index.md from the frontmatter, then checks every markdown file of
      the bundle. Run before each commit; exit status 1 on failure.

  python3 tools/okf.py link --bundle docs FILE [FILE ...] [--no-steps]
      In place: bare decision codes (D-nn) become links whose text is the decision
      title; step codes (Sn) become links to the step file (not in headings or ranges).

Checks: every non-reserved .md has frontmatter with non-empty type, title and
description; reserved files (index.md, log.md) carry no frontmatter, except okf_version
in the root index.md; no decision code outside a link anywhere; inside a git repository,
no markdown file of the bundle ignored by .gitignore. Codes of other registers
(review problems P1-P14, peer-review points Hnn) are warnings.
Links are relative paths, which OKF allows and which also resolve on GitHub and in
editors. Standard library only.
Spec: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

CODE_RE = re.compile(r"(?<![\w\[])(D-\d{2}[bc]?)(?![\w])")
STEP_RE = re.compile(r"(?<![\w\[/-])(S[0-7])(?![\w]|-S\d)")
PROTECT_RE = re.compile(r"(`[^`]*`|\[[^\]]*\]\([^)]*\))")
BARE_CODE_RE = re.compile(r"\bD-\d{2}[bc]?\b")
OTHER_CODES_RE = re.compile(r"\b(P\d{1,2}|H\d{1,2})\b")
STEPS = {
    "S0": "basi del lavoro", "S1": "nuovo riferimento spatial", "S2": "piano delle correzioni",
    "S3": "correzioni di sostanza", "S4": "figure scRNA", "S5": "integrazione spatial",
    "S6": "taglio e stile", "S7": "LaTeX e pacchetto METEOR",
}
RESERVED = {"index.md", "log.md"}
DIR_HEADINGS = {"steps": "Step"}
DIR_DESCRIPTIONS = {
    "decisions": "Una decisione per file, con titolo e descrizione in parole semplici, chi l'ha presa e se è in vigore.",
    "steps": "Un file per step: dubbi ricevuti, attese, riassunto In breve, approvazione del PI, link al report.",
}


def id_key(code):
    m = re.match(r"D-(\d+)([a-z]?)", code)
    return (int(m.group(1)), m.group(2)) if m else (10**6, code)


def read_frontmatter(path):
    """Return (dict of flat keys, body). Quoted values are JSON-decoded; others kept raw."""
    txt = pathlib.Path(path).read_text(encoding="utf-8")
    if not txt.startswith("---\n") or "\n---\n" not in txt[4:]:
        return None, txt
    fm_txt, body = txt[4:].split("\n---\n", 1)
    fm = {}
    for line in fm_txt.splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        val = m.group(2).strip()
        if val.startswith('"'):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
        fm[m.group(1)] = val
    return fm, body


def decision_titles(bundle):
    titles = {}
    for p in pathlib.Path(bundle, "decisions").glob("D-*.md"):
        fm, _ = read_frontmatter(p)
        if fm and fm.get("title"):
            titles[p.stem] = fm["title"]
    return titles


def link_text(text, titles, bundle, file_dir, link_steps=True):
    """Link bare D-nn (everywhere) and Sn (outside headings, ranges) with readable text."""
    bundle, file_dir = os.path.abspath(bundle), os.path.abspath(file_dir)

    def rel(*parts):
        return os.path.relpath(os.path.join(bundle, *parts), file_dir)

    def dec(m):
        code = m.group(1)
        return f"[{titles[code]} ({code})]({rel('decisions', code + '.md')})" if code in titles else code

    def step(m):
        code = m.group(1)
        return f"[{STEPS[code]} ({code})]({rel('steps', code + '.md')})"

    out, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if in_fence or line.lstrip().startswith("```"):
            out.append(line)
            continue
        heading = line.lstrip().startswith("#")
        parts = PROTECT_RE.split(line)
        for k in range(0, len(parts), 2):
            p = CODE_RE.sub(dec, parts[k])
            if link_steps and not heading:
                p = STEP_RE.sub(step, p)
            parts[k] = p
        out.append("".join(parts))
    return "\n".join(out)


def link_file(path, titles, bundle, link_steps=True):
    path = pathlib.Path(path)
    txt = path.read_text(encoding="utf-8")
    if txt.startswith("---\n") and "\n---\n" in txt[4:]:
        fm_txt, body = txt[4:].split("\n---\n", 1)
        head = "---\n" + fm_txt + "\n---\n"
    else:
        head, body = "", txt
    path.write_text(head + link_text(body, titles, bundle, path.parent, link_steps), encoding="utf-8")


def _strip_protected(body):
    return PROTECT_RE.sub("", body)


def check_file(path, bundle):
    fm, body = read_frontmatter(path)
    problems, warns = [], []
    if path.name in RESERVED:
        is_root_index = path.name == "index.md" and path.parent.resolve() == pathlib.Path(bundle).resolve()
        if fm is not None and not (is_root_index and set(fm) <= {"okf_version"}):
            problems.append("reserved file with frontmatter")
    else:
        if fm is None:
            return ["missing frontmatter"], []
        problems += [f"missing {k}" for k in ("type", "title", "description") if not fm.get(k)]
        for k in ("title", "description"):
            if BARE_CODE_RE.search(str(fm.get(k, ""))):
                warns.append(f"decision code in {k}")
        warns += sorted(set(OTHER_CODES_RE.findall(_strip_protected(body))))
    bare = sorted(set(BARE_CODE_RE.findall(_strip_protected(body))), key=id_key)
    if bare:
        problems.append("bare decision codes: " + ", ".join(bare))
    return problems, warns


def concepts_in(d):
    return [p for p in sorted(pathlib.Path(d).glob("*.md")) if p.name not in RESERVED]


def build_indexes(bundle):
    bundle = pathlib.Path(bundle)
    for d in sorted(p for p in bundle.rglob("*") if p.is_dir()):
        files = concepts_in(d)
        if not files:
            continue
        lines = []
        if d.name == "decisions":
            groups = {}
            for p in sorted(files, key=lambda p: id_key(p.stem)):
                fm, _ = read_frontmatter(p)
                groups.setdefault((fm or {}).get("group", "Altre decisioni"), []).append((p, fm or {}))
            for g, items in groups.items():
                lines.append(f"# {g}\n")
                for p, fm in items:
                    flag = " (superata)" if fm.get("status") == "deprecated" else ""
                    lines.append(f"* [{fm.get('title')} ({p.stem})]({p.name}){flag} - {fm.get('description')}")
                lines.append("")
        else:
            lines.append(f"# {DIR_HEADINGS.get(d.name, d.name)}\n")
            for p in files:
                fm, _ = read_frontmatter(p)
                fm = fm or {}
                code = f" ({fm['step_id']})" if fm.get("step_id") and d.name == "steps" else ""
                lines.append(f"* [{fm.get('title')}{code}]({p.name}) - {fm.get('description')}")
            lines.append("")
        (d / "index.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ['---', 'okf_version: "0.2"', '---', '# Documenti\n']
    for p in concepts_in(bundle):
        fm, _ = read_frontmatter(p)
        lines.append(f"* [{(fm or {}).get('title')}]({p.name}) - {(fm or {}).get('description')}")
    lines.append("\n# Cartelle\n")
    for d in sorted(p for p in bundle.iterdir() if p.is_dir()):
        if concepts_in(d):
            lines.append(f"* [{DIR_HEADINGS.get(d.name, d.name.capitalize()) if d.name != 'decisions' else 'Decisioni'}]({d.name}/) - "
                         f"{DIR_DESCRIPTIONS.get(d.name, '')}")
    lines.append("")
    (bundle / "index.md").write_text("\n".join(lines), encoding="utf-8")


def ignored_by_git(bundle):
    """Markdown files of the bundle that git would silently skip (None outside a git repo)."""
    try:
        out = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", str(bundle)],
                             capture_output=True, text=True, check=True).stdout.split("\n")
    except Exception:
        return None
    return [p for p in out if p.endswith(".md") or p.endswith("/")]


def check(bundle):
    build_indexes(bundle)
    n_bad, n_files, warn_codes = 0, 0, set()
    ignored = ignored_by_git(bundle)
    if ignored:
        n_bad += 1
        print(f"FAIL ignored by git (fix .gitignore): {', '.join(ignored)}")
    for p in sorted(pathlib.Path(bundle).rglob("*.md")):
        n_files += 1
        problems, warns = check_file(p, bundle)
        if problems:
            n_bad += 1
            print(f"FAIL {p.relative_to(bundle)}: {'; '.join(problems)}")
        warn_codes.update(w for w in warns if not w.startswith("decision code"))
        for w in warns:
            if w.startswith("decision code"):
                print(f"WARN {p.relative_to(bundle)}: {w}")
    if warn_codes:
        print(f"WARN codes of other registers still unlinked: {', '.join(sorted(warn_codes))}")
    print(f"{n_files} markdown files checked, {n_bad} failing")
    return n_bad


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("check")
    c.add_argument("--bundle", required=True)
    lk = sub.add_parser("link")
    lk.add_argument("--bundle", required=True)
    lk.add_argument("--no-steps", action="store_true")
    lk.add_argument("files", nargs="+")
    a = ap.parse_args()
    if a.mode == "link":
        titles = decision_titles(a.bundle)
        for f in a.files:
            link_file(f, titles, a.bundle, link_steps=not a.no_steps)
        return
    sys.exit(1 if check(a.bundle) else 0)


if __name__ == "__main__":
    main()
