# Scelte del PI, regione R2 (Metodi), step S3

Data: 2026-11-04. Ogni scelta ha il testo raccomandato già in `edits_R2.csv` (colonna `scelta_pi`); qui ci sono le prove, le alternative con il testo pronto e la conseguenza di ciascuna. Le prove DGX (sacct e log SLURM letti in sola lettura) sono nel pacchetto `R2_dgx_evidence.tgz`, da committare in `results_v2/S3/R2_dgx_evidence/` se l'agente principale lo approva (lo script `valori_R2.py` le legge da lì o, se mancano, direttamente dal DGX).

## CENSUS_CIT · Chiave e forma della citazione di CELLxGENE Census

**Domanda.** Come si cita la fonte del dataset scRNA (CZ CELLxGENE Census, release 2025-11-08), dopo aver tolto Zheng2017?

**Prove.** `scripts/download_data.py`: `CENSUS_VERSION = "2025-11-08"`, filtro `tissue_general == 'brain' and is_primary_data == True and assay in 10x 3' v1-v3`, campionamento `np.random.seed(42)` + `choice`. Log DGX del job 16140: "Found 3,436,470 matching cells", "Downloaded: 1,300,000 cells x 53,384 genes". Articolo letto nel PDF (Zotero): CZ CELLxGENE Discover, *Nucleic Acids Research* 53(D1):D886-D900, 2025, doi 10.1093/nar/gkae1142; il passaggio sul Census descrive l'accesso programmatico (API Python e R) alle cellule di CZ CELLxGENE con query sui metadati e il campo `is_primary_data`. Metadati verificati su Crossref (54 autori, primo autore collettivo "CZI Cell Science Program").

**Alternative.**
- **A (raccomandata).** Citare l'articolo NAR con la chiave `CZCellxGene2025` e la release nel testo (testo in R2-001). Conseguenza: serve aggiungere la voce al `.bib` (regione R4 o agente principale); voce pronta qui sotto.
- **B.** Citare l'articolo e, in più, il pacchetto `cellxgene-census` come software (@misc con URL e versione). Conseguenza: una voce in più nel `.bib` (pesa sul limite di pagine D-03); la versione del pacchetto usata non è registrata nei JSON, quindi la voce direbbe solo la release dei dati.
- **C.** Nessuna voce bibliografica: URL e release nel testo, "...from the CZ CELLxGENE Census (release 2025-11-08, https://chanzuckerberg.github.io/cellxgene-census/)...". Conseguenza: nessuna modifica al `.bib`, ma Springer preferisce le citazioni formali e la fonte resta senza riferimento citabile.

**Raccomandazione: A.** È la fonte primaria del Census, letta e verificata; la release nel testo garantisce la riproducibilità.

Voce `.bib` pronta (da Crossref; per brevità si può usare `and others` dopo il primo autore):

```
@article{CZCellxGene2025,
  author    = {{CZI Cell Science Program} and Abdulla, Shibla and Aevermann, Brian and Assis, Pedro and Badajoz, Seve and Bell, Sidney M and Bezzi, Emanuele and Cakir, Batuhan and Chaffer, Jim and Chambers, Signe and Cherry, J Michael and Chi, Tiffany and Chien, Jennifer and Dorman, Leah and Garcia-Nieto, Pablo and Gloria, Nayib and Hastie, Mim and Hegeman, Daniel and Hilton, Jason and Huang, Timmy and Infeld, Amanda and Istrate, Ana-Maria and Jelic, Ivana and Katsuya, Kuni and Kim, Yang Joon and Liang, Karen and Lin, Mike and Lombardo, Maximilian and Marshall, Bailey and Martin, Bruce and McDade, Fran and Megill, Colin and Patel, Nikhil and Predeus, Alexander and Raymor, Brian and Robatmili, Behnam and Rogers, Dave and Rutherford, Erica and Sadgat, Dana and Shin, Andrew and Small, Corinn and Smith, Trent and Sridharan, Prathap and Tarashansky, Alexander and Tavares, Norbert and Thomas, Harley and Tolopko, Andrew and Urisko, Meghan and Yan, Joyce and Yeretssian, Garabet and Zamanian, Jennifer and Mani, Arathi and Cool, Jonah and Carr, Ambrose},
  title     = {{CZ CELLxGENE Discover}: a single-cell data platform for scalable exploration, analysis and modeling of aggregated data},
  journal   = {Nucleic Acids Research},
  year      = {2025},
  volume    = {53},
  number    = {D1},
  pages     = {D886--D900},
  doi       = {10.1093/nar/gkae1142}
}
```

`edit_id`: R2-001.

## CONC_11MARZO · Concordanza dal run dell'11 marzo: dichiarata o ricalcolata

**Domanda.** La concordanza a 10.000 cellule (Table 2, Fig. 5, righe 240-244, 422) viene da un run di prova dell'11 marzo diverso dalle ripetizioni cronometrate: lo si dichiara o si ricalcola?

**Prove.** `results/concordance_10000_r1.json`: `cpu_timestamp` 2026-03-11T23:14:30Z, `gpu_timestamp` 2026-03-11T23:15:03Z, cluster CPU 31/40/45 (r = 0.5/1.0/1.5). Questi istanti cadono nel job `smoke_test` 16139 (sacct: poddgx01, 16 CPU, 1 GPU, 11/03 23:59:59 - 12/03 00:15:27 CET), che ha anche creato `brain_10000.h5ad` (lo stesso file usato poi dal benchmark). Le 5 ripetizioni cronometrate CPU (100 CPU, job 16161) danno 31/41/46 cluster in tutte e cinque; le GPU 32/40/45 come nel run di concordanza. Il codice di confronto (`scripts/compare_results.py`) e i file per cella delle ripetizioni (`results/{cpu,gpu}_10000_r1_{clusters,hvgs,de,knn,pca_loadings}`) esistono, quindi un ricalcolo a 10.000 cellule è possibile in pochi minuti.

**Alternative.**
- **A (raccomandata).** Dichiararlo nella didascalia di Table 2 (testo in R2-019): "Concordance was computed once, at 10,000 cells, on a separate pair of CPU and GPU runs made on 11 March 2026 (UTC) in a preliminary test job (16 CPUs, one GPU), with the same input file and parameters as the benchmark but before the timed repeats; at Leiden r = 1.0 and 1.5 its CPU run found 40 and 45 clusters, against 41 and 46 in all five timed CPU repeats.". Conseguenza: nessun calcolo; i numeri di Table 2, Fig. 5 e righe 240-244 restano; la regione R3 (R0244, riga 240) usa la stessa data (11 March 2026, UTC).
- **B.** Ricalcolare a 10.000 cellule sulla ripetizione 1 cronometrata (CPU job 16161, GPU job 16314) con `compare_results.py`. Conseguenza: i valori di ARI e NMI cambiano (la CPU cronometrata ha 41 e 46 cluster); vanno riscritti Table 2/Fig. 5 e le righe 240-244 e 422 (R3, R4); nella didascalia: "Concordance was computed at 10,000 cells between the first timed CPU and GPU repeats." È una nuova analisi: serve il via libera del PI e il tempo di rigenerare la figura (S4).
- **C.** Ricalcolare a tutte le dimensioni (collegata alla scelta di R3 "indebolire interchangeable o ricalcolare a tutte le dimensioni"). Conseguenza: la Jaccard dei vicini e il DE a 1,3M richiedono file grandi e tempo di calcolo; cambia la sezione concordanza dei Risultati e della Discussione; a ridosso della scadenza del 10 novembre è la più rischiosa.

**Raccomandazione: A.** Il run dell'11 marzo usa lo stesso file e gli stessi parametri: dichiararlo basta a non affermare oltre il disegno, senza nuove analisi a sei giorni dalla scadenza. Se il PI vuole numeri sulle ripetizioni cronometrate, B è economica.

`edit_id`: R2-019.

## HD2UM · Visium HD 2 µm: sottocampione casuale di 400.000 bin su 6.296.688

**Domanda.** Come si presenta la piattaforma Visium HD 2 µm, visto che il sottocampione casuale tiene il 6,35% dei bin e quindi non descrive la risoluzione a 2 µm?

**Prove.** `SPATIAL/results_v2/server_gpu/spatial_gpu_visium_hd_square_002um_r1_results.json`: `n_spots_input` 6,296,688, `n_spots_after_qc` 389,492; `SPATIAL/run_all_benchmarks.sh`: `--max-spots 400000`; `benchmark_spatial_gpu.py`: `np.random.seed(42)` + `choice` dopo il caricamento. 400,000 / 6,296,688 = 6.3525%; il passo della griglia regolare di pari densità è 2 / sqrt(0.0635) = 7.94 µm (la distanza media al vicino più prossimo di un diradamento casuale è circa la metà: per questo il testo parla di densità, non di distanza fra bin). `SPATIAL/SPATIAL.md` (riga 255 circa) riconosce già che il sottocampionamento casuale a 2 µm distrugge la contiguità spaziale.

**Alternative.**
- **A (raccomandata).** Dichiararlo e rinominare la piattaforma (testo in R2-026, ultima frase): "Random subsampling kept 6.35% of the 2 um bins, so the subsample has the bin density of a regular grid with a spacing of about 8 um, and its spatial neighbour graph and autocorrelation statistics do not describe the native 2 um resolution." In tabelle e figure (S5) la piattaforma diventa "Visium HD 2 um (random 400k-bin subsample)". Conseguenza: nessun nuovo run; S5 adegua etichette e frasi dei Risultati spatial.
- **B.** Togliere la piattaforma 2 µm dal capitolo. Testo per la riga 122: "Spatial benchmarks used two 10x Genomics public datasets, both obtained from the 10x Genomics public data portal. The first is Visium v1 Mouse Brain Sagittal Anterior, the standard spot-based spatial transcriptomics platform, consisting of 2,695 spots at 55 um resolution and approximately 32,285 genes. The second is the Visium HD Spatial Gene Expression Library, Mouse Brain (FFPE), processed by 10x Genomics with Space Ranger 3.0.0 (CytAssist; Visium Mouse Transcriptome Probe Set v2.0), benchmarked at the 8 um bin size (393,543 bins, 19,059 genes)." (si tolgono anche le due frasi sul sottocampione). Conseguenza: spariscono le righe 2 µm di Tables 8-10 e Fig. 7-9 (S5) e lo speedup di testa di HD 2 µm nell'abstract; il capitolo si accorcia (D-03).
- **C.** Nuovo run su un ritaglio contiguo di circa 400.000 bin a 2 µm. Conseguenza: fuori da D-01 (nuovo calcolo, CPU di riferimento sul DGX e GPU sul server, circa mezza giornata di macchina più l'analisi); i numeri 2 µm di S1 si buttano; difficilmente compatibile con il 10 novembre.

**Raccomandazione: A.** Corregge l'affermazione senza nuovo calcolo e lascia al lettore un dato utile sul costo a 400.000 bin.

`edit_id`: R2-026 (la stessa modifica contiene anche le correzioni R0259, R0426 e R0428, che valgono per tutte e tre le alternative).

## RAPIDS_DGX · Perché lo spatial GPU non è girato sul DGX (R0279 con R0451, gruppo J07)

**Domanda.** Che cosa dicono i Metodi (righe 161-163) sul mancato run GPU spatial sul DGX?

**Prove.** Log SLURM letti sul DGX (sola lettura): job `test_driver` 16944 (27/03/2026, poddgx02, container `sc-benchmark-2406.sif`): "CuPy: PASS", "RMM: PASS", "rapids-singlecell: PASS", "Overall: ALL PASS". Sei job `spatial_smoke` del 27/03/2026 (16945-16951) su poddgx02, 1 GPU, con il container `sc-benchmark-2406.sif` (RAPIDS 24.06): la parte CPU termina con exit 0, la parte GPU con exit 1 per `CURAND_STATUS_INITIALIZATION_FAILED` (16945) e `CUSPARSE_STATUS_NOT_INITIALIZED` / "CUDA context cannot be initialized" (16946-16951); altri quattro job del 25/03 (16862-16874) sono in sacct ma senza log. Nessun log di un tentativo con il container RAPIDS 26.02. Il driver di poddgx02 è 535.183.01 (nvidia-smi nel log 16317: "CUDA Version: 12.2"). `SPATIAL/SPATIAL.md` righe 263-265: "DGX driver 535.183.01 (CUDA 12.2) is incompatible with RAPIDS 26.02 (needs driver 570+)", con l'opzione di ricostruire su RAPIDS 24.06 "(tested: CuPy/RMM/rsc all pass on driver 535)" (commit d65ff4d secondo il registro). Il testo attuale dice invece che un downgrade a RAPIDS 25.02 è fallito per dipendenze: nessun file lo documenta. Dopo D-11 la frase "DGX-scale spatial benchmarks were not feasible" è falsa (il riferimento CPU spatial gira sul DGX).

**Alternative.**
- **A (raccomandata).** Riga 161: "The GPU part of the spatial pipeline was run only on the workstation: on DGX node `poddgx02` (driver 535.183.01) a container based on RAPIDS 24.06 passed basic CuPy, RMM and rapids-singlecell tests, but smoke tests of the spatial GPU pipeline in it failed when CuPy initialised cuSPARSE and cuRAND, and the cause was not investigated further."; righe 162-163 tolte (R2-034..R2-036). Conseguenza: i Metodi riportano ciò che i log mostrano (test di base riusciti nel job test_driver 16944, smoke test spatial falliti nei job 16945-16951), senza la spiegazione sul limite CUDA, che nessun log documenta; la propagazione del driver di R0623 è soddisfatta; le Limitazioni (riga 432, R4) dicono la stessa cosa.
- **B.** Riga 161: "The GPU part of the spatial pipeline was run only on the workstation."; righe 162-163 tolte. Conseguenza: frase più corta (D-03) ma tace un tentativo documentato; è la raccomandazione del piano scritta prima di trovare i log.
- **C.** Come A, più la frase finale "Porting the spatial pipeline to a driver-compatible RAPIDS release remains future work." Conseguenza: una frase in più (D-03); annuncia un lavoro futuro che il capitolo non motiva altrove.

**Raccomandazione: A.** Dice ciò che i log mostrano, in una frase, senza cause non verificate.

`edit_id`: R2-034, R2-035, R2-036.

## REPO_DOI · Tag, commit e DOI d'archivio del repository (R0454; codice proposto da R2)

Il piano elenca questa scelta fra quelle di S3 senza un codice assegnato alla mia regione; la frase sta alla riga 170, quindi la preparo e propongo il codice `REPO_DOI`.

**Domanda.** Il capitolo dichiara una release identificata (tag, commit, DOI d'archivio, per esempio Zenodo) o solo l'URL del repository?

**Prove.** `.gitignore`: `results/*` tranne `*.json`, `logs/`, `data/`, `SPATIAL/results/*.csv`; i log SLURM stanno solo sul DGX. `scripts/benchmark_maxpower_chunked.py` entra in git il 25/03/2026 (a54da19), dopo il run chunked del 24/03; il JSON a 1,7M ha una configurazione (scaling su GPU, pool 10 GB) diversa dallo script committato. I JSON scRNA non registrano l'hash git (quelli spatial di S1 sì: `metadata.system.git_commit`).

**Alternative.**
- **A (raccomandata).** Il PI crea un tag di release e un DOI (Zenodo) prima della sottomissione; alla prima frase di R2-039 si aggiunge "(release <tag>, commit <hash>, archived at <DOI>)". Conseguenza: legame FAIR fra testo, codice e risultati; mezz'ora di lavoro del PI; il testo resta in attesa fino ad allora.
- **B.** Solo URL e hash del commit finale, senza DOI. Conseguenza: nessun archivio persistente (un repository GitHub può cambiare o sparire).
- **C.** Il testo di R2-039 così com'è (solo URL). Conseguenza: nessuna identificazione della versione: è il difetto FAIR segnalato dalla revisione.

**Raccomandazione: A.** Testo attuale della modifica (senza identificativi): "All code, Dockerfiles, SLURM submission scripts and result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX>. Per-cell outputs (cluster labels, HVG lists, DE tables, k-NN indices, PCA loadings, Moran's I and Geary's C values) and SLURM logs are not in the repository because of their size; the stress-test results at 1.7M and 3.4M cells and the chunked 12M-cell run were produced by intermediate versions of the scripts that were not committed."

`edit_id`: R2-039. Il target `make download-data` (`--max-cells 100000`) non ricrea i dati del capitolo: da correggere nel README o nel Makefile in un passo successivo.

## Voci del `.bib` pronte per la regione R4 o per l'agente principale (non sono scelte del PI)

Solo R4 modifica il `.bib`; queste due voci sono state verificate su Crossref in questa sessione.

R0518 (Crossref 10.1109/SCW63240.2024.00028):

```
@inproceedings{Shanmugavelu2024,
  author    = {Shanmugavelu, Sanjif and Taillefumier, Mathieu and Culver, Christopher and Hernandez, Oscar and Coletti, Mark and Sedova, Ada},
  title     = {Impacts of floating-point non-associativity on reproducibility for {HPC} and deep learning applications},
  booktitle = {SC24-W: Workshops of the International Conference for High Performance Computing, Networking, Storage and Analysis},
  year      = {2024},
  pages     = {170--179},
  publisher = {IEEE},
  doi       = {10.1109/SCW63240.2024.00028}
}
```

R0536 (Crossref 10.1038/s41592-024-02212-x; 22 autori nell'ordine di Crossref, anno 2025 coerente con il volume 22, online 2024-03-20; la chiave resta Marconato2024):

```
@article{Marconato2024,
  author    = {Marconato, Luca and Palla, Giovanni and Yamauchi, Kevin A. and Virshup, Isaac and Heidari, Elyas and Treis, Tim and Vierdag, Wouter-Michiel and Toth, Marcella and Stockhaus, Sonja and Shrestha, Rahul B. and Rombaut, Benjamin and Pollaris, Lotte and Lehner, Laurens and V{\"o}hringer, Harald and Kats, Ilia and Saeys, Yvan and Saka, Sinem K. and Huber, Wolfgang and Gerstung, Moritz and Moore, Josh and Theis, Fabian J. and Stegle, Oliver},
  title     = {{SpatialData}: an open and universal data framework for spatial omics},
  journal   = {Nature Methods},
  year      = {2025},
  volume    = {22},
  number    = {1},
  pages     = {58--62},
  doi       = {10.1038/s41592-024-02212-x}
}
```
