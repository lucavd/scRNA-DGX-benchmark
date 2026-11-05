# Scelte del PI della regione R1 (fronte e Introduction)

Step S3 «correzioni di sostanza», 4 novembre 2026. Manoscritto di riferimento `manuscript/full_paper_LNBI.md` (md5 4587032be8d2905007687e0bb50d848e). Ogni numero qui sotto è riletto da script (`valori_R1.py`, ricevute in `ricevute_R1.csv`); convenzione D-15 (media e SD campionaria di r1-r5, speedup = rapporto fra medie).

In `edits_R1.csv` c'è il testo dell'opzione raccomandata, con `scelta_pi` uguale al codice. Le alternative sono qui, con il testo pronto.

## TITOLO (voci R0730, R0001; assorbite R0253, R0559)

**Domanda.** Quale titolo nuovo, diverso da quello dello short paper, senza "systematic" e "scalability", con l'hardware per modalità oppure senza hardware?

**Prove.** Il titolo attuale (riga 2) è identico a quello dello short paper (`manuscript_short_cameraready.md` riga 1) e attribuisce al DGX H100 anche lo spatial. I JSON dicono: scRNA su `NVIDIA H100 80GB HBM3` (`results/gpu8_1300000_r1_results.json`), GPU spatial `NVIDIA GeForce RTX 4090` (`SPATIAL/results/spatial_gpu_visium_r1_results.json`); CPU di riferimento a 100 CPU in entrambe le modalità (`metadata.n_cpus` = 100 in `results/cpu_1300000_r1_results.json` e in `SPATIAL/results_v2/dgx_cpu/...`).

| opzione | titolo | parole | difflib con lo short paper |
|---|---|---|---|
| A (raccomandata) | GPU-accelerated single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics: per-step speedups, capacity and concordance against a 100-CPU reference | 19 | 0.590 |
| B | How much do GPUs accelerate single-cell and spatial transcriptomics? Benchmarking rapids-singlecell against Scanpy and Squidpy on a common CPU reference | 20 | 0.567 |
| C | GPU acceleration of single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics against a common 100-CPU reference: speed, capacity and concordance | 21 | 0.605 |

Conseguenze. A: tiene l'attacco dello short paper (il legame resta riconoscibile, come chiede la regola CIBB di un titolo "leggermente diverso"), mette l'hardware per modalità e nomina ciò che il capitolo misura. B: nessun hardware, forma a domanda; nomina i tre pacchetti ma è il più lontano dallo short paper per tono. C: come A, ma "common 100-CPU reference" è un po' più forte del vero (le due CPU di riferimento sono allocazioni da 100 CPU di nodi DGX H100, non necessariamente lo stesso nodo).

**Raccomandazione: A**, perché risolve l'attribuzione dello spatial, toglie le due parole escluse e resta vicino allo short paper senza coincidere. Modifica che ne dipende: R1-001.

**Revisione del 4 novembre 2026 (correzione dalla regione R3).** I log SLURM del DGX mostrano che il run a 12,000,000 cellule della pipeline memory-optimised (job 16531, sacct COMPLETED 0:0) si e' fermato con `TimeoutError` dopo la ricerca dei vicini (sottoprocesso con exit code 1), e che i due run a 13,745,880 cellule (job 16463 con Leiden e 16662 con KMeans) sono stati uccisi con codice -9 dopo la selezione degli HVG, senza messaggio di out-of-memory. 'limited by host memory' non e' quindi dimostrato: gli abstract dicono solo che i run piu' grandi si sono fermati a un time-out di Dask o sono stati uccisi durante la pre-elaborazione su CPU (C: 'before clustering'). Per lo stesso motivo il titolo dice 'capacity' invece di 'memory limits', la domanda sulla capacita' (riga 41) chiede dove si fermano i run piu' grandi e non quale risorsa li limita, e la frase di contributo di NOVITA parla della dimensione massima completata. Una variante chunked ha completato 12,000,000 cellule (results/maxpower_chunked_12000000_8gpu_results.json): spetta alla regione R3 dirlo nei Risultati.

## ABSTRACT (voce R0731 e voci di frase R0007, R0240/R0638, R0565, R0566, R0567, R0568, R0639)

**Domanda.** Quale abstract nuovo (150-250 parole, nessuna frase uguale allo short paper)?

**Prove.** Abstract attuale = short paper, 246 parole contate dallo stesso script (9 frasi su 9 identiche). Valori riletti: CPU 52,056.21 s, GPU 8 435.18 s, 119.62x; GPU 2 105.53x; Wilcoxon 93.53% del tempo CPU; senza DE 7.92x (2 GPU) e 9.23x (8 GPU) (`results/*_1300000_r1..5_results.json`); ARI 0.907733-0.963095 a 10,000 cellule (`results/concordance_10000_r1.json`); 11.9M da 3,436,470 cellule sorgente (`maxpower_limit_8gpu.json`, `maxpower_11900000_8gpu_results.json`); DE pseudo-bulk 127.47 s contro t-test CPU 5,597.79 s su 3,399,892 cellule (`de_benchmark_*.json`); spatial con CPU `reference_dgx`, convenzione `1_5`: Visium v1 1.414x, HD 8 um senza co-occorrenza 6.869x, HD 2 um 10.426x (`s1_speedups.csv`, `s1_extra_numbers.json`); co-occorrenza HD 8 um con rsc 0.14.1 diversa dalla CPU a 41 distanze su 49, con 0.15.1 uguale a 49 su 49, rapporto dei tempi 0.983 [0.951; 1.004] (`s1_extra_numbers.json`, `cooc_check/cooc_check_eval.json`).

### Opzione A (raccomandata): abstract completo, centrato sulla scomposizione e sull'estensione spatial

Single-cell and spatial transcriptomics now yield millions of cells or bins, yet standard frameworks run on CPUs. We compared rapids-singlecell on NVIDIA H100 GPUs with Scanpy on 100 logical CPUs of a DGX H100 node, on 10,000 to 1.3 million mouse brain cells sampled from CELLxGENE Census, five repeats each. At 1.3 million cells the GPU pipeline took 435 s against 52,056 s on CPU (119.6-fold; 105.5-fold with two GPUs allocated, a difference due to data loading alone). Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold. Additional GPUs did no computation in this configuration. At 10,000 cells, HVG selection was identical and Leiden clusterings agreed with ARI 0.908-0.963. A memory-optimised pipeline completed 11.9 million cells, built from copies of a 3,436,470-cell dataset; larger runs stopped at a Dask time-out or were killed in CPU preprocessing. At 3.4 million cells, pseudo-bulk differential expression took 127 s against 5,598 s for a cell-level t-test. For spatial data we rebuilt the CPU reference: one fresh process per repeat, the same cell groups for CPU and GPU. Against 100 CPUs of a DGX H100 node, an RTX 4090 accelerated end-to-end analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occurrence) and 10.4-fold on Visium HD 2 um. At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances through 32-bit integer overflow; version 0.15.1 matched the CPU at all 49 in the same time.

Parole (script, split su spazi): **247**; massima somiglianza difflib di una frase con lo short paper: 0.536; nessuna frase identica.

### Opzione B: abstract a domanda, più corto (senza i tempi del DE a 3.4 milioni)

How much of a GPU speedup in single-cell analysis comes from the GPU itself, and how much from the steps that stay on the CPU? We timed Scanpy on 100 logical CPUs and rapids-singlecell on NVIDIA H100 GPUs of a DGX H100 node, from 10,000 to 1.3 million mouse brain cells sampled from CELLxGENE Census, with five repeats per configuration. At 1.3 million cells the CPU took 52,056 s and the GPU 435 s, a 119.6-fold speedup, but Wilcoxon differential expression was 93.5% of the CPU time: without it the speedup fell to 7.9-9.2-fold. Data-loading time, not the number of GPUs allocated, separated the two- and eight-GPU runs (105.5-fold and 119.6-fold). At 10,000 cells HVG selection was identical and Leiden clusterings agreed with ARI 0.908-0.963. A memory-optimised pipeline completed 11.9 million cells, built from copies of a 3,436,470-cell dataset; larger runs stopped at a Dask time-out or were killed during CPU-side preprocessing. For spatial transcriptomics we rebuilt the CPU reference so that every repeat runs in a fresh process with the same cell groups as the GPU. Against 100 CPUs of a DGX H100 node, an RTX 4090 was 1.4-fold faster on Visium v1, 6.9-fold on Visium HD 8 um without co-occurrence and 10.4-fold on Visium HD 2 um, and GPU co-occurrence in rapids-singlecell 0.14.1 proved wrong at Visium HD 8 um through 32-bit integer overflow, which version 0.15.1 corrects.

Parole (script, split su spazi): **230**; massima somiglianza difflib di una frase con lo short paper: 0.443; nessuna frase identica.

### Opzione C: abstract che apre con l'estensione rispetto allo short paper

This chapter extends a GPU benchmark of single-cell and spatial transcriptomics with a rebuilt spatial CPU reference and a decomposition of the single-cell speedup. On a DGX H100 node we compared Scanpy on 100 logical CPUs with rapids-singlecell on H100 GPUs, on 10,000 to 1.3 million mouse brain cells from CELLxGENE Census, five repeats each. The full pipeline ran 119.6 times faster on GPU at 1.3 million cells (435 s against 52,056 s), but 93.5% of the CPU time was Wilcoxon differential expression, and the speedup without it was 7.9-9.2-fold. Allocating eight rather than two GPUs changed only data loading. At 10,000 cells, HVG sets were identical and Leiden clusterings agreed with ARI 0.908-0.963. Pseudo-bulk differential expression at 3.4 million cells finished 44 times sooner than a cell-level t-test, and a memory-optimised pipeline completed 11.9 million partly duplicated cells on one node, while larger runs stopped before clustering. For spatial data, every CPU and GPU repeat ran in a fresh process with shared cell groups, against 100 CPUs of a DGX H100 node. An RTX 4090 accelerated the analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um without co-occurrence and 10.4-fold on Visium HD 2 um. GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances at Visium HD 8 um because of integer overflow; version 0.15.1 fixed it at no cost in time.

Parole (script, split su spazi): **228**; massima somiglianza difflib di una frase con lo short paper: 0.434; nessuna frase identica.

Conseguenze. A: contiene ogni risultato che oggi è nell'abstract, corretto, più l'estensione; è a 247 parole, quindi le correzioni di stile di S6 non possono aggiungere parole. B: lascia margine (230) ma toglie il benchmark del DE e il conteggio 41/49; la domanda iniziale rende esplicita la tesi. C: dichiara subito l'estensione (utile per l'ammissibilità del capitolo) e dice "partly duplicated cells" invece della dimensione della sorgente.

**Raccomandazione: A**, perché recepisce tutte le voci di frase senza togliere risultati e dà al DE il formato di confronto di tempi chiesto da D-04 (127 s contro 5,598 s). In tutte e tre le opzioni la piattaforma "Visium HD 2 um" va rinominata se in S5 il PI decide di dichiarare il sottocampione di 400.000 bin. Modifica che ne dipende: R1-002.

## CIFRA (cifra di testa scRNA; vale anche per Risultati, Discussione e Conclusioni)

**Domanda.** Come si riporta lo speedup a 1.3 milioni di cellule: 119.6x da solo, o con il run a 2 GPU, la quota del Wilcoxon e lo speedup senza espressione differenziale?

**Prove.** Medie r1-r5 (D-15): CPU 52,056.2 +/- 392.0 s; 8 GPU 435.2 +/- 16.2 s (119.6x); 2 GPU 493.3 +/- 10.3 s (105.5x); 4 GPU 107.0x. Fra 2 e 8 GPU solo il caricamento dati differisce oltre 2 SD (149.0 +/- 20.8 contro 90.6 +/- 5.0 s, differenza 58.4 s contro 2 SD = 41.5 s, con la SD maggiore, 20.77 s; `results_v2/S3/evidence/data_loading_1300000_gpu2_gpu8_sd.txt`); ogni altro step differisce meno di 2 SD (PCA+vicini su GPU 0, D-02). Wilcoxon = 93.5% del tempo CPU; senza DE 7.9x (2 GPU), 8.1x (4 GPU), 9.2x (8 GPU).

### Opzione A (raccomandata): 119.6x con il run a 2 GPU e la scomposizione

Formulazione per i Risultati (riga 183, regione R3):

> At 1.3 million cells, the GPU pipeline with eight GPUs allocated completed the full analysis in 435.2 +/- 16.2 s (7.3 min), compared with 52,056.2 +/- 392.0 s (14.5 h) for the CPU pipeline, a 119.6-fold speedup. With two GPUs allocated the time was 493.3 +/- 10.3 s (105.5-fold); the difference lies in data loading (149.0 against 90.6 s, runs on different nodes), because the additional GPUs did not take part in the computation. Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-fold with two GPUs and 9.2-fold with eight.

Formulazione breve per abstract (già in R1-002), Discussione e Conclusioni (righe 420 e 436, regione R4):

> At 1.3 million cells the GPU pipeline was 119.6 times faster than the CPU (105.5 times in the two-GPU run, which differed only in data loading), and 93.5% of the CPU time was Wilcoxon differential expression; without it the speedup was 7.9-9.2-fold.

### Opzione B: 119.6x da solo, con la quota del Wilcoxon

> At 1.3 million cells, the GPU pipeline completed the full analysis in 435.2 +/- 16.2 s (7.3 min), compared with 52,056.2 +/- 392.0 s (14.5 h) for the CPU pipeline, a 119.6-fold speedup. Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold.

Conseguenza: più corta, ma lascia al lettore l'idea che le 8 GPU contino (D-02 dice che non hanno calcolato).

### Opzione C: in testa lo speedup senza espressione differenziale

> Without differential expression, the GPU pipeline was 7.9 to 9.2 times faster than the CPU at 1.3 million cells. Including Wilcoxon differential expression, which took 93.5% of the CPU time, the full pipeline took 435.2 +/- 16.2 s against 52,056.2 +/- 392.0 s, a 119.6-fold speedup (105.5-fold in the two-GPU run, which differed only in data loading).

Conseguenza: la cifra di testa diventa 7.9-9.2x; è la lettura più prudente, ma sposta l'enfasi del capitolo e richiede di riscrivere anche titolo e Conclusioni in quel senso.

**Raccomandazione: A.** Riporta il valore misurato secondo D-15, e insieme le due ragioni per cui non va letto come effetto delle 8 GPU né come accelerazione uniforme della pipeline. Le altre regioni usano le due formulazioni sopra parola per parola (i numeri sono nelle ricevute R1-V005...R1-V012 e R1-V051...R1-V061). Modifica che ne dipende: R1-002 (abstract).

## NOVITA (voci R0538, R0020, R0732)

**Domanda.** Che cosa dichiara il capitolo come nuovo rispetto alla letteratura (riga 34) e rispetto allo short paper (frase di estensione)?

**Prove** (lette in sessione). Nolet2022: Table 1 con tempi per step su 40 CPU e su 1-8 V100, concordanza CPU-GPU a 1.3 milioni (PCA |r| >= 0.999, vicini conservati 95.66%, ARI 0.54) (testo estratto nel pacchetto, `tracks/E_work/pdf_txt/2022.05.26.493607v1.full.txt`). Gardner2025: H100 80 GB, 50,000-1.2M cellule, "median ARI between 0.45 and 0.55", "not interchangeable" (`3731599.3767378.txt`). Hu2025 (full text da Unpaywall): dataset di 13 milioni di cellule **simulato** dalle distribuzioni per cluster del dataset da 1.3 milioni, su una sola A100 (non "replicato" come nella proposta del piano). Dicks2026: tempi per step su B200, H200 e RTX PRO 6000; Tahoe-100M in meno di 20 minuti su un nodo con 8 GPU (`2603.02402v1.txt`). Con D-02 il punto (ii) multi-GPU non è più un contributo.

### Opzione A: gap statement del piano (con Hu2025 corretto)

Riga 34:

> Earlier studies have reported per-step timings on one to eight GPUs with CPU-GPU concordance [@Nolet2022], accuracy-performance trade-offs on NVIDIA H100 GPUs [@Gardner2025], a simulated 13-million-cell dataset processed on one A100 GPU [@Hu2025] and 100 million cells analysed on a node with eight GPUs [@Dicks2026].

Riga 35:

> Gardner et al. [-@Gardner2025] also found that CPU and GPU pipelines were not interchangeable (median ARI 0.45-0.55).
Less is known about how much of an end-to-end speedup comes from single steps such as differential expression testing, how many cells a hybrid CPU-GPU pipeline can complete on one node, and how GPU spatial analyses compare with a matched CPU reference.

Conseguenza: afferma che "less is known" su tre aspetti; Nolet2022 e Dicks2026 riportano già tempi per step, quindi la frase va difesa davanti al revisore.

### Opzione B (raccomandata): elenco dei lavori precedenti e contributo dichiarato come complemento

Riga 34 (R1-007):

> Earlier studies have reported per-step timings on one to eight GPUs with CPU-GPU concordance [@Nolet2022], a simulated 13-million-cell dataset processed on one A100 GPU [@Hu2025] and 100 million cells analysed on a node with eight GPUs [@Dicks2026].

Riga 35 (R1-008):

> Gardner et al. [-@Gardner2025] evaluated accuracy-performance trade-offs on NVIDIA H100 GPUs and found that CPU and GPU pipelines were not interchangeable (median ARI 0.45-0.55).
We complement these studies with three analyses: the share of the end-to-end speedup due to differential expression testing on one DGX H100 node, the largest cell count that a hybrid CPU-GPU pipeline completed on that node and where larger runs stopped, and a spatial benchmark of an RTX 4090 against a matched CPU reference.

Conseguenza: non afferma lacune nella letteratura, dice solo che cosa aggiunge questo capitolo; ogni elemento è sostenuto da una sezione dei Risultati (scomposizione del DE, stress test, benchmark spatial).

### Opzione C: nessuna dichiarazione di novità rispetto alla letteratura

Riga 34: tolta per intero. Riga 35:

> Gardner et al. [-@Gardner2025] evaluated accuracy-performance trade-offs on NVIDIA H100 GPUs and found that CPU and GPU pipelines were not interchangeable (median ARI 0.45-0.55).

Conseguenza: l'Introduzione passa dai lavori precedenti alle domande senza dire che cosa aggiunge; la differenza la fanno solo le domande e la frase di estensione.

### Frase di estensione rispetto allo short paper (R0732, riga 44, R1-015)

Versione raccomandata (terza frase di R1-015):

> This chapter extends our CIBB 2026 short paper with a new CPU reference for the spatial benchmark, in which every repeat runs in a fresh process and CPU and GPU spatial statistics use the same cell groups; the new reference removes a slowdown of the CPU between repeats of the original spatial runs and shows that GPU co-occurrence at Visium HD 8 um was wrong because of 32-bit integer overflow, an error that rapids-singlecell 0.15.1 corrects.

Versione corta alternativa:

> This chapter extends our CIBB 2026 short paper with a new CPU reference for the spatial benchmark and reports an integer-overflow error in GPU co-occurrence at Visium HD 8 um, which rapids-singlecell 0.15.1 corrects.

Nota: la proposta del piano diceva "corrects a thread-count defect in the original CPU timings". La frase vale solo per lo spatial (il rallentamento della CPU fra ripetizioni di marzo, S1); i tempi CPU scRNA non sono stati corretti (D-16 li tiene e dichiara pynndescent a `n_jobs = 1`). Per questo il testo dice "between repeats of the original spatial runs".

**Raccomandazione: B con la frase di estensione lunga.** Modifiche che ne dipendono: R1-007, R1-008, R1-015.

## DOMANDE (righe 37-42; voci R0240, R0022, R0538)

**Domanda.** Dopo D-02 (nessun calcolo distribuito sulle GPU aggiuntive) le domande di ricerca restano cinque con la seconda riscritta, o diventano quattro?

**Prove.** PCA+vicini a 1.3M: 17.23, 16.99 e 17.01 s con 2, 4 e 8 GPU (medie r1-r5 di `pca` + `neighbors` dai JSON gpu2/gpu4/gpu8); dai JSON ogni step fuori dal caricamento differisce meno di 2 SD fra 2 e 8 GPU (vedi CIFRA).

### Opzione A (raccomandata): quattro domande

- riga 37 (R1-009): "Here we address four questions."
- riga 38 (R1-010, indipendente dalla scelta): tolto "on identical hardware".
- riga 39 (R1-011): tolta per intero.
- riga 40 (R1-012): "Third" diventa "Second".
- riga 41 (R1-013): "Third, capacity: how many cells can the hybrid pipeline complete on one DGX H100 node, and where do larger runs stop?"
- riga 42 (R1-014): "Fifth" diventa "Fourth".

### Opzione B: cinque domande, la seconda riscritta

- riga 37: "Here we address five questions."
- riga 39: "Second, multi-GPU allocation: does allocating more GPUs of the node change runtime in the configuration used?"
- riga 40: invariata ("Third, concordance: ...").
- riga 41: "Fourth, capacity: how many cells can the hybrid pipeline complete on one DGX H100 node, and where do larger runs stop?"
- riga 42: invariata.

Conseguenza: B tiene una domanda la cui risposta è "no, per costruzione della configurazione", che D-02 riduce a un paragrafo; A è coerente con il taglio delle figure multi-GPU.

**Raccomandazione: A.** Modifiche che ne dipendono: R1-009, R1-011, R1-012, R1-013, R1-014.

## HCA (riga 23; voce R0472, assorbita R0014)

**Domanda.** Come si cita lo Human Cell Atlas, visto che Regev2017 è il white paper di un progetto e non riporta dataset?

**Prove** (abstract Crossref letti in sessione). Tabula Sapiens: "nearly 500,000 cells from 24 different tissues and organs". Yao2023: scRNA-seq di circa 7 milioni di cellule (circa 4.0 milioni dopo il QC) e MERFISH di circa 4.3 milioni; la piattaforma si chiama "Allen Brain Cell Atlas". Regev2017: l'HCA "aims to define all human cell types". La proposta del piano ("plans to extend such maps to all human tissues") non è la parafrasi più vicina: il testo usa "define all human cell types".

### Opzione A (raccomandata): HCA come obiettivo, con Regev2017

> Atlas-scale projects such as Tabula Sapiens [@TabulaSapiens2022] and the Allen Brain Cell Atlas of the whole mouse brain [@Yao2023] have produced datasets of hundreds of thousands to millions of cells, placing severe computational demands on analysis pipelines; the Human Cell Atlas aims to define all human cell types [@Regev2017].

### Opzione B: HCA tolto

> Atlas-scale projects such as Tabula Sapiens [@TabulaSapiens2022] and the Allen Brain Cell Atlas of the whole mouse brain [@Yao2023] have produced datasets of hundreds of thousands to millions of cells, placing severe computational demands on analysis pipelines.

Conseguenza: Regev2017 resta citato solo alla riga 441, che S6 toglie (R0716); la voce del .bib resta comunque.

### Opzione C: HCA fra i progetti che producono dati

Richiede la citazione di un dataset o del portale HCA, che in questa sessione non è stata letta: non si può scrivere ora (regola 5).

**Raccomandazione: A.** Modifica che ne dipende: R1-004.

## PADOVA (affiliazioni e parti finali)

**Domanda.** "University of Padova, Padova" o "University of Padua, Padua"?

**Prove.** Nel manoscritto "Padova" alle righe 8, 10, 154 e 451, "Padua" alle righe 12 e 455 (R0717). Lo short paper usa "Padova" per le affiliazioni 1 e 2 e "Padua" per la 3. Entrambe le forme inglesi sono in uso per l'ateneo (Wikidata usa "University of Padua" con alias "University of Padova").

- **A (raccomandata): "Padova" ovunque.** Riga 12: "^3^ Neuromuscular Unit, Department of Neuroscience, University of Padova, Padova, Italy"; riga 455 (R4): "University of Padova". È la forma già prevalente nel testo e nell'affiliazione del corresponding author.
- B: "Padua" ovunque (righe 8, 10, 12, 154, 451, 455, comprese le città). Cambia anche l'affiliazione del primo autore rispetto allo short paper.
- C: lasciare le forme come sono (ogni autore la sua). Il volume LNBI avrebbe due nomi per lo stesso ateneo.

Nessuna modifica in `edits_R1.csv`: la riga 12 è della voce R0717, assegnata a S6 (regola 8). Con l'opzione A, la regione R4 sostituisce "University of Padua" alla riga 455 e S6 applica il testo sopra alla riga 12.
