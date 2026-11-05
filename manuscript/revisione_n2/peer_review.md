# Track F: Discussione e peer-review sulla letteratura

Manoscritto: `full_paper_LNBI.md` (LNBI, CIBB 2026). Dati: `/tmp/repo` commit a4b9b9e, sola lettura.
Codice e tabelle di questo track: `tracks/F_work/` (f00-f05, CSV di output). Esiti riga per riga: `tracks/F_findings.json` (115 voci: 79 dell'inventario, 6 frasi fuori inventario, 15 punti nascosti, 15 PoW).

Convenzioni usate in tutto il track: media aritmetica sulle ripetizioni indicate; SD campionaria (ddof = 1, coincide con Table 4); speedup = media CPU / media GPU; "rep2-5" = convenzione dichiarata per lo spatial, "rep1-5" = convenzione dichiarata per lo scRNA.

## 0. In breve

1. **Lo "scaling multi-GPU" non e' stato misurato.** Nella pipeline ibrida `adata.X` resta un array CuPy su GPU 0: in rapids-singlecell 0.14.1 `pp.pca` usa Dask solo se X e' un `DaskArray` e `pp.neighbors` non ha un ramo Dask. I tempi di PCA + neighbours sono identici con 2, 4 e 8 GPU (1.3M: 17.23 / 16.99 / 17.01 s). Il "12%" tra 2 e 8 GPU a 1.3M sta tutto nel data loading su CPU (149.0 contro 90.6 s), misurato su nodi diversi (driver 535.247.01 contro 535.183.01) e con job concorrenti. L'argomento della Results l252 (VRAM aggregata > 80 GB, quindi distribuzione) misura i pool RMM da 10 GB dei worker Dask inattivi.
2. **Le cifre di testa dello spatial dipendono dall'esclusione della ripetizione 1.** La giustificazione e' il warmup JIT, ma nella rep1 la CPU e' stata piu' veloce: co-occurrence HD 8 um 73.5 s contro circa 3,573 s nelle rep2-5, con output identico bit a bit. Con tutte le ripetizioni lo speedup e' 41.5x end-to-end e 2,088x per la co-occurrence. Nella sola rep1 e' 6.4x e 29x. In piu', CPU e GPU calcolano la co-occurrence su 7 e 3 cluster, cioe' su carichi di lavoro diversi.
3. **Il 120x end-to-end e' soprattutto un benchmark del Wilcoxon di Scanpy.** Il DE vale il 93.5% del tempo CPU a 1.3M. Senza DE lo speedup e' 7.9-9.2x. Dicks et al. 2026, sullo stesso dataset ma senza DE e senza I/O, riportano circa 110x su una sola H200: lo scarto non e' discusso nel manoscritto.
4. **La concordanza e' misurata solo a 10k celle, su un run precedente al benchmark (2026-03-11).** A partire da 50k celle le etichette Leiden GPU cambiano tra ripetizioni con lo stesso seme. La letteratura riporta ARI CPU-GPU intorno a 0.5 su 50k-1.3M celle (Gardner 2025; Nolet 2022: 0.54 a 1.3M). La frase "interchangeable" non e' sostenuta.
5. **Costo.** Il "well under one dollar" combina il tempo ottenuto con 8 GPU con il prezzo di una GPU: con 8 GPU il costo e' 1.93-3.87 USD, con 2 GPU 0.55-1.10 USD. Normalizzato per costo, lo speedup a 1.3M va da 10x a 50x con 8 GPU e da 34x a 175x con 2 GPU (le ipotesi di prezzo sono dichiarate nella sezione 4).

## 1. Confronto con la letteratura

Fonti lette in questa sessione: PDF locali in `/tmp/repo/manuscript/bibliography/` (testo estratto in `F_work/lit/`) per Dicks, Nolet e Gardner; WebFetch per ScaleSC (preprint bioRxiv), Billato (OpenAlex e bioRxiv), Duò e Squair (abstract via OpenAlex), codice sorgente di rapids-singlecell v0.14.1 su GitHub, documentazione stable di rapids-singlecell. Ogni riga riporta solo quanto letto.

| Studio (DOI) | Domanda | Hardware GPU | Baseline CPU (core) | Dataset | Metriche di velocita' | Concordanza | Speedup riportati |
|:--|:--|:--|:--|:--|:--|:--|:--|
| Nolet et al. 2022, bioRxiv (10.1101/2022.05.26.493607) | Workflow RAPIDS per scRNA e scATAC, multi-GPU | DGX-1, 1-8 V100 | 40 core (2 x 20 Xeon), stesso nodo | 1.3M cervello topo E18 e sottocampioni 50k, 250k | Tempo per step e totale; preprocessing distribuito con Dask | 1.3M: PCA abs Pearson >= 0.999, kNN conservati 95.66%, Leiden ARI 0.54, NMI 0.76 | 1.3M: 15,656 s CPU, 951 s con 1 GPU (16.5x), 365 s con 8 GPU (42.9x); da 1 a 8 GPU 2.6x |
| Gardner et al. 2025, SC'25 Workshops (10.1145/3731599.3767378) | Compromesso accuratezza/prestazioni | H100 80 GB, singola | 2 x Xeon 6548Y, 64 core | 1.3M E18, sottocampioni 50k-1.2M, 3 repliche | Tempo totale e per step | ARI CPU-GPU mediana 0.45-0.55 a tutte le dimensioni; GPU-GPU con lo stesso seme: Leiden ARI 0.927 | Oltre 10x end-to-end (1.2M: circa 3 h contro circa 17 min); oltre 150x per neighbours e clustering |
| Hu et al. 2025, ScaleSC (preprint 10.1101/2025.01.28.635256; pubblicato 10.1093/bioadv/vbaf167, DOI dal bib) | Scalabilita' su una GPU | A100, singola | Non riportata | 70k, 1.3M E18, 13M simulati (copie), 662k | Dal caricamento al Leiden, I/O incluso | Qualitativa ("replicate Scanpy's results in most steps") | 1.3M: 2 min contro 4.5 h di Scanpy (circa 135x); 13M sotto 1 h su una A100; rapids-singlecell fallisce a 1.3M (limite int32) |
| Dicks et al. 2026, arXiv (10.48550/arXiv.2603.02402) | Paper di rapids-singlecell | B200, H200, RTX PRO 6000, singola; 8 B300 per Tahoe-100M | Threadripper Pro 7975WX, 32 core / 64 thread | 1.3M E18 (senza DE, "timing excluded I/O"), Harmony fino a 11.4M, Tahoe 100M | Tempo per step e cumulativo, 3 run | numpy.allclose per gli step deterministici; ARI per Leiden (valori non riportati nel testo) | 1.3M: circa 52 min CPU contro 26 s (B200), oltre 120x; H200 110x; sotto circa 50k celle CPU comparabile o piu' veloce; 100M celle in meno di 20 min con Dask multi-GPU |
| Billato et al. 2025, bioRxiv (10.1101/2025.10.28.681564) | Scalabilita' e accuratezza di 5 framework | 4 x A100 (PCA), 2 x P100 (pipeline) | EPYC 7301 (PCA a singolo core), Xeon Gold 6130 (core non dichiarati) | 1.3M e 3 dataset annotati | Tempo PCA (10 ripetizioni), tempo pipeline | ARI rispetto alla verita' nota: RAPIDS < 0.7 su BE1, OSCA e scrapper 0.95-0.97 | PCA RAPIDS circa 15x rispetto al miglior CPU; pipeline 1.3M: RAPIDS circa 20 min, OSCA 2.5 h, Seurat 3 h |
| **Questo lavoro** | Velocita', scaling 1-8 GPU, concordanza, capacita', spatial | DGX H100 (1-8), RTX 4090 per lo spatial | SLURM 100 CPU su 224 logiche (112 core fisici); spatial: n_cpus 128 nei JSON | 1.3M E18 e sottocampioni; CELLxGENE 3.44M replicato fino a 11.9M; Visium v1/HD | Tempo per step, I/O e DE inclusi; 5 ripetizioni (rep1 inclusa nello scRNA, esclusa nello spatial) | Solo a 10k: ARI 0.908-0.963, HVG J 1.0, PCA 1.0 | 120x a 1.3M (8 GPU), 105x (2 GPU); senza DE 7.9-9.2x |

### Dove il lavoro e' allineato
- Gli speedup per step su neighbours, UMAP e Leiden (10-90x, singola GPU) sono nell'ordine di grandezza di Dicks e di Gardner.
- HVG e PCA concordanti: in linea con Nolet (PCA abs Pearson >= 0.999) e con la validazione `allclose` di Dicks. Dagli hash dei JSON l'identita' della lista HVG CPU/GPU risulta estesa a 100k (dato non sfruttato nel testo).
- Il vincolo di memoria lato host su pipeline "in-memory" e' coerente con la motivazione di ScaleSC.

### Dove se ne discosta senza spiegarlo
1. **Stesso dataset, cifra simile, causa diversa.** Dicks: circa 110-120x su una GPU, senza DE e senza I/O. Qui: 120x con 8 GPU, ma il 93.5% del tempo CPU e' DE; senza DE la cifra e' 8-9x, perche' il preprocessing della pipeline ibrida resta su Scanpy CPU. Il manoscritto cita Dicks solo come software e non confronta i numeri.
2. **Concordanza.** Gardner (che il manoscritto cita solo come "limited to a single GPU") conclude che CPU e GPU "are not interchangeable", con ARI di circa 0.5; Nolet riporta ARI 0.54 a 1.3M. Qui si ottiene 0.91-0.96 a 10k e si conclude per l'intercambiabilita'. La citazione di Gardner e' selettiva.
3. **Multi-GPU.** Nolet 2022 distribuiva gia' filtering e normalisation su 8 GPU (272 s contro 60 s a 1.3M). Il codice di rapids-singlecell 0.14.1 ha rami Dask per `normalize_total`, `log1p` e `pca`, e la documentazione stable elenca anche QC, filtri, HVG e scale. Il manoscritto (l88, l418, l432) sostiene che il preprocessing "had no distributed GPU route".
4. **Capacita'.** ScaleSC elabora 13M celle su una sola A100. Dicks elabora 100M celle con Dask su 8 B300. "11.9M su un DGX, limite CPU RAM" e' quindi una proprieta' della pipeline scelta, non dell'analisi GPU.
5. **Piccoli dataset.** Dicks: sotto circa 50k celle la CPU e' comparabile. Qui: 12x a 10k. Lo scarto si spiega col DE CPU (54.9% del tempo CPU a 10k), ma il testo non lo dice.
6. **Spatial.** In questa sessione non ho trovato benchmark GPU spatial sistematici e comparabili. La documentazione di rapids-singlecell riporta tempi GPU per Moran e Geary senza confronto CPU. Il superlativo "largest GPU speedup reported for any spatial transcriptomics operation" resta quindi non verificabile.

## 2. Punti nascosti che un revisore chiederebbe

| # | Punto | Evidenza (ricalcolata) | Severita' |
|:--|:--|:--|:--|
| H1 | Il multi-GPU non distribuisce nulla | X CuPy su GPU 0 (`scripts/benchmark_multigpu.py`); rsc 0.14.1 `_pca.py`: ramo Dask solo con `isinstance(X, DaskArray)`; `_neighbors/__init__.py`: nessun ramo Dask; PCA+neighbours 2.98/2.97/3.00 s (500k) e 17.23/16.99/17.01 s (1.3M). Il diario (`CLAUDE.md`) scrive "PCA: Single-GPU truncated SVD (cuML)" e "Other 7 GPUs sat idle" per la pipeline standard | critical |
| H2 | Nodi, concorrenza, CPU allocate | Driver 535.247.01 (1/2/4 GPU, eseguiti in parallelo dalle 21:53 alle 23:03 del 15/03) contro 535.183.01 (8 GPU, stress test su `poddgx02`); `--cpus-per-task` 16/32/56/200 contro 100 per la CPU; nessun `--exclusive`. Il testo (l157) dice "dedicated node" | major |
| H3 | Esclusione della rep1 nello spatial | Co-occurrence CPU HD 8 um: r1 73.47 s, r2-5 3570-3574 s, `.npy` identici (max diff 0). Anche Moran e Geary CPU sono piu' lenti nelle r2-5 (35.7 contro 47.9 s): la CPU peggiora dopo la rep1 | critical |
| H4 | Warmup e JIT nello scRNA | Warmup = matmul 100 x 100 (non compila i kernel di rsc). Rep1 GPU 10k: 6.40 s contro 2.50 s; leiden_0.5 r1 1.70 s contro 0.09 s; SD 1 GPU 10k da 1.75 a 0.11 s escludendo r1. Convenzione opposta a quella dello spatial | major |
| H5 | Peso del DE | Quota DE nel tempo CPU: 54.9% (10k), 84.9%, 86.9%, 84.6%, 93.5% (1.3M) | major |
| H6 | Equita' della baseline | 100 CPU logiche su 224; QC Scanpy a 1.3M: 188.2 s con 32 CPU e 186.6 s con 200 (passo sostanzialmente single-thread); nessuna curva di scaling dei thread | major |
| H7 | Concordanza: solo 10k, run diverso, non determinismo a scala | `concordance_10000_r1.json` del 2026-03-11: CPU 40/45 cluster (r = 1.0/1.5) contro 41/46 nei 5 run CPU del benchmark, che sono deterministici; tempo GPU 16.9 s contro 3.3 s. A >= 50k le etichette GPU variano tra ripetizioni (1.3M, r = 1.5: 4 partizioni distinte in 5 run) | major |
| H8 | Leiden non equivalenti | CPU: igraph con `n_iterations=2`; GPU: cuGraph con `max_iter=100` (default di rsc). Contraddice "identical parameters" della Table 1 | major |
| H9 | Tetto della Jaccard kNN | max 0.9375 (= 15/16), `fraction_perfect` 0.0: gli insiemi confrontati hanno cardinalita' diverse; 0.930 e' il 99% del massimo raggiungibile | minor |
| H10 | Codice non cronometrato | Restano fuori dal cronometro init RMM, warmup, copia `adata.raw`, subset HVG, avvio e arresto Dask. Intervallo tra timestamp (limite superiore, include il salvataggio): 8.2 s contro 2.5 s cronometrati (1 GPU 10k), 522 s contro 428 s (8 GPU 1.3M) | minor |
| H11 | Un solo dataset per la scala; stress test su copie | Scala 10k-1.3M solo su E18. Stress test e DE su CELLxGENE 3,436,470 celle; oltre questa soglia `anndata.concat` di copie esatte (celle duplicate) | major |
| H12 | Co-occurrence su carichi diversi | HD 8 um: 7 cluster CPU, 3 GPU; concordanza della co-occurrence `shape_mismatch`, quindi non calcolata (i Methods l149 la descrivono) | major |
| H13 | Test DE non equivalenti | Table 7 confronta t-test CPU, Wilcoxon GPU e Wilcoxon su pseudo-bulk CPM; nessun confronto dei p-value tra CPU e GPU a parita' di test | major |
| H14 | Soglie | Skip oltre 500 cluster e oltre 100k spot, "rho > 0.97 stringent", risoluzione 0.1 per HD: nessuna motivazione ne' analisi di sensibilita' | minor |
| H15 | Non determinismo GPU nello spatial | Co-occurrence GPU HD 8 um diversa in r3 e r5 (max diff 7.70); cluster HD 2 um 534 contro 538; ARI 0.0652 contro 0.0843 | minor |

Amdahl: la Discussione parla di "classic manifestation of Amdahl's law". Il fit T(N) = a + b/N sui 15 run da 2, 4 e 8 GPU non trova frazione parallela al netto del data loading (sezione 4, PoW-A). Il riferimento Amdahl 1967 (DOI 10.1145/1465482.1465560, dal bib) non e' stato aperto in questa sessione.

## 3. PoW proposti

| PoW | Punto nascosto | Protocollo eseguibile | Dati necessari / disponibili | Come cambierebbe l'interpretazione | Riferimento (DOI letto) | Priorita' |
|:--|:--|:--|:--|:--|:--|:--|
| A (eseguito) | H1, H2 | Fit di Amdahl per step su 2/4/8 GPU; differenze per step tra 2 e 8 GPU | JSON nel repo, si' | Frazione parallela circa 0: la sezione multi-GPU va riscritta (risultato nella sezione 4) | Nolet 2022, 10.1101/2022.05.26.493607 | alta |
| B (eseguito) | H3 | Speedup spatial con rep2-5, rep1-5 e sola rep1; confronto degli `.npy` | JSON e `.npy`, si' | Le cifre 51.6x e 3,272x non reggono senza spiegare la variabilita' 49x della CPU | n/a | alta |
| C (eseguito) | H5 | Speedup con e senza DE e solo DE, per N e numero di GPU | JSON, si' | Il 120x e' guidato dal DE CPU | Dicks 2026, 10.48550/arXiv.2603.02402 | alta |
| D (eseguito) | H4 | Table 4 e speedup con rep1-5 e con rep2-5 | JSON, si' | Speedup a 10k da 12.0x a 14.0x; SD dominata dalla rep1 | n/a | alta |
| E (eseguito) | H6 | Speedup normalizzato per costo (ipotesi dichiarate) e per energia (limite TDP) | JSON e prezzi letti, si' | Lo speedup in risorse premia 2 GPU rispetto a 8 | Pagine prezzi (sezione 4) | alta |
| F (eseguito) | H7 | Hash delle etichette Leiden e numero di cluster per ripetizione, CPU e GPU, a ogni N | JSON, si' | GPU non deterministica a >= 50k; numero di cluster divergente con N | Gardner 2025, 10.1145/3731599.3767378 | media |
| G (eseguito) | H10 | Differenza tra timestamp consecutivi meno tempo cronometrato | JSON, si' | Overhead GPU non trascurabile a N piccoli | n/a | media |
| H | H7, H8 | `compare_results.py` sui CSV di etichette gia' salvati per r1-r5 a 50k-1.3M (CPU contro gpu, gpu2, gpu8); 5 semi per lato per ARI CPU-CPU, GPU-GPU e CPU-GPU; igraph con `n_iterations=-1` o 100 contro cuGraph con 100 | CSV sul cluster DGX, non nel repo | ARI a 1.3M vicino a 0.9: tesi rafforzata. Vicino a 0.5 (come in Nolet e Gardner): "interchangeable" va ritirato | Gardner 2025; Nolet 2022 | alta |
| I | H1, H2 | Vero multi-GPU: X letta come Dask array (`read_elem_lazy`, chunk da 100k celle), preprocessing rsc su Dask, PCA `covariance_eigh`; nodo esclusivo e fisso, stessi `cpus-per-task`, cache gestita in modo uniforme; confronto con l'ibrida a `n_gpus=1` | Stessi h5ad sul cluster | Speedup da 1 a 8 GPU > 1.5x: lo "sublineare" era un artefatto. Curva piatta: la tesi regge | Nolet 2022 (2.6x da 1 a 8 V100); Dicks 2026 | alta |
| J | H6 | CPU a 1, 16, 50, 100 e 224 thread, per step, a 100k e 1.3M; DE con implementazione CPU alternativa | h5ad sul cluster | Speedup per step poco sensibile ai thread: la baseline e' di fatto single-thread e va dichiarato | n/a | media |
| K | H11 | Ripetere la scala 10k-1.3M e la concordanza su `brain_full_3436470.h5ad` (CELLxGENE, 202 donatori) | Gia' scaricato sul cluster | Speedup per step entro +-30%: generalizzabilita' rafforzata | Billato 2025, 10.1101/2025.10.28.681564 | media |
| L | H6 | `nvidia-smi --query-gpu=power.draw` a 1 Hz e RAPL per i socket, integrati per run | Nuovi run | Rapporto energetico < 10x a 1.3M: il vantaggio in tempo va distinto da quello in risorse | n/a | media |
| M | H9 | Escludere l'indice della cellula stessa e allineare k prima della Jaccard | `.npz` gia' salvati | La Jaccard kNN salirebbe verso 1: la frase sul floating-point va tolta | n/a | bassa |
| N | H3, H12 | Co-occurrence CPU e GPU sulle stesse etichette (quelle CPU) e sugli stessi intervalli; 5 ripetizioni in processi separati | h5ad Visium HD locali | Speedup < 100x: la cifra 3,272x va ritirata | n/a | alta |
| O | H14, A0314 | Componenti connesse del grafo kNN di espressione a HD 2 um; leidenalg e cuGraph con 5 semi ciascuno | h5ad locali | Migliaia di componenti: i 2,559 cluster CPU riflettono il grafo, non la stocasticita' | Duò 2020, 10.12688/f1000research.15666.3 | media |

## 4. Risultati dei PoW eseguiti

### PoW-A: Amdahl e attribuzione del 12% (`f02_scrna_pow.py`, `f02_amdahl.csv`, `f02_steps_2v8_*.csv`)
Modello T(N) = a + b/N stimato sui 15 run (2, 4, 8 GPU x 5 ripetizioni); IC95 con t(13) = 2.16.

| N | Grandezza | 2 GPU (s) | 4 GPU (s) | 8 GPU (s) | b (s) | IC95 b | Frazione parallela a N=2 |
|--:|:--|--:|--:|--:|--:|:--|--:|
| 500k | totale | 124.46 | 124.96 | 124.60 | -0.60 | -15.8, 14.6 | 0.00 |
| 500k | PCA + neighbours | 2.98 | 2.97 | 3.00 | -0.03 | -1.05, 0.99 | 0.00 |
| 1.3M | totale | 493.29 | 486.63 | 435.18 | 136.6 | 57.1, 216.2 | 0.14 |
| 1.3M | data loading (CPU) | 148.99 | 135.07 | 90.61 | 141.4 | 50.9, 231.9 | 0.46 |
| 1.3M | PCA + neighbours | 17.23 | 16.99 | 17.01 | 0.62 | -1.04, 2.29 | 0.02 |
| 1.3M | totale meno data loading | 344.30 | 351.57 | 344.57 | -4.75 | -51.9, 42.4 | 0.00 |

A 1.3M la differenza 2 -> 8 GPU (58.12 s) e' interamente nel data loading (58.38 s). Gli altri step variano di meno di 2.4 s, in entrambe le direzioni. La sequenza delle differenze (2 -> 4: 6.7 s; 4 -> 8: 51.5 s) e' incompatibile con Amdahl, che richiederebbe la prima doppia della seconda. Il data loading e' una lettura h5ad su CPU: le differenze riflettono nodo, disco e contesa (2 e 4 GPU concorrenti sullo stesso nodo; nel job a 4 GPU la rep1 impiega 79.8 s e le rep2-5 132-164 s).

### PoW-B: ripetizione 1 nello spatial (`f01_spatial_repeats.py`, `f01_spatial_speedup_conventions.csv`)

| Piattaforma, step | CPU r1 (s) | CPU r2-5 (s) | GPU r1 (s) | GPU r2-5 (s) | Speedup r2-5 | Speedup r1-5 | Speedup solo r1 |
|:--|--:|--:|--:|--:|--:|--:|--:|
| HD 8 um, totale | 584.6 | 4,068.4 | 91.4 | 78.8 | 51.6 | 41.5 | 6.4 |
| HD 8 um, co-occurrence | 73.5 | 3,573.2 | 2.51 | 1.09 | 3,271.5 | 2,087.9 | 29.2 |
| HD 8 um, Moran | 35.7 | 47.9 | 3.76 | 0.30 | 162.3 | 46.0 | 9.5 |
| HD 2 um, totale | 1,010.1 | 1,042.0 | 109.1 | 96.7 | 10.8 | 10.4 | 9.3 |
| Visium v1, totale | 39.7 | 10.0 | 24.5 | 6.0 | 1.7 | 1.6 | 1.6 |

Le matrici di co-occurrence CPU delle 5 ripetizioni sono identiche (somma 6074.49, differenza massima 0). Per la GPU la rep1 e' davvero un warmup (Moran 3.76 contro 0.30 s). Per la CPU di HD 8 um invece la rep1 e' la piu' veloce, e la CPU rallenta in tutti gli step spaziali dalla rep2 in poi. Senza una spiegazione (thread numba, stato del processo, memoria) non si puo' stabilire quale dei due valori CPU sia quello "tipico". Lo speedup della co-occurrence va dunque riportato almeno come intervallo: da 29x (r1 contro r1) a 3,272x (r2-5). Va inoltre ricalcolato su etichette comuni (PoW-N).

### PoW-C: composizione dello speedup (`f02_speedup_with_without_DE.csv`)

| N | GPU | Speedup totale | Speedup senza DE | Quota DE su tempo CPU | Speedup del solo DE |
|--:|--:|--:|--:|--:|--:|
| 10k | 1 | 12.0 | 9.4 | 54.9% | 15.6 |
| 50k | 1 | 33.7 | 8.9 | 84.9% | 66.9 |
| 100k | 1 | 43.8 | 10.2 | 86.9% | 87.5 |
| 500k | 2 | 34.9 | 6.8 | 84.6% | 139.6 |
| 1.3M | 2 | 105.5 | 7.9 | 93.5% | 715.3 |
| 1.3M | 8 | 119.6 | 9.2 | 93.5% | 691.1 |

### PoW-D: convenzione sulla ripetizione 1 nello scRNA (`f02_table4_conventions.csv`)

| Configurazione | Media rep1-5 (SD) | Media rep2-5 (SD) | rep1 / media rep2-5 | Speedup rep1-5 | Speedup rep2-5 |
|:--|--:|--:|--:|--:|--:|
| CPU 10k | 39.48 (10.19) | 34.92 (0.31) | 1.65 | | |
| 1 GPU 10k | 3.28 (1.75) | 2.50 (0.11) | 2.56 | 12.0 | 14.0 |
| 1 GPU 50k | 8.39 (2.23) | 7.40 (0.31) | 1.67 | 33.7 | 37.7 |
| 1 GPU 100k | 14.77 (2.22) | 13.80 (0.49) | 1.35 | 43.8 | 46.6 |
| 2 GPU 1.3M | 493.29 (10.32) | 496.91 (7.40) | 0.96 | 105.5 | 105.0 |
| 8 GPU 1.3M | 435.18 (16.22) | 428.11 (4.27) | 1.08 | 119.6 | 121.9 |

Effetti per step (`f02_perstep_speedup_1gpu.csv`). Normalisation a 10k: 329x con rep1-5, 115x con rep2-5; il 329x viene dalla rep1 lenta della CPU. Leiden a 10k: leiden_0.5 0.36x con rep1-5 e 1.12x con rep2-5; leiden_1.0 e leiden_1.5 sono piu' veloci su GPU anche includendo la rep1 (1.36x, 1.60x). PCA a 10k: 4.8x contro 11.7x.

### PoW-E: costo ed energia (`f03_cost_energy.py`, `f03_cost_energy.csv`)
Ipotesi di prezzo, lette il 2026-11-03 e da trattare come ipotesi:
- H100 per GPU-ora: 2.69 USD (Runpod community SXM), 3.99 (Lambda 8 GPU), 4.29 (Lambda 1 GPU), 6.88 (AWS p5). Fonte: intuitionlabs.ai, articolo aggiornato al 2026-10-11; il 3.99 e' confermato su lambda.ai/service/gpu-cloud/pricing.
- CPU: c7i.24xlarge (96 vCPU Sapphire Rapids) a 4.284 USD/h (instances.vantage.sh). Scenario A: 100 vCPU = 4.46 USD/h. Scenario B: 200 vCPU = 8.93 USD/h.
- Energia, solo come limite superiore: H100 SXM fino a 700 W (nvidia.com); 8480C assimilata a 8480+ (350 W, 56 core / 112 thread; dato da listini di rivenditori visti nei risultati di ricerca, non da Intel ARK).

| N, GPU | Speedup in tempo | Costo CPU (A / B, USD) | Costo GPU (2.69 - 6.88 USD/GPU-h) | Speedup per costo | Energia, limite TDP |
|:--|--:|:--|:--|:--|--:|
| 10k, 1 | 12.0 | 0.049 / 0.098 | 0.002 - 0.006 | 7.8 - 39.9 | 5.0 |
| 100k, 1 | 43.8 | 0.80 / 1.60 | 0.011 - 0.028 | 28.4 - 145.3 | 18.2 |
| 1.3M, 2 | 105.5 | 64.5 / 129.1 | 0.74 - 1.89 | 34.2 - 175.1 | 22.0 |
| 1.3M, 8 | 119.6 | 64.5 / 129.1 | 2.60 - 6.65 | 9.7 - 49.6 | 6.0 |

Verifica della frase l420: 7.3 minuti richiedono 8 GPU. A 2-4 USD per GPU-ora il costo e' quindi 1.93-3.87 USD, non "well under one dollar". Con 2 GPU (8.2 min) e' 0.55-1.10 USD. Una singola GPU a 1.3M non e' stata misurata.

### PoW-F: determinismo e cluster a scala (`f02_determinism.csv`)
- CPU: 1 hash distinto delle etichette su 5 ripetizioni, a ogni N e a ogni risoluzione (deterministica).
- GPU: deterministica a 10k. Da 50k in su compaiono 2-4 partizioni distinte su 5 run con lo stesso seme (per esempio 1.3M con 2 GPU e r = 1.5: 82, 83 e 84 cluster in 4 partizioni distinte).
- Numero di cluster, CPU contro GPU a 8 GPU, 1.3M: 59 contro 50-52 (r = 0.5), 75 contro 68-69 (r = 1.0), 89 contro 79-84 (r = 1.5). A 10k: 31/41/46 contro 32/40/45.
- Hash della lista HVG identico tra CPU e GPU a ogni N (a 500k e 1.3M per costruzione: nella pipeline ibrida l'HVG e' calcolato con Scanpy).

### PoW-G: tempo non cronometrato (`f02_walltime_gaps.csv`)
Intervallo medio tra timestamp consecutivi (rep2-5), con il tempo cronometrato tra parentesi: CPU 1.3M 52,342 s (52,176); 8 GPU 1.3M 522 s (428); 1 GPU 10k 8.2 s (2.5); 8 GPU 10k 19.4 s (3.8). Il timestamp si registra prima del salvataggio dei CSV, quindi l'intervallo include il salvataggio per entrambe le pipeline ed e' solo un limite superiore. Per la GPU, a piccoli N la parte non cronometrata (init RMM, warmup, copie, avvio Dask) vale il 50-80% dell'intervallo.

### Verifica collaterale: capacita' in funzione degli HVG (`f04_capacity_hvg.py`)
A 11.9M la matrice densa HVG pesa 95.2 GB, cioe' il 17.8% del picco di 534.55 GB. Con capacita' inversamente proporzionale agli HVG si otterrebbero 23.8M celle (1,000 HVG) e 4.76M (5,000). Con il bilancio della Table 6 (36.9 kB per cella fuori dagli HVG) si otterrebbero 13.1M e 9.4M. Le cifre del testo (20M e 4M) non derivano da nessuno dei due modelli.

## 5. Frasi da riformulare

1. l14, abstract: "The GPU pipeline achieved up to 120-fold end-to-end speedup at 1.3M cells (435 s vs 52,056 s on CPU), reducing a 14.5-hour analysis to 7.3 minutes."
   Perche': il valore 120x dipende dal job a 8 GPU, la cui differenza dal job a 2 GPU sta nel data loading; il 93.5% del tempo CPU e' DE.
   Proposta: "At 1.3M cells the GPU pipeline completed in 435-493 s versus 52,056 s for Scanpy (105-120-fold); Wilcoxon differential expression accounted for 93% of the CPU time, and excluding it the speedup was 8-9-fold."
2. l14, abstract: "Multi-GPU scaling was sublinear due to CPU preprocessing dominance."
   Perche': nessuno step e' stato distribuito.
   Proposta: "In the configuration tested, PCA and neighbour search ran on a single device regardless of the number of GPUs allocated, so multi-GPU scaling was not measured; runtimes with 2, 4 and 8 GPUs differed only in CPU-side data loading."
3. l14, abstract: "achieving up to 51.6x end-to-end speedup (Visium HD 8 um) and 3,272x for co-occurrence analysis"
   Perche': le due cifre dipendono dall'esclusione della rep1, in cui la CPU ha impiegato 73 s invece di 3,573 s.
   Proposta: "end-to-end speedups of 6-52x on Visium HD 8 um depending on the repeat, driven by co-occurrence analysis, whose CPU runtime varied 49-fold across repeats with identical output (29-3,272x)". In alternativa: rimuovere le cifre fino all'esecuzione del PoW-N.
4. l416: "Normalisation and neighbour graph construction represent ideal GPU workloads, achieving speedups of 88-329x and 44-88x respectively, because they involve high arithmetic intensity"
   Proposta: "Normalisation (173-329x, an element-wise, memory-bandwidth-bound operation) and neighbour search (44-88x) benefited most".
5. l416: "Leiden clustering on small graphs is limited by low arithmetic intensity: consistent with the roofline model [@Williams2009], cuGraph's constant-time overhead exceeds CPU's short runtime"
   Proposta: "At 10k cells the apparent CPU advantage for Leiden was confined to the first call in the first repeat (cuGraph initialisation); in repeats 2-5 the GPU was 1.1-1.6-fold faster, although cuGraph ran up to 100 iterations against 2 for igraph."
6. l418: "The relatively modest 12% improvement from 2 to 8 GPUs at 1.3M cells reflects a fundamental constraint imposed by pipeline structure ... a classic manifestation of Amdahl's law"
   Proposta: "Runtimes with 2, 4 and 8 GPUs were indistinguishable for every GPU step, because the expression matrix was not converted to a Dask array and PCA and neighbour search therefore ran on one device; the 12% difference at 1.3M cells arose in data loading, which ran on different nodes."
7. l418: "a DGX H100 node is more efficiently utilised as eight independent single-GPU workers running concurrent analyses (yielding near-linear throughput scaling ...)"
   Proposta: "Normalised by cost, two GPUs per analysis were 3-4 times more efficient than eight at 1.3M cells; whether concurrent single-GPU jobs scale linearly was not tested, and the I/O contention we observed between concurrent jobs suggests it may not."
8. l420: "Single H100 GPUs are readily rentable ... translates to well under one dollar of compute rental for an entire atlas-scale analysis."
   Proposta: "At on-demand prices of USD 2.7-6.9 per H100-hour (October 2026), the 2-GPU run at 1.3M cells cost USD 0.7-1.9 and the 8-GPU run USD 2.6-6.7, against about USD 65 for 14.5 h on a 100-vCPU cloud instance; a single-GPU run at this size was not measured."
9. l420: "the memory-optimised variant described here extends single-GPU feasibility to 1.3M cells and beyond"
   Proposta: togliere, oppure "we expect, but did not test, that the memory-optimised variant would run on a single GPU".
10. l422: "This level of concordance is reassuring for practitioners: it indicates that GPU-accelerated and CPU-based analyses remain interchangeable for biological interpretation and conclusions."
    Proposta: "At 10,000 cells, CPU and GPU pipelines agreed closely (ARI 0.91-0.96). At 50,000 cells and above, GPU Leiden labels varied across repeats with a fixed seed, and other studies report CPU-GPU ARI near 0.5 at these sizes [Gardner 2025; Nolet 2022]; interchangeability at atlas scale therefore remains to be shown."
11. l422: "Floating-point non-associativity in GPU parallel reductions contributes negligibly to observed differences, as the dominant source of variation is the Leiden algorithm's non-deterministic vertex ordering."
    Proposta: togliere, oppure "We did not separate the contributions of numerical differences and of the clustering implementation."
12. l424: "it occurred because transient memory spikes during individual preprocessing operations briefly multiplied the working set past the SLURM cgroup limit"
    Proposta: "we hypothesise that transient allocations within preprocessing steps exceeded the cgroup limit; our between-step sampling cannot confirm this."
13. l424: "with 2,000 HVGs this suggests 20M cells at 1,000 HVGs and 4M cells at 5,000 HVGs"
    Proposta: togliere. In alternativa: "the dense HVG matrix accounted for 18% of the recorded peak, so halving or more than doubling the number of HVGs would shift capacity only moderately (an estimated 13M and 9M cells)".
14. l424: "Our ScaleSC-inspired chunked variant indeed reduced aggregate VRAM by a factor of five (49 GB to 10 GB) without improving the cell limit"
    Proposta: "The chunked variant reduced aggregate VRAM five-fold (49 to 10 GB) and raised the limit from 11.9M to at least 12.0M cells (it failed at 15.0M)."
15. l426: "GPU acceleration of cell-level DE provides moderate speedups (3-7x)"
    Proposta: "Cell-level GPU tests finished 3-7 times sooner than the CPU t-test; since the CPU Wilcoxon was not run at this scale, these ratios are not within-method accelerations."
16. l426: "at 3.4 million cells, p-values from cell-level tests become uninformative because virtually every gene reaches statistical significance"
    Proposta: togliere, oppure riportare la frazione di geni con p aggiustato < 0.05 dai risultati salvati.
17. l428: "is, to our knowledge, the largest GPU speedup reported for any spatial transcriptomics operation"
    Proposta: togliere il superlativo e aggiungere che CPU e GPU hanno lavorato su 7 e 3 cluster.
18. l428: "scientists can obtain identical rankings of spatially variable genes in seconds rather than minutes"
    Proposta: "nearly identical rankings (top-50 identical, top-100 Jaccard >= 0.98) in under a second rather than 35-48 s".
19. l430: "The dramatic divergence at Visium HD 2 um (ARI = 0.080) is not specific to GPU versus CPU comparison"
    Proposta: "The divergence at Visium HD 2 um (ARI 0.080; 2,559 CPU and 534-538 GPU clusters) reflects a systematic difference between implementations at this resolution; we did not test whether runs of the same implementation with different seeds diverge to a similar extent."
20. l432: "in which the preprocessing steps had no distributed GPU route and therefore executed on the host CPU"
    Proposta: "in which, as implemented, preprocessing ran in Scanpy on the host CPU; rapids-singlecell 0.14.1 provides Dask-based routes for normalisation and PCA that we did not use."
21. l438, Conclusions: "Multi-GPU scaling provides modest benefit (12% at 1.3M cells, 2 to 8 GPUs) due to the dominance of non-GPU-parallelised pipeline phases."
    Proposta: "Our multi-GPU configuration did not distribute any step, so multi-GPU scaling remains to be measured."
22. Titolo (l2): "... spatial transcriptomics on NVIDIA DGX H100 ..."
    Proposta: "GPU-accelerated single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics: ..."

## 6. Limiti di questo track
- Non ho ricalcolato i numeri dei Risultati che non sostengono una conclusione della Discussione: lo fanno gli altri track.
- I passaggi completi di Squair 2021, Amdahl 1967, Williams 2009 e Regev 2017 non sono stati letti (per Squair, Duò e Williams solo abstract o record OpenAlex). Le voci che ne dipendono sono marcate UNVERIFIABLE oppure si fondano sui dati, non sulla fonte.
- La lista delle funzioni Dask di rapids-singlecell viene dalla documentazione "stable" (versione corrente). Per la 0.14.1 ho verificato nel codice del tag solo `pca`, `normalize_total`, `log1p` e `neighbors`.
- Le pagine PubMed e PMC hanno restituito captcha. Per ScaleSC ho usato il preprint bioRxiv.
