---
type: Overview
title: "Il capitolo LNBI sul benchmark GPU contro CPU"
description: "Cosa stiamo facendo, dove sta il materiale e come si legge questa documentazione."
status: stable
generated: { by: lnbi-agent/skill-v1, at: 2026-11-03T11:00:00+01:00 }
sources:
  - id: prompt
    resource: "git:main:manuscript/revisione_n2/PROMPT_claude_science.md"
    title: "Prompt di partenza del PI, 3 novembre 2026"
  - id: rev2
    resource: "git:main:manuscript/revisione_n2/revisione_n2_report.md"
    title: "Revisione n.2 del capitolo, 3 novembre 2026"
---
# Cosa stiamo facendo

Portiamo alla sottomissione su Springer METEOR, entro il 10 novembre 2026, il capitolo LNBI esteso dello short paper CIBB 2026 sul benchmark GPU contro CPU. Il lato scRNA-seq usa rapids-singlecell su DGX H100, il lato spatial Squidpy su RTX 4090. Il punto di partenza sono i problemi trovati dalla revisione n.2 del 3 novembre[^rev2]. Il protocollo di lavoro è la skill di progetto `lnbi-scrna-dgx-session`; il mandato del PI è il prompt di partenza[^prompt].

# Dove sta il materiale

- Repo di lavoro: `/mnt/wwn-0x5000039d58caca35/2026.scRNA_DGX` su `ssh:lesexp-server` ([Si lavora solo sul server (D-07)](decisions/D-07.md)).
- Manoscritto: `manuscript/full_paper_LNBI.md`. Revisione n.2: `manuscript/revisione_n2/`.
- Risultati grezzi in sola lettura: `results/` e `SPATIAL/results/`, controllati con `manifests/raw_results_md5_2026-11-03.tsv` ([Integrità dei risultati grezzi con un manifest md5 (D-08)](decisions/D-08.md)).

# Come si legge

Le [decisioni](decisions/index.md) sono una per file. Gli [step](steps/index.md) hanno un file ciascuno, con attese e riassunto. Il [registro](log.md) elenca le modifiche per data.

[^prompt]: Prompt di partenza del PI, 3 novembre 2026.
[^rev2]: Revisione n.2 del capitolo, 3 novembre 2026.
