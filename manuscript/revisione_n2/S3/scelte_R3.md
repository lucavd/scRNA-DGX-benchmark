# Scelte del PI della regione R3 (Risultati scRNA, righe 176-323)

Step S3, 4 novembre 2026. Manoscritto all'apertura: md5 4587032be8d2905007687e0bb50d848e (commit fc9c11c).
Ogni numero citato qui ha una ricevuta in `ricevute_R3.csv` o e' un conteggio letto nei file indicati.
In `edits_R3.csv` c'e' il testo dell'opzione raccomandata, con `scelta_pi` = codice.

## Una scoperta che pesa su tre scelte (CAPACITA_LOG, T5_PUNTI, T6)

Il run a 12,0 milioni di cellule con la pipeline memory-optimised **non e' fallito per memoria registrata**.
Il log del job 16531 (`logs/slurm-maxpower_8gpu_16531.out` e `.err`) mostra che QC, normalizzazione, HVG, scaling, PCA e ricerca dei vicini sono terminati.
Poi il processo e' uscito con codice 1 per un `TimeoutError` durante la chiusura del cluster Dask, prima di Leiden.
Le righe "killed by signal 9" del log sono i worker Dask che il nanny uccide durante la chiusura. Per sacct sul DGX il job e' COMPLETED, ExitCode 0:0.
Il 12,0M e' stato tentato una sola volta. Il job successivo (16591) ha usato 12.000.000 come limite superiore noto, e quel valore e' finito in `results/maxpower_limit_8gpu.json` come `first_oom_at`.
I due run a 13,7M (Leiden, job 16463; KMeans, job 16662) sono stati uccisi (codice -9) dopo la selezione HVG, durante la copia in `adata.raw` e il subset, prima dello scaling.
La variante chunked ha completato 12,0M (131.5 min, 861.7 GiB) ed e' stata uccisa a 15,0M (exit 137) durante la conversione CSR-CSC (`logs/slurm-chunked_single_16825.out`).
La variante sparse-scatter e' stata uccisa a 14M durante la selezione HVG (`logs/slurm-memopt_16683.out`, 629.0 GiB dopo la costruzione del dataset).

## CIFRA: cifra di testa scRNA (coordinata con la regione R1)

- **Domanda.** Come si presenta il 119.6x a 1.3M cellule?
- **Prove.** CPU 52,056.2 +/- 392.0 s; 8 GPU 435.2 +/- 16.2 s (119.6x); 2 GPU 493.3 +/- 10.3 s (105.5x). Caricamento dati 149.0 s (2 GPU) contro 90.6 s (8 GPU), su nodi diversi (poddgx03 e poddgx02). Wilcoxon CPU 48,688.3 s, cioe' 93.5% del totale CPU. Senza DE: 9.2x (8 GPU), 7.9x (2 GPU). Fonti: `results/{cpu,gpu2,gpu8}_1300000_r{1..5}_results.json`. Dicks2026 (passaggio letto nel pdf_txt del pacchetto, metadati su arXiv): oltre 120x su B200 e 110x su H200 contro una CPU a 32 core, senza DE e senza I/O.
- **Alternative.** (A, raccomandata, testo di R1 piu' la frase su Dicks2026) in `edits_R3.csv` R3-001. (B) Come A senza la frase su Dicks2026: si toglie l'ultima frase di R3-001; il confronto con Dicks resta solo dove lo mette la Discussione (R4). (C) Solo 119.6x e quota del Wilcoxon, senza il run a 2 GPU: si toglie la seconda frase di R3-001; il 105.5x resta alla riga 185.
- **Raccomandazione.** A. Dice da dove viene il fattore 120 (il Wilcoxon CPU) e lo mette accanto al riferimento esterno piu' vicino.
- **Edit.** R3-001. Il titolo della sottosezione (riga 180, "achieves up to 120-fold") non e' toccato da alcuna voce: va rivisto insieme a CIFRA (vedi anomalie).

## T5_PUNTI: Table 5 con tutti i punti o con una selezione dichiarata

- **Domanda.** Table 5 mostra tutte le 16 dimensioni completate o una selezione dichiarata?
- **Prove.** In `results/` ci sono 16 JSON `maxpower_*_8gpu_results.json` completati, da 1.7M a 11.9M (esclusi chunked e limit). 1.7M e 3.4M (Leiden, 16 marzo) hanno una configurazione diversa: 1.7M ha pool RMM da 10 GB e VRAM 175 GiB, 3.4M e' un sottocampione non replicato con VRAM 75 GiB. Le altre 14 usano pool da 2 GB e la PCA covariance_distributed. I run Leiden a 3.44M, 6.87M e 10.31M del 19 marzo (job 16463) sono stati sovrascritti dai run KMeans del 22 marzo: restano solo nel log. I tempi non crescono in modo monotono (11.5M 114 min, 11.7M 104 min) per via del QC.
- **Alternative.** (A, raccomandata) Selezione dichiarata in didascalia: edit R3-022 ("Rows are a selection of the 16 sizes that completed (1.7M to 11.9M cells); the result files of all of them are in the repository."). Righe invariate salvo le correzioni (R3-024, R3-025, R3-026). (B) Tutti i punti: sostituire le righe 273-279 con la tabella qui sotto e la didascalia di R3-022 con "Memory in GiB. All completed sizes are listed; 1.7M and 3.4M were run with an earlier configuration (Leiden on the source dataset without replication at 3.4M). Above 3.4M cells the input contains replicated cells (see text)." Costo: 11 righe in piu', contro D-03 (circa 15 pagine).

```
| Cells | Runtime (min) | CPU RAM (GiB) | GPU VRAM (GiB) | Clustering | Status |
|------:|--------------:|-------------:|--------------:|:-----------|:-------|
| 1.7M | 12 | 126 | 175 | Leiden | Pass |
| 3.4M | 22 | 167 | 75 | Leiden | Pass |
| 3.44M | 18 | 155 | 49 | KMeans | Pass |
| 6.87M | 38 | 308 | 49 | KMeans | Pass |
| 8.5M | 46 | 379 | 49 | Leiden | Pass |
| 9.4M | 59 | 426 | 49 | Leiden | Pass |
| 9.8M | 64 | 443 | 49 | Leiden | Pass |
| 10.0M | 72 | 452 | 49 | Leiden | Pass |
| 10.1M | 73 | 456 | 49 | Leiden | Pass |
| 10.2M | 69 | 460 | 49 | Leiden | Pass |
| 10.31M | 91 | 465 | 49 | KMeans | Pass |
| 11.1M | 94 | 500 | 49 | Leiden | Pass |
| 11.5M | 114 | 517 | 49 | Leiden | Pass |
| 11.7M | 104 | 526 | 49 | Leiden | Pass |
| 11.8M | 119 | 530 | 49 | Leiden | Pass |
| 11.9M | 119 | 535 | 49 | Leiden | **Pass (max)** |
| 12.0M | --- | --- | --- | Leiden | Fail (Dask shutdown timeout after neighbours) |
| 13.7M | --- | --- | --- | Leiden, KMeans | Fail (killed after HVG selection) |
```

- **Raccomandazione.** A. La tabella resta corta (D-03), e la selezione e' dichiarata e verificabile.
- **Edit.** R3-022.

## T6: Table 6 ricostruita dalla traccia o tolta

- **Domanda.** Table 6 si ricostruisce dalla traccia di 11.9M o si toglie?
- **Prove (previsione P4 di S3).** Residuo per differenza = 534.55 - 426.10 - 88.66 = **19.79 GiB**. Fonte: `results/maxpower_11900000_8gpu_results.json`, md5 0a424b1622e6f22be8e3729e30aedd0e. Chiavi: `memory.peak_ram_gb` 534.55, `memory.detailed.qc_filtering_ram_before_gb` 426.1; matrice densa 11,899,623 x 2,000 x 4 B / 1024^3 = 88.659 GiB. Atteso 19.79 GiB (scarto < 0.01): **confermata**. Il valore e' positivo e sotto 60 GiB, quindi la struttura regge. Inoltre: delta misurato dello scaling +81.71 GiB; delta Leiden +0.48 GiB; nessuna conversione CSC nel codice principale; memoria fisica 2,016 GiB secondo psutil (il 2,048 del testo e' una costante del codice). Pero' il titolo "at the 12M-cell failure point" non regge: il 12.0M non si e' fermato per memoria registrata.
- **Alternative.** (A, raccomandata) Ricostruire con titolo "at 11.9M cells, the largest completed run": edit R3-028 ... R3-040 (righe 283-304). Baseline 426 + 89 + 20 = 535 GiB; transitori +426 (copia raw), +89 (densificazione); Leiden < 1; HVG e worker Dask n.q.; CSC tolta. (B) Togliere Table 6: tutte le righe 283-304 escono (come `vecchio` le righe intere 283, 285, 287-302 e 304, `nuovo` vuoto). In R3-018 si toglie la frase "We report an indicative budget in Table 6. ". Alla fine di R3-018 si aggiunge: "At 11.9M the trace contains one full sparse copy of the replicated matrix (about 426 GiB, the RAM at the start of QC) and the dense scaled HVG matrix (89 GiB), which together account for all but 20 GiB of the 535 GiB recorded." Si risparmia circa mezza pagina (D-03). (C) Ricostruire solo la parte misurata (baseline e subtotale) e togliere i transitori stimati: in A si tolgono R3-035, R3-036 e le righe 293, 298, 299, 300; resta la nota della riga 304 sulle quantita' non misurate.
- **Raccomandazione.** A, perche' la P4 e' confermata e la tabella mostra quanto della memoria e' misurato e quanto stimato. Se il PI deve tagliare per D-03, B e' il taglio piu' pulito.
- **Edit.** R3-028, R3-029, R3-030, R3-031, R3-032, R3-033, R3-034, R3-035, R3-036, R3-037, R3-038, R3-039, R3-040.

## KMEANS: righe KMeans in Table 5

- **Domanda.** Le tre righe KMeans (3.44M, 6.87M, 10.31M) restano in Table 5?
- **Prove.** A circa 10M cellule il picco di RAM e' simile: 465.4 GiB con KMeans (10.31M), 460.5 GiB con Leiden (10.2M). I tempi no: 91.5 contro 69.2 min, con il QC a 3,156 contro 2,218 s, run in giorni diversi (22 e 17 marzo). Il run KMeans a 13.7M esiste (log 16662) ed e' stato ucciso come quello Leiden.
- **Alternative.** (A, raccomandata) Tenerle con la frase di R0166, edit R3-027. (B) Sostituirle con righe Leiden della stessa configurazione, per esempio 8.5M (46 min, 379 GiB), 9.4M (59, 426) e 10.2M (69, 460), tutte con VRAM 49 GiB: righe 273-275 sostituite, riga 281 tolta, riga 264 invariata (R3-019). La tabella diventa una sola serie, ma perde la parte bassa (3.4M-6.9M). (C) Toglierle senza sostituirle: righe 273-275 e 281 tolte.
- **Raccomandazione.** A: tiene i punti bassi della curva di memoria e dice chiaramente che i tempi vengono da due serie.
- **Edit.** R3-027.

## CAPACITA_LOG: frase sul limite di capacita'

- **Domanda.** I log dei run a 13.7M, 14M e 15M mancano?
- **Prove.** No, ci sono tutti: sul server in `logs/` (158 file) e sul DGX in `/mnt/projects/dctv/dgx/u0044/sc-gpu-benchmark/logs/` (214 file; 16843, 16696 e 16803 solo sul DGX). La scelta come era formulata decade. Ne nasce un'altra, sul fallimento a 12.0M (vedi sopra).
- **Alternative per abstract (riga 14, R1) e Discussione (riga 424, R4).** (A, raccomandata) "the memory-optimised pipeline completed 11.9 million cells; the single run at 12.0 million cells stopped with a Dask shutdown timeout and runs at 13.7 million cells were killed during CPU preprocessing; a chunked variant completed 12.0 million cells". Niente "CPU RAM is the binding constraint" come fatto dimostrato: al massimo "consistent with CPU-side memory pressure", per i kill a 13.7M, 14M e 15M. (B) Tenere "CPU RAM as the binding constraint" e dire che il 12.0M non e' attribuito. (C) Ripetere il 12.0M sul DGX: e' un nuovo run, fuori dalle decisioni (nessun job in S3).
- **Raccomandazione.** A: e' quello che i log dicono.
- **Edit nella regione.** Nessuno dipende dalla scelta. R3-017, R3-018, R3-019, R3-020, R3-021, R3-025 e R3-026 riportano i fatti dei log (istruzioni di R0142, R0143, R0153, R0154, R0156, R0164, R0165).

## CONC_INTERCAMB: "interchangeable" (R0498, gruppo J06)

- **Domanda.** Indebolire "interchangeable" o ricalcolare la concordanza a tutte le dimensioni?
- **Prove.** A 10k le etichette sono identiche nelle 5 ripetizioni sia su CPU sia su GPU. Da 50k in su le etichette GPU cambiano fra le ripetizioni ad almeno una risoluzione (da 2 a 4 partizioni distinte), quelle CPU mai (hash in `results/*_results.json`). Gardner2025 (passaggio letto, metadati Crossref): ARI CPU-GPU circa 0.5 sul dataset da 1.3M e sui sottocampioni, e "not interchangeable".
- **Costo del ricalcolo (stima, non eseguito).** Le uscite per il confronto esistono gia' per tutte le dimensioni (`*_clusters.csv`, `*_hvgs.csv`, `*_pca_loadings.csv`, `*_de.csv`). I `*_knn.npz` ci sono per CPU e per 1 GPU fino a 100k, non per gpu2/4/8 a 500k e 1.3M. `scripts/compare_results.py` su queste uscite e' solo CPU, nessun run nuovo: stimo meno di 30 minuti su un core (i CSV dei cluster a 100k pesano 1.5 MB; a 1.3M circa 20 MB). Conseguenze: nuovi numeri in Fig. 5 (S4), alle righe 240-244 e in Discussione; la Jaccard dei vicini a 500k e 1.3M resta non calcolabile.
- **Alternative.** (A, raccomandata) Indebolire: edit R3-014. (B) Ricalcolare a tutte le dimensioni (costo sopra), poi riscrivere le righe 240-244 con le nuove tabelle. (C) Tenere "interchangeable": contraddetto dai dati da 50k in su, sconsigliato.
- **Raccomandazione.** A: non chiede calcoli e dice cio' che i dati sostengono.
- **Edit.** R3-014.

## CONC_11MARZO: concordanza dal run dell'11 marzo (frase dei Risultati; la frase dei Metodi e' della regione R2)

- **Domanda.** Dichiarare che la concordanza viene dal run separato dell'11 marzo o ricalcolarla sui run cronometrati?
- **Prove.** `results/concordance_10000_r1.json`: cpu_timestamp 2026-03-11T23:14:30Z, gpu_timestamp 23:15:03Z, cioe' 12 marzo 00:14 CET; ripetizioni cronometrate dal 12 marzo (CPU) e dal 15 marzo (GPU). Cluster CPU in quel run: 31, 40, 45; in tutte e 5 le ripetizioni cronometrate: 31, 41, 46. GPU: 32, 40, 45 in entrambi.
- **Alternative.** (A, raccomandata) Dichiarare: prima frase aggiunta in R3-012 ("made on 11 March 2026 (UTC), before the timed benchmark"). Per coerenza R2 scrive la stessa data, con "(UTC)". (B) Ricalcolare sulla coppia r1 dei run cronometrati (uscite presenti a 10k; pochi minuti di CPU). Cambiano i numeri di Fig. 5 e delle righe 240-242, con una nuova ricevuta per ciascuno.
- **Raccomandazione.** A.
- **Edit.** R3-012 (insieme a JACCARD).

## JACCARD: Jaccard dei vicini riformulata o ricalcolata senza la cella stessa

- **Domanda.** Basta dichiarare il tetto 15/16 o si ricalcola?
- **Prove (ricalcolo leggero eseguito, circa 5 s, dai `results/{cpu,gpu}_10000_r{1..5}_knn.npz`).** Le liste salvate dei vicini sono identiche nelle 5 ripetizioni. CPU: 16 indici per cella, GPU: 15, in entrambe la cella stessa compresa. Jaccard con la cella: media 0.9304, mediana e massimo 0.9375 (riproduce la concordanza dell'11 marzo). Senza la cella: media 0.9258, massimo 14/15 = 0.9333 (il tetto resta, perche' le cardinalita' restano diverse). Inclusione: per il 95.0% delle celle tutti i vicini GPU sono anche vicini CPU; in media il 99.6% dei vicini GPU e' fra quelli CPU. Attenzione: questi valori vengono dai run cronometrati, non dal run dell'11 marzo.
- **Alternative.** (A) Solo la riformulazione di R0371 (tetto 15/16): in R3-012 togliere la frase "In the saved neighbour lists ... CPU neighbour. ". (B, raccomandata) A piu' la frase sull'inclusione (95.0%): testo in R3-012. (C) Sostituire la Jaccard con la Jaccard senza la cella (0.926): sconsigliato, il tetto resta (14/15) e il numero non e' piu' informativo.
- **Raccomandazione.** B: e' la misura che dice quanto i vicini coincidono davvero, senza l'effetto della cardinalita'.
- **Edit.** R3-012.

## HVG_CAP: capacita' in funzione degli HVG (frase della Discussione, riga 424, regione R4, voce R0601)

- **Domanda.** Si tiene la stima "20M cells at 1,000 HVGs and 4M cells at 5,000 HVGs"?
- **Prove.** A 11.9M la matrice densa HVG vale 88.66 GiB, il 16.6% del picco di 534.55 GiB. Il 17.8% della revisione mescola GB e GiB (95.2 GB su 534.55 GiB). Modello inversamente proporzionale agli HVG: 23.8M (1,000 HVG) e 4.76M (5,000). Modello a bilancio (40,234 B per cella fuori dagli HVG, stesso picco come limite): 12.98M e 9.53M. Nessuno dei due da' 20M e 4M. Il limite stesso e' incerto, perche' il 12.0M non si e' fermato per memoria.
- **Alternative.** (A, raccomandata) Togliere la frase (istruzione di R0601). (B) "the dense HVG matrix accounted for 17% of the recorded peak at 11.9M cells, so halving the number of HVGs or increasing it 2.5-fold would shift capacity only moderately (an estimated 13M and 9.5M cells under a fixed memory budget)".
- **Raccomandazione.** A: la stima poggia su un limite di memoria che i log non confermano.
- **Edit nella regione.** Nessuno (riga 424 della regione R4).
