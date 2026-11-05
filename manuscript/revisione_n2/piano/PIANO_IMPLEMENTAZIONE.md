# Piano di implementazione della revisione n.2 (capitolo LNBI)

Generato da `tools/s2_mkplan.py` (step S2, 4 novembre 2026). Non si modifica a mano: si correggono gli ingressi (`voci/`, `arbitrati.csv`, `PIANO_testa.md`, `PIANO_coda.md`) e si rigenera. Manoscritto di riferimento: `manuscript/full_paper_LNBI.md`, md5 4587032be8d2905007687e0bb50d848e (le righe citate sono di questa versione). Controlli dell'ultima generazione: `checks.json`.

## Come si usa

1. Si lavora per step (S3, S4, S5, S6, S7), nell'ordine della sezione «Sequenza di lavoro», non nell'ordine dei livelli.
2. Prima della prima voce che dipende da una decisione, la decisione si registra in `docs/decisions/` (le decisioni ancora aperte sono qui sotto).
3. Su una riga toccata da più voci (mappa `mappe/transazioni.csv`) non si usa `edit_file` voce per voce: si rilegge la riga, si compone il testo che soddisfa tutte le voci, si sostituisce una volta sola.
4. Ogni voce chiusa si registra in `IMPL_diario.csv`: `id, livello, esito, valore_inserito, convenzione, fonte_riletta, riga, data, note`, con `esito` in `fatto | rimandato | non applicabile | deciso-diversamente`.
5. Ogni valore nuovo si rilegge con uno script dal file indicato in **Fonte**, anche quando la voce lo riporta già: la voce dice dove leggerlo, il diario registra cosa si è letto.
6. Le voci `assorbita` non si eseguono: le copre la voce primaria indicata in `ledger.csv` (colonna `final`). Le voci `verificare-in-step` si aprono leggendo la fonte; se la fonte non conferma, l'affermazione si indebolisce o si toglie.
7. Prima di chiudere una voce si applicano le propagazioni della mappa `mappe/occorrenze_valore.csv` con `action = propagare` e quell'`id`; le occorrenze `omografo-non-toccare` e `valore-confermato-non-toccare` non si toccano.

## Decisioni da prendere prima di lavorare

| codice | cosa | stato | raccomandazione | voci che ne dipendono |
|---|---|---|---|---|
| CONV | Convenzione unica sulle ripetizioni | in attesa del PI (S2) | A: media e SD di tutte e 5 le ripetizioni, in scRNA e spatial | colonna `decision` o `depends_on` = CONV |
| NEIGH | Ricerca dei vicini CPU a 1 thread numba (Scanpy `settings.n_jobs = 1` passato a pynndescent da 8.192 cellule in su), trovata in S2 | in attesa del PI (S2) | dichiararlo nei Metodi e quantificarlo in S3 con una misura a server libero | frasi sugli speedup dei vicini: Discussione riga 416, Fig. 2 riga 221, Table 9 riga 362 (spatial, "Expression neighbours") |
| D-01 ... D-13 | Decisioni già registrate | prese | | vedi `docs/decisions/` |

Scelte del PI che gli step successivi porteranno al PI (non decise in S2; le voci interessate hanno `level` L5 o `decision` PI-S3):

- **In S3.** Titolo (2-3 alternative, senza "systematic" e "scalability", hardware per modalità); abstract nuovo (150-250 parole); cifra di testa scRNA (119,6x con 8 GPU da sola o con il run a 2 GPU, più la quota del Wilcoxon 93,5% e lo speedup senza espressione differenziale); che cosa il capitolo dichiara come nuovo e la frase sull'estensione rispetto allo short paper; domande di ricerca dopo D-02 (righe 37-39); Human Cell Atlas alla riga 23; chiave e forma della citazione di CELLxGENE Census; tag, commit e DOI d'archivio del repo; Table 5 con tutti i punti dello stress test o una selezione dichiarata; Table 6 ricostruita dalla traccia o tolta; righe KMeans in Table 5; frase sul limite di capacità se mancano i log dei run a 13,7M, 14M e 15M; concordanza: indebolire "interchangeable" o ricalcolarla a tutte le dimensioni; concordanza dal run dell'11 marzo dichiarata o ricalcolata; Jaccard dei vicini riformulata o ricalcolata senza la cella stessa; confronto con Dicks 2026; paragrafo sul costo cloud tenuto (con fonte di prezzo datata) o tolto; capacità in funzione degli HVG; dichiarazione sull'uso di LLM richiesta da Springer; PoW proposti dalla revisione e non coperti da decisioni (H, J, K, L, M, O); Padova o Padua; formula di ringraziamento del cluster.
- **In S5.** Visium HD 2 µm: il sottocampione casuale di 400.000 bin su 6.296.688 tiene il 6,35% dei bin, quindi le statistiche spaziali non descrivono la risoluzione a 2 µm (raccomandato: dichiararlo e rinominare la piattaforma; alternative: toglierla, oppure un nuovo run su un ritaglio contiguo); speedup della sola co-occorrenza corretta come informazione (D-13 la toglie dagli speedup); Table 8 e Fig. 7 a HD 8 µm senza co-occorrenza o con totali completi e nota; spazio per il controllo CPU sul server; frase dei Metodi sui run spatial di marzo in un processo unico; spiegazione del mancato run GPU spatial sul DGX (righe 161-163 e Limitations).

## Convenzioni e trappole

1. **Valori spatial della revisione superati.** 51,6x, 41,5x, 7,4x, 6,4x, 3.272x (3.271x), 2.088x, 67x, 29x (co-occorrenza), Moran e Geary 162-170x, 4,75x, e 2.559 come numero di cluster della CPU di riferimento (2.559 vale solo per il controllo sul server, CPU a 128 thread): nessuno di questi si scrive come valore di riferimento. Fonti uniche degli speedup spatial di testa: Visium v1 e HD 2 µm da `s1_speedups.csv` (step `total`, cpu `reference_dgx`, convention `1_5`, punto e IC); HD 8 µm senza co-occorrenza da `s1_extra_numbers.json`, `speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx`. I valori spatial si leggono da `SPATIAL/results_v2/` con CPU `reference_dgx` e convenzione `1_5` (`s1_speedups.csv`, `s1_step_stats.csv`, `s1_extra_numbers.json`); il controllo sul server (`control_server`) si riporta accanto.
2. **Co-occorrenza a Visium HD 8 µm (D-13).** Fuori dagli speedup; il difetto di rapids-singlecell 0.14.1 si riporta come risultato, con la verifica 0.15.1 (`SPATIAL/results_v2/cooc_check/cooc_check_eval.json`).
3. **I gruppi di Leiden spatial dipendono dalla macchina CPU** (HD 8 µm: 4 sul DGX, 7 sul server; HD 2 µm: 3.027 e 2.559; GPU 3-4 e 538): ogni numero di cluster dice la macchina.
4. **Convenzione A** (se approvata): i valori scRNA già nel testo, calcolati sulle ripetizioni 1-5, restano; a 10.000 e 50.000 cellule la ripetizione 1 pesa dal 5 al 14% sullo speedup end-to-end e molto di più su normalizzazione e vicini (compilazione JIT), e il testo lo dice dove cita quei valori.
5. **Omografi.** Le dimensioni dei dataset (10,000, 50,000, 100,000, 500,000, 1.3M) compaiono ovunque: la mappa delle occorrenze li marca; non si sostituisce per ricerca globale.
6. **Niente lineette U+2013 e U+2014** nel manoscritto; prima di ogni commit si cercano nei file modificati.
7. Lo stile (`manuscript/revisione_n2/stile/`) si applica in S6, dopo la sostanza: molte frasi della copia di stile cambieranno.
8. **Memoria in GiB.** Tutte le memorie dei JSON (RAM e VRAM, chiavi `*_gb`) sono calcolate come byte / 1024^3, cioè GiB (`get_peak_ram_gb` in `scripts/benchmark_*.py`). Nel testo si scrive GiB, oppure si converte in GB; una tabella non mescola le due unità (per esempio la matrice HVG densa a 11,9M vale 95,2 GB = 88,66 GiB).
9. **Espressione differenziale.** Il benchmark gira su 3.399.892 cellule e 202 donatori (sottocampione da 3,4M dopo il QC), non sulla selezione completa da 3.436.470: tutti gli otto `results/de_benchmark_*.json` riportano `n_cells` 3399892.
10. **Tempo non cronometrato.** Gli intervalli fra timestamp di ripetizioni consecutive contengono le ripetizioni 2-5 (a 10.000 cellule su 1 GPU: 8,23, 8,03, 8,44, 8,22 s); per questa grandezza la convenzione A non si applica e lo si dice (eccezione registrata nella voce R0653).


# Voci per difficoltà crescente

Il livello misura la difficoltà, non la precedenza: l'ordine di lavoro è nella sezione «Sequenza di lavoro».


## L1 · sostituzione di una cifra (35 voci)

#### R0512 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** bib:RAPIDS2024 (fuori dalla prosa); registro: MISMATCH, minor
- **Valore:** {RAPIDS}: Open {GPU} Data Science → RAPIDS: Libraries for End to End GPU Data Science
- **Istruzione:** In cibb2026_references.bib, voce @misc RAPIDS2024 (citata a riga 32): sostituire il titolo con la forma usata dagli sviluppatori, title = {{RAPIDS}: Libraries for End to End {GPU} Data Science}, e aggiungere versione e data di ultimo accesso in un campo che splncs04 stampa, per esempio note = {Version 26.02, last accessed <data della verifica>} (la versione 26.02 e' quella dell'immagine base dichiarata a riga 155). Aprire https://rapids.ai il giorno della modifica per la data di accesso; se reindirizza a developer.nvidia.com, tenere l'URL rapids.ai. La chiave RAPIDS2024 resta (non viene stampata).
- **Fonte:** revisione_n2_log.csv R0512 recomputed (forma della ref. 13 di Dicks2026); full_paper_LNBI.md riga 155 per la versione
- **Nota:** Anno: Dicks2026 usa 2023, la voce 2024; con la versione 26.02 l'anno coerente e' 2026. Scelta minore di S3, da registrare.

#### R0515 · S3 · P5 (bibliografia) · aggiungere
- **Bersaglio:** bib:Gardner2025 (fuori dalla prosa); registro: MISMATCH, minor
- **Valore:** (campo pages assente) → 349--358
- **Istruzione:** Voce @inproceedings Gardner2025: aggiungere pages = {349--358} (splncs04 stampa le pagine degli inproceedings). Facoltativo: address = {St. Louis} dal record Crossref. Autori, booktitle, editore e DOI restano: il registro li conferma.
- **Fonte:** revisione_n2_log.csv R0515 recomputed (Crossref 10.1145/3731599.3767378)

#### R0535 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** bib:Palla2022 (fuori dalla prosa); registro: MISMATCH, major
- **Valore:** Palla, Giovanni and Spitzer, Hannah and Klein, Michal and Fischer, David and Schaar, Anna Christina and Kuemmerle, Louis Benedikt and Rybakov, Sergei and Ibarra, Ignacio L. and Holber, Olle and Virshup, Isaac and Pegno, Mohammad Nofallah and Theis, Fabian J. → Palla, Giovanni and Spitzer, Hannah and Klein, Michal and Fischer, David S. and Schaar, Anna Christina and Kuemmerle, Louis Benedikt and Rybakov, Sergei and Ibarra, Ignacio L. and Holmberg, Olle and Virshup, Isaac and Lotfollahi, Mohammad and Richter, Sabrina and Theis, Fabian J.
- **Istruzione:** Voce @article Palla2022 (citata alle righe 28, 140, 160): sostituire il campo author con l'elenco di 13 autori in value_new ('Holber' diventa 'Holmberg'; 'Pegno, Mohammad Nofallah' non esiste ed e' sostituito, nello stesso punto, da Mohammad Lotfollahi e Sabrina Richter; Fischer con l'iniziale S.) e aggiungere number = {2}. Prima di salvare confrontare ordine e nomi con il record OpenAlex o nature.com indicato in source. Lo stesso tipo di errore in Marconato2024 e' la voce R0536 (traccia T2).
- **Fonte:** revisione_n2_log.csv R0535 recomputed e note (OpenAlex works/doi:10.1038/s41592-021-01358-2; nature.com); cibb2026_references.bib Palla2022
- **Nota:** Verificato dal capo. L'iniziale S. di Fischer viene da 'Fischer DS' del ricalcolo.

#### R0544 · S3 · P13 (affermazioni oltre i dati) · correggere
- **Bersaglio:** prosa (riga 28); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The 10x Genomics Visium HD platform generates up to 6.3 million 2 um bins per tissue section`
- **Valore:** up to 6.3 million 2 um bins per tissue section → ~11.2 million
- **Istruzione:** Riga 28, 'The 10x Genomics Visium HD platform generates up to 6.3 million 2 um bins per tissue section': 6.3 milioni e' il numero di bin 2 um del dataset usato (6,296,688), non il massimo della piattaforma; la capture area Visium HD ha circa 11.2 milioni di quadrati 2x2 um (glossario Space Ranger). Riscrivere: "A Visium HD capture area contains about 11.2 million 2 um barcoded squares [10x Space Ranger glossary]; the section analysed here yielded 6.3 million 2 um bins" e aggiungere al .bib una voce per il glossario Space Ranger (URL del registro). Il nome del dataset (Tiny 3', non FFPE) si corregge nei Metodi (S3, da S1).
- **Fonte:** righe_da_pianificare.csv R0544 recomputed (https://www.10xgenomics.com/support/software/space-ranger/getting-started/space-ranger-glossary)
- **Assorbe:** R0255
- **Nota:** Il testo del glossario non e' nel pacchetto: S3 riapre l'URL prima di citare.

#### R0400 · S3 · P10 (concordanza) · correggere
- **Bersaglio:** tabella:Table 1 riga 8 Leiden (riga 78); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `| 8 | Leiden clustering | r in {0.5, 1.0, 1.5}, seed = 42 | igraph (CPU) / cuGraph (GPU) [@Traag2019] |`
- **Valore:** r in {0.5, 1.0, 1.5}, seed = 42 → n_iterations=2; n_iterations=100
- **Istruzione:** Table 1, riga 8: nella colonna Key parameters aggiungere le iterazioni, "r in {0.5, 1.0, 1.5}, seed = 42; `n_iterations` = 2 (CPU, igraph) / 100 (GPU, rapids-singlecell default)".
- **Fonte:** righe_da_pianificare.csv id=R0040 campo recomputed (sorgente del pacchetto rapids-singlecell 0.14.1, file rapids_singlecell/tools/_clustering.py riga 130, non del repo)
- **Assorbe:** R0040
- **Nota:** Valore GPU preso da R0040 (sorgente 0.14.1), non da R0400 che legge la documentazione corrente.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0428 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 122); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The second is Visium HD Mouse Brain (CytAssist, FFPE), benchmarked at two bin sizes: 8 um (393,543 bins) and 2 um (subsampled from the native 6.3 million dow...`
- **Valore:** subsampled from the native 6.3 million down to 389,492 bins → 6,296,688; 400,000; 389,492; seed 42
- **Istruzione:** Riga 122: "2 um (subsampled from the native 6.3 million down to 389,492 bins)" diventa "2 um (6,296,688 bins, randomly subsampled to 400,000 bins with seed 42; 389,492 after QC)" e, nell'ultima frase, "subsampled to approximately 400,000 bins" diventa "subsampled to 400,000 bins". Controllare in S3 che i metadata di SPATIAL/results_v2 (S1) riportino gli stessi conteggi dei JSON di marzo.
- **Fonte:** righe_da_pianificare.csv id=R0428 e id=R0259 campo recomputed (SPATIAL/results/spatial_*_visium_hd_* metadata)

#### R0342 · S3 · P10 (concordanza) · correggere
- **Bersaglio:** prosa (riga 149); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Spatial autocorrelation concordance was measured as the Spearman rho between CPU and GPU per-gene Moran's I (and separately Geary's C) statistics across all ...`
- **Valore:** statistics across all genes → across the 2,000 HVGs
- **Istruzione:** Riga 149: "statistics across all genes" diventa "statistics across the 2,000 highly variable genes on which spatial autocorrelation was computed". In S5 confermare n_common_genes = 2000 nei JSON di concordanza di SPATIAL/results_v2 (D-12 punto 6: il calcolo della concordanza non è cambiato).
- **Fonte:** righe_da_pianificare.csv id=R0464 campo note; id=R0342 campo recomputed (n_common_genes = 2000)
- **Assorbe:** R0464
- **Nota:** La concordanza di punta (rho >= 0,9995) riguarda solo i 2.000 HVG: da dire anche nei Risultati spatial (S5).

#### R0518 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** bib:Shanmugavelu2024 (riga 173); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Shanmugavelu2024`
- **Valore:** n.d. → SC24-W: Workshops of the International Conference for High Performance Computing, Networking, Storage and Analysis; 170-179; IEEE
- **Istruzione:** Voce Shanmugavelu2024 del .bib: booktitle come in Crossref, aggiungere pages = {170--179} e publisher = {IEEE}; autori e doi restano.
- **Fonte:** righe_da_pianificare.csv id=R0518 campo recomputed (api.crossref.org/works/10.1109/SCW63240.2024.00028)

#### R0129 · S3 · P10 (concordanza) · correggere
- **Bersaglio:** prosa (riga 242); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The downstream biological results also aligned well: differential expression log-fold-changes across 40 matched cluster pairs showed mean Spearman correlatio...`
- **Valore:** 30 of the 40 pairs → 34
- **Istruzione:** A riga 242 sostituire "with 30 of the 40 pairs exceeding" con "with 34 of the 40 pairs exceeding" e aggiungere dopo "0.946": "(median 0.9995; the mean is lowered by two pairs, one of which shares no cells)".
- **Fonte:** revisione_n2_log.csv id=R0129 campo recomputed (a04_concordance.py: results/concordance_10000_r1.json)
- **Dipende da:** R0709
- **Nota:** Coppie anomale: cpu17_gpu24 (rho -0.157, overlap 0.0) e cpu38_gpu5 (rho 0.448).

#### R0697 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 262); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `while recorded peak aggregate VRAM was only 49 GB out of 640 GB (7.6%)`
- **Valore:** 49 GB out of 640 GB (7.6%) → 48.8 GB
- **Istruzione:** A riga 262 sostituire "only 49 GB out of 640 GB (7.6%)" con "only 48.8 GiB out of 640 GiB (7.6%)" e a riga 424 "aggregate GPU VRAM remained flat at 49 GB (7.6% of the 640 GB total)" con "aggregate GPU VRAM remained flat at 48.8 GiB (7.6% of the 640 GiB total)" (riga 424 nella transazione della riga). Il picco 48.84 e' NVML used/1024**3, quindi GiB (R0252); 640 GiB e' la capacita' nominale di 8 schede da 80 GiB (il driver ne riporta 79.6 per scheda, 636.8 in totale, 7.7%): se il testo usa la capacita' riportata dal driver, scrivere 636.8 GiB e 7.7% anche in abstract e Conclusioni. Table 5 conserva 49 arrotondato con intestazione in GiB. Abstract (riga 14) e Conclusioni (riga 437) hanno solo il 7.6%, che resta.
- **Fonte:** revisione_n2_log.csv id=R0697 campo recomputed
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0156 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 267); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `This variant succeeded at 12.0 million cells (862 GB peak RAM, 10 GB aggregate VRAM, 156 min) but failed at 15.0 million cells during the CSR-to-CSC layout c...`
- **Valore:** 156 min → 131.5 min
- **Istruzione:** A riga 267 sostituire "156 min" con "131.5 min" (7,891.25 s nel JSON). Per "failed at 15.0 million cells" nessun JSON: S3 cerca il log del run a 15.0M; se manca, scrivere "and a run at 15.0 million cells failed" senza lo step.
- **Fonte:** revisione_n2_log.csv id=R0156 campo recomputed (results/maxpower_chunked_12000000_8gpu_results.json timings.total)
- **Assorbe:** R0468
- **Nota:** Primaria per R0468. Il JSON e' stato prodotto da una versione dello script diversa da HEAD (A0094): dichiararlo nel README del repo, non nel testo.

#### R0161 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** tabella:Table 5 riga 10.3M (riga 275); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `10.3M | 92 | 465 | 49 | KMeans | Pass`
- **Valore:** | 92 | → 91
- **Istruzione:** In Table 5, riga 10.3M, colonna Runtime: sostituire 92 con 91 (5,488.53 s = 91.48 min).
- **Fonte:** revisione_n2_log.csv id=R0161 campo recomputed (results/maxpower_10309410_8gpu_results.json timings.total)

#### R0191 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** tabella:Table 7 riga Pseudo-bulk (riga 315); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Pseudo-bulk (Wilcoxon) | CPU (aggregated) | 0 | 128 | 43.7x`
- **Valore:** | 128 | 43.7x | → 127 | 43.9x
- **Istruzione:** In Table 7, riga Pseudo-bulk (Wilcoxon): Time 128 diventa 127 e Speedup 43.7x diventa 43.9x (5,597.79 / 127.47). Allineare il testo di riga 321 (R0196). L'abstract (44x, T1) e' gia' coerente.
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0191 campo recomputed (results/de_benchmark_pseudobulk.json, de_benchmark_ttest_cpu.json)
- **Dipende da:** D-04

#### R0194 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** tabella:Table 7 riga t-test scatter (riga 318); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `t-test (scatter) | GPU | 8 | 1,656 | 3.4x`
- **Valore:** 1,656 → 1,655
- **Istruzione:** In Table 7, riga t-test (scatter): Time 1,656 diventa 1,655 (1,655.47 s, ttest_scatter); Speedup 3.4x resta (3.38x). Usare il run ttest_scatter, non il rerun 'clean' (1,649.36), salvo diversa scelta dichiarata.
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0194 campo recomputed (results/de_benchmark_*.json)
- **Dipende da:** R0197

#### R0195 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** tabella:Table 7 riga t-test chunk (riga 319); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `t-test (chunk-stream) | GPU | 1 | 1,650 | 3.4x`
- **Valore:** 1,650 → 1,649
- **Istruzione:** In Table 7, riga t-test (chunk-stream): Time 1,650 diventa 1,649 (1,649.46 s); Speedup 3.4x resta (3.39x).
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0195 campo recomputed (results/de_benchmark_*.json)

#### R0197 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 321); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Among cell-level tests on GPU, Wilcoxon (826 s) was faster than t-test (1,656 s), and multi-GPU scatter (826 s for Wilcoxon) was essentially equivalent to si...`
- **Valore:** t-test (1,656 s) → 1,655
- **Istruzione:** A riga 321 sostituire "Wilcoxon (826 s) was faster than t-test (1,656 s)" con "the Wilcoxon implementation (826 s) finished sooner than the t-test (1,655 s)"; il resto (826 contro 831 s) resta. Per D-04 i due test GPU non sono confrontabili a parita' di metodo (Wilcoxon scritto a mano, senza pareggi ne' p-value): non trarne conclusioni sui test.
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0197 campo recomputed (results/de_benchmark_*.json)
- **Dipende da:** D-04; R0194

#### R0199 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 416); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Normalisation and neighbour graph construction represent ideal GPU workloads, achieving speedups of 88-329x and 44-88x respectively, because they involve hig...`
- **Valore:** 88-329x → 173-329x
- **Istruzione:** Riga 416: in 'achieving speedups of 88-329x and 44-88x respectively' sostituire 88-329x con 173-329x (normalizzazione; Results riga 217: 329x a 10k, 206x a 50k, 173x a 100k, medie r1-r5 secondo la convenzione A). Il 44-88x dei vicini resta. La frase si riscrive insieme a R0575 (meccanismo).
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0575 campo recomputed; full_paper_LNBI.md riga 217
- **Dipende da:** CONV
- **Nota:** Con la convenzione 2-5 la normalizzazione sarebbe 115-137x (R0575): se il PI sceglie 2-5 la voce si rigenera. Il limite inferiore 88 era copiato dai vicini.

#### R0588 · S3 · P13 (affermazioni oltre i dati) · correggere
- **Bersaglio:** prosa; bib:nuova fonte di prezzo (riga 420); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Single H100 GPUs are readily rentable on commercial cloud platforms at approximately USD 2 to 4 per hour, so the 120x speedup at 1.3M cells reported here (re...`
- **Valore:** well under one dollar → 1.93-3.87
- **Istruzione:** Riga 420: la frase 'Single H100 GPUs are readily rentable on commercial cloud platforms at approximately USD 2 to 4 per hour, so the 120x speedup at 1.3M cells reported here (reducing a 14.5-hour CPU analysis to 7.3 minutes) translates to well under one dollar of compute rental for an entire atlas-scale analysis.' combina il tempo a 8 GPU con il prezzo di una GPU. Sostituire con: "At on-demand prices of USD 2 to 4 per H100-hour [price source, accessed 2026], the 8-GPU run at 1.3M cells (7.3 min) would cost USD 1.93-3.87 as allocated; a single-GPU run at this size was not measured." Aggiungere una fonte di prezzo datata (peer_review.md PoW-E: intuitionlabs.ai, articolo aggiornato al 2026-10-11; Lambda 3.99 USD/GPU-h) come voce bibliografica con data di accesso, e dire che il range 2-4 USD vale per i fornitori neocloud.
- **Fonte:** righe_da_pianificare.csv id=R0588 campo recomputed (tracks/F_work/f03_cost_energy.py: 8 x 435.18 s x 2-4 USD/GPU-h)
- **Dipende da:** R0587
- **Assorbe:** R0207, R0545, R0663
- **Nota:** Hyperscaler 6.88-12.29 USD/GPU-h (R0588): con quei prezzi il costo sale. Se il PI toglie il paragrafo (pi_choices), la voce diventa 'togliere'.

#### R0602 · S3 · P13 (affermazioni oltre i dati) · correggere
- **Bersaglio:** prosa (riga 424); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Our ScaleSC-inspired chunked variant indeed reduced aggregate VRAM by a factor of five (49 GB to 10 GB) without improving the cell limit, which further under...`
- **Valore:** without improving the cell limit → 12.0M
- **Istruzione:** Riga 424: nella frase 'Our ScaleSC-inspired chunked variant indeed reduced aggregate VRAM by a factor of five (49 GB to 10 GB) without improving the cell limit, which further underlines that GPU memory is not the binding resource in current single-cell workflows.' sostituire da 'without improving the cell limit' alla fine con: "and raised the limit from 11.9M to at least 12.0M cells (it failed at 15.0M), while host RAM reached 862 GB, which confirms that GPU memory was not the binding resource in this pipeline."
- **Fonte:** righe_da_pianificare.csv id=R0602 campo recomputed (results/maxpower_chunked_12000000_8gpu_results.json); full_paper_LNBI.md riga 267 ('15.0 million cells', '862 GB peak RAM')
- **Dipende da:** R0156
- **Assorbe:** R0213, R0683
- **Nota:** Il massimo di 11.9M in abstract, Table 5 e Conclusioni va qualificato per pipeline (T1, T3, T4).

#### R0216 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 426); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Within cell-level tests on GPU the Wilcoxon rank-sum test actually outperformed the t-test (826 vs 1,656 s), a counterintuitive result that reflects the fact...`
- **Valore:** 1,656 → 1,655
- **Istruzione:** Riga 426: in '(826 vs 1,656 s)' sostituire 1,656 con 1,655 (1,655.47 s arrotondato). Stesso arrotondamento in Table 7 (T3).
- **Fonte:** righe_da_pianificare.csv id=R0216 campo recomputed (results/de_benchmark_ttest_scatter.json)

#### R0229 · S3 · P9 (convenzione sulle ripetizioni) · correggere
- **Bersaglio:** prosa (riga 432); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The 75% CPU-preprocessing fraction we report is thus a property of the software stack available at the time of benchmarking rather than an intrinsic limit of...`
- **Valore:** 75% → 78.0%
- **Istruzione:** Riga 432: sostituire 'The 75% CPU-preprocessing fraction we report' con "The share of the timed total spent in CPU preprocessing (data loading, QC, normalisation and HVG selection) in the 8-GPU hybrid runs at 1.3M cells (78.0%, mean of five repeats)", perche' R0353 toglie la frase dei Risultati (riga 231) che riportava la quota e il valore va dichiarato dove si usa. 78.0% = media r1-5 da results/gpu8_1300000_r{1..5}_results.json (somma dei quattro step su timings.total; 77.98% come rapporto delle medie, 78.03% come media dei rapporti); il 75% era la sola ripetizione 1. La continuazione della frase si scrive con R0628; se il PI toglie la frase, toglierla con R0628.
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0229 campo recomputed (tracks/A_work/a03_multigpu.py)
- **Dipende da:** CONV; R0353
- **Nota:** Coerenza con Results riga 231 (run 'rappresentativo' r1, T3).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0623 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 432); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `This was not a design choice: the cluster's driver (535.183.01) caps the CUDA runtime at 12.2, and while the scRNA-seq pipeline ran there through forward com...`
- **Valore:** 535.183.01 → 535.247.01; 535.183.01
- **Istruzione:** Riga 432: sostituire 'the cluster's driver (535.183.01) caps the CUDA runtime at 12.2' con: "the cluster nodes we used ran drivers 535.247.01 (1-, 2- and 4-GPU runs) and 535.183.01 (8-GPU runs and stress test), which cap the CUDA runtime at 12.2". In S3 verificare che il limite 12.2 valga anche per 535.247.01 (release notes CUDA citate in R0339) e indicare su quale nodo è fallito lo stack spatial GPU. Nella stessa riga 432 sostituire anche "Spatial benchmarks were conducted on a local RTX 4090 workstation rather than the DGX H100 cluster, precluding measurements of multi-GPU spatial scaling and benchmarking of the full Visium HD 2 um resolution (6.3 million bins)." con "The GPU part of the spatial benchmark ran on an RTX 4090 workstation, while its CPU reference ran on a DGX node; multi-GPU spatial analysis and the full Visium HD 2 um resolution (6.3 million bins) were not benchmarked." (D-11).
- **Fonte:** righe_da_pianificare.csv id=R0623 campo recomputed (tracks/F_work/f02_provenance.csv, metadata.gpu_info.driver_version)
- **Assorbe:** R0226
- **Nota:** La frase precedente della stessa riga ('Spatial benchmarks were conducted on a local RTX 4090 workstation rather than the DGX H100 cluster...') non ha una riga di registro in T5 ma va aggiornata per D-11 (la CPU di riferimento spatial ora gira sul DGX, S3.md).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0238 · S3 · PF (finanziamento) · correggere
- **Bersaglio:** prosa (riga 455); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `This study was co-funded by the BIRD 2024/START (SID) programs, Department of Cardio-Thoracic-Vascular Sciences (DCTV), University of Padua (PI: Daniele Sabb...`
- **Valore:** B53C22006450001 → B53C22006440001
- **Istruzione:** Riga 455, Funding: sostituire "CUP: B53C22006450001" con "CUP: B53C22006440001" (D-05). Nient'altro nella frase.
- **Decisione o convenzione:** D-05
- **Fonte:** decisioni_D01_D13.txt D-05
- **Dipende da:** D-05
- **Assorbe:** R0736

#### R0646 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** trasversale (fuori dalla prosa); registro: UNSUPPORTED, critical
- **Valore:** 51.6x → 6.868546906119942
- **Istruzione:** I valori della revisione (51.6x con r2-5, 41.5x con r1-5, 6.4x con la sola r1) sono superati da S1: con un processo per ripetizione la CPU non rallenta (P1: co-occorrenza HD 8 um max/min 1,008 sul DGX) e le convenzioni 1_5 e 2_5 coincidono. In S5 riscrivere ogni cifra spatial di testa (abstract riga 14, Risultati 338-342, Conclusioni 440) con il riferimento DGX, convenzione 1_5, e a Visium HD senza la co-occorrenza (D-13): HD 8 um 6.9x [IC 6.8; 6.9], HD 2 um 10.4x, Visium v1 1.4x (a v1 la co-occorrenza resta, D-13 vale solo a HD). La frase dei Metodi a riga 166 la riscrive in S3 la voce R0453 (testo unico, con Numba, OmniPath e gruppi comuni): in S5 non riscriverla; controllare soltanto che, insieme alla riga 165 (R0466), dica che ogni ripetizione gira in un processo nuovo e che si riporta la media di tutte e cinque le ripetizioni. La causa del rallentamento di marzo (Squidpy lascia numba a 1 thread dopo nhood_enrichment, P2 di S1) va scritta come motivo del nuovo riferimento.
- **Decisione o convenzione:** D-01
- **Fonte:** s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0] (IC [1],[2]; convenzione 1_5 verificata in S2: (total - co_occurrence) dgx_cpu / server_gpu da s1_step_stats.csv mean_1_5 riproduce il valore, con mean_2_5 sarebbe 6.8783); per HD 2 um e v1 s1_speedups.csv platform=visium_hd_square_002um|visium step=total cpu=reference_dgx convention=1_5
- **Dipende da:** D-01;D-13;CONV
- **Assorbe:** R0660
- **Nota:** Il JSON non riporta la convenzione del valore senza co-occorrenza; S1.md lo usa come valore di riferimento (6,9x). Il totale con co-occorrenza (7,8x) non si usa a HD.
- **Modificata in arbitrato:** instruction, source, target (vedi `arbitrati.csv`)

#### R0673 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** trasversale (fuori dalla prosa); registro: info, info
- **Valore:** 2,559 → 3027
- **Istruzione:** Il numero di cluster CPU su cui poggia il PoW-O (2,559 a HD 2 um) e' superato da S1: stessi software e dati danno 3027 gruppi sul DGX, 2559 sul server, 538 sulla GPU. In S5 Table 10 riga 394, Risultati riga 398 e Discussione riga 430 usano i valori del DGX e dicono che il Leiden CPU a HD 2 um cambia con la macchina; non attribuire la divergenza a una causa (componenti connesse o stocasticita'): il protocollo del PoW-O non e' stato eseguito e richiede decisione del PI.
- **Decisione o convenzione:** D-01
- **Fonte:** s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um.dgx_cpu[0] (server_cpu e server_gpu per il confronto)
- **Dipende da:** D-01
- **Nota:** Contesto la premessa del PoW-O: la CPU a HD 2 um non e' riproducibile fra macchine, quindi 'CPU deterministica' (R0615) vale solo a macchina fissa.
- **Modificata in arbitrato:** target (vedi `arbitrati.csv`)

#### R0360 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 338); registro: UNSUPPORTED, critical
- **Ancora (univoca nel .md):** `End-to-end speedup increased from 1.7x on Visium v1 (2,695 spots) to 51.6x on Visium HD 8 um (393,543 bins) (Fig. 7)`
- **Valore:** 1.7x | 51.6x → 1.4138500544127761 | 6.868546906119942 | 10.426139539453574 ; controllo 1.6072574291799362 | 6.079115818835975 | 9.391911325890455
- **Istruzione:** Riga 338: sostituire "End-to-end speedup increased from 1.7x on Visium v1 (2,695 spots) to 51.6x on Visium HD 8 um (393,543 bins) (Fig. 7), demonstrating that GPU acceleration becomes increasingly valuable as spatial resolution increases." con "Against the DGX CPU reference, end-to-end GPU speedups were 1.4x on Visium v1 (2,695 spots), 6.9x on Visium HD 8 um (393,543 bins; co-occurrence excluded, see below) and 10.4x on Visium HD 2 um (389,492 bins) (Fig. 7). With the 128-thread server CPU as reference they were 1.6x, 6.1x and 9.4x: the choice of CPU changes the speedup by 10-14%, in different directions per platform." Togliere la clausola 'increasingly valuable as spatial resolution increases'. Valori in value_new nell'ordine v1 | HD 8 um | HD 2 um (riferimento DGX) poi controllo.
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0]; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_speedups.csv platform=visium step=total cpu=control_server convention=1_5; SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.control_server[0]; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=control_server convention=1_5; range 10-14%: S1.md In breve punto 4
- **Dipende da:** CONV; D-11; D-13
- **Assorbe:** R0287
- **Nota:** Le righe 367 e 370 (registro PASS, fuori piano) diventano false con S1: a HD 2 um lo speedup e' ora il piu' alto, Visium v1 scende a 1.4x; S5 le riscrive con gli stessi file. Il ligando-recettore a Visium v1 include ora il download OmniPath (S3.md).

#### R0362 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 342); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `co-occurrence analysis, which achieved a 3,272x speedup (from 3,573 s on CPU to 1.09 s on GPU; Fig. 8)`
- **Valore:** 3,272x | 3,573 s | 1.09 s → 4 | 8 | 49 | 0.00022028734855439325 | 0.9829900284836788 [0.9512110082296242; 1.0038022401843067] | 103.24464
- **Istruzione:** Riga 342: sostituire "The dominant contributor to the HD 8 um speedup was co-occurrence analysis, which achieved a 3,272x speedup (from 3,573 s on CPU to 1.09 s on GPU; Fig. 8)." con il risultato di D-13: "At Visium HD 8 um the GPU co-occurrence computed with rapids-singlecell 0.14.1 was incorrect: with the same 4 cell groups as the CPU, it matched the CPU result in only 8 of 49 distance intervals, because the number of bin pairs within the larger distance thresholds exceeds the range of the 32-bit integer counters. The GPU co-occurrence of the original March runs had the same defect. With rapids-singlecell 0.15.1 the GPU result matched the CPU in 49 of 49 intervals (maximum absolute difference 0.00022) at unchanged runtime (0.15.1/0.14.1 time ratio 0.98, 95% CI 0.95-1.00). Co-occurrence is therefore excluded from the Visium HD speedups; on the DGX CPU it took 103 s." Se il PI vuole anche uno speedup della sola co-occorrenza con 0.15.1, vedi pi_choices (default D-13: nessuno).
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_evaluation.json gates.G5.detail[visium_hd_square_008um].n_groups; SPATIAL/results_v2/cooc_check/cooc_check_eval.json hd8_rsc0141_equal_intervals, Q1_hd8_rsc0151_equal_intervals, Q1_hd8_rsc0151_max_abs_diff, Q3_ratio, Q3_ci; SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=co_occurrence col=mean_1_5; marzo con lo stesso difetto: SPATIAL/results_v2/s1_extra_numbers.json gpu_cooc_zero_slices
- **Dipende da:** D-13; CONV
- **Assorbe:** R0289
- **Nota:** Anche la frase della riga 343 e la spiegazione del rallentamento di marzo (numba a 1 thread dopo nhood_enrichment, S1 P2) vanno riportate; la seconda spetta ai Metodi (S3).

#### R0297 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** tabella:Table 9 riga Co-occurrence (riga 355); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Co-occurrence | 3,573 | 1.09 | 3,272x`
- **Valore:** 3,573 | 1.09 | 3,272x → 103.24464
- **Istruzione:** Riga 355, Table 9 "Co-occurrence | 3,573 | 1.09 | 3,272x": per D-13 la riga resta solo con il tempo CPU di riferimento e senza speedup: "Co-occurrence | 103.2 | n.r. | n.r." con nota "GPU result incorrect with rapids-singlecell 0.14.1 (int32 overflow); see text". In alternativa togliere la riga (scelta PI, vedi pi_choices).
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=co_occurrence col=mean_1_5
- **Dipende da:** D-13; R0295; R0362
- **Nota:** Il 3,271x proposto dal registro e' superato. Tempo GPU nella pipeline 2.55 s (0.14.1, risultato errato): non riportarlo come accelerazione.

#### R0326 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** tabella:Table 10 riga N clusters (riga 394); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `N clusters (CPU / GPU) | 16 / 15 | 7 / 3 | 2,559 / 538`
- **Valore:** 16 / 15 | 7 / 3 | 2,559 / 538 → dgx_cpu [16, 16, 16, 16, 16] [4, 4, 4, 4, 4] [3027, 3027, 3027, 3027, 3027]; server_gpu [15, 15, 15, 15, 15] [3, 4, 3, 3, 3] [538, 538, 538, 538, 538]; server_cpu [16, 16, 16, 16, 16] [7, 7, 7, 7, 7] [2559, 2559, 2559, 2559, 2559]
- **Istruzione:** Riga 394, Table 10 "N clusters (CPU / GPU) | 16 / 15 | 7 / 3 | 2,559 / 538": con il riferimento DGX scrivere "N clusters (CPU / GPU) | 16 / 15 | 4 / 3-4 | 3,027 / 538" con nota "GPU: 3 groups in four repeats, 4 in one; with the server CPU, 16, 7 and 2,559". Tutta Table 10 si rifa' dai JSON di concordanza nuovi. Righe di Table 10 da riscrivere esplicitamente in S5 (didascalia riga 384): riga 388 (Moran's I Spearman rho), 389 (Geary's C Spearman rho, oggi 0.9995 a HD 8 um), 390 (SVG Jaccard top 50), 391 (SVG Jaccard FDR < 0.05), 392 (Cluster ARI), 393 (Cluster NMI), ciascuna dai 6 JSON di concordanza di S1, riferimento DGX contro GPU, con il controllo server contro GPU in nota; registrare nel diario percorso e md5 dei JSON letti.
- **Decisione o convenzione:** D-11
- **Fonte:** SPATIAL/results_v2/s1_extra_numbers.json own_leiden_clusters; SPATIAL/results_v2/ file di concordanza (6 JSON: riferimento DGX contro GPU, controllo server contro GPU; percorso da rileggere sul server, non nel pacchetto)
- **Dipende da:** D-11; R0365
- **Nota:** Il problema 'modale contro media' (537 contro 538) scompare: nei nuovi run GPU HD 2 um dà 538 in 5 su 5.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0329 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 399); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `This 4.75x difference in cluster granularity arises from algorithmic differences between the leidenalg (CPU) and cuGraph (GPU) Leiden implementations, which ...`
- **Valore:** 4.75x | leidenalg → 5.63 (3027/538, s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um dgx_cpu[0] / server_gpu[0])
- **Istruzione:** Riga 399: "This 4.75x difference in cluster granularity arises from algorithmic differences between the leidenalg (CPU) and cuGraph (GPU) Leiden implementations...". Sostituire il rapporto con quello del riferimento DGX (cluster CPU dgx_cpu / cluster GPU server_gpu, HD 2 um, da calcolare in S5 e arrotondare a 2 decimali) e "leidenalg" con "igraph". La causa ("arises from algorithmic differences") va indebolita come in R0694.
- **Decisione o convenzione:** D-11
- **Fonte:** SPATIAL/results_v2/s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um (dgx_cpu, server_gpu)
- **Dipende da:** R0699; R0694
- **Nota:** Verifica S2: 3027/538 = 5.63. Il registro proponeva 4.76x sui cluster di marzo: superato.
- **Modificata in arbitrato:** value_new, depends_on (vedi `arbitrati.csv`)

#### R0572 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 413); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `The extension to spatial transcriptomics shows that GPU advantages are even more pronounced for spatial-specific operations, with co-occurrence analysis achi...`
- **Valore:** over three orders of magnitude speedup → 1.4; 6.9; 10.4
- **Istruzione:** Riga 413. La frase 'The extension to spatial transcriptomics shows that GPU advantages are even more pronounced for spatial-specific operations, with co-occurrence analysis achieving over three orders of magnitude speedup.' non vale più: i valori della revisione (7.4x, 6.4x, 41.5x, 3,272x, 67x, 29x) sono superati da S1 e per D-13 la co-occorrenza a Visium HD esce dagli speedup. Sostituire con: "The spatial benchmark, repeated with a fresh process per repeat and the same cell groups on CPU and GPU, gave end-to-end speedups of 1.4x (Visium v1), 6.9x (Visium HD 8 um, co-occurrence excluded) and 10.4x (Visium HD 2 um) against the 100-CPU DGX reference; among spatial-specific operations only spatial autocorrelation gained substantially, and GPU co-occurrence at Visium HD 8 um was incorrect in rapids-singlecell 0.14.1." Accanto ai valori di riferimento scrivere quelli del controllo sul server (1.6x, 6.1x, 9.4x), come chiede S5.md.
- **Decisione o convenzione:** D-13
- **Fonte:** s1_speedups.csv platform=visium step=total cpu=reference_dgx convention=1_5; s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx
- **Dipende da:** D-01; D-11; D-13; R0360
- **Nota:** A HD 2 um la co-occorrenza non gira, quindi il totale coincide con quello senza co-occorrenza. Il ricalcolo del registro (Moran/Geary 162x, vicini 1.0x) usa la CPU di marzo degradata: superato.
- **Modificata in arbitrato:** depends_on, source (vedi `arbitrati.csv`)

#### R0611 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 428); registro: UNSUPPORTED, critical
- **Ancora (univoca nel .md):** `The 3,272x speedup achieved for co-occurrence analysis on Visium HD 8 um data is, to our knowledge, the largest GPU speedup reported for any spatial transcri...`
- **Valore:** 3,272x → 8/49 (0.14.1); 49/49 (0.15.1); 0.983 [0.951; 1.004]
- **Istruzione:** Riga 428: sostituire la frase 'The 3,272x speedup achieved for co-occurrence analysis on Visium HD 8 um data is, to our knowledge, the largest GPU speedup ... across thousands of bins and spatial distance intervals simultaneously.'. I valori della revisione (29x, 67x, 2,088x) sono superati da S1; per D-13 la co-occorrenza a Visium HD esce dagli speedup e il difetto si riporta come risultato: "At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was incorrect: on the same 4 cell groups as the CPU it matched the CPU result at only 8 of 49 distances, because its 32-bit pair counters overflow at this number of bins. With rapids-singlecell 0.15.1 it matched at 49 of 49 distances in the same time (time ratio 0.983 [0.951; 1.004]), so we excluded co-occurrence from the Visium HD speedups." Lo speedup della sola co-occorrenza (40.4x in pipeline, 23.4x nella verifica) si scrive solo se il PI lo vuole come informazione (pi_choices).
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/cooc_check/cooc_check_eval.json campi hd8_rsc0141_equal_intervals, Q1_hd8_rsc0151_equal_intervals, Q3_ratio, Q3_ci; SPATIAL/results_v2/s1_extra_numbers.json own_leiden_clusters.visium_hd_square_008um.dgx_cpu; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_008um step=co_occurrence cpu=reference_dgx convention=1_5
- **Dipende da:** D-13; R0572; R0362
- **Assorbe:** R0334
- **Nota:** value_new vuoto: a HD la co-occorrenza non entra negli speedup (D-13).
- **Modificata in arbitrato:** value_new, depends_on (vedi `arbitrati.csv`)

#### R0612 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 428); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Spatial autocorrelation statistics (Moran's I, Geary's C) achieved similarly impressive speedups of 162-170x with near-perfect numerical concordance (rho >= ...`
- **Valore:** 162-170x → Moran 20.8-21.0; Geary 122.4-128.9; controllo server: Moran 9.3-13.1, Geary 55.1-75.6
- **Istruzione:** Riga 428: '162-170x' (e il '162-163x' proposto dalla revisione) è superato da S1. Sostituire 'achieved similarly impressive speedups of 162-170x' con: "were accelerated 20.8-21.0x (Moran's I) and 122.4-128.9x (Geary's C) on Visium HD". In S5 aggiungere i valori del controllo sul server accanto e scrivere che Moran sulla GPU resta più lento di Geary (circa 4 s contro meno di 1 s); sul Visium v1 Moran non accelera (0.5x).
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv step=spatial_autocorr_moran e spatial_autocorr_geary, platform=visium_hd_square_008um e visium_hd_square_002um, cpu=reference_dgx, convention=1_5
- **Dipende da:** D-01; D-11; R0366
- **Assorbe:** R0335, R0696
- **Nota:** Il '162-170x ok' del registro (rep2-5 di marzo) poggiava sulla CPU degradata dopo la prima ripetizione.
- **Modificata in arbitrato:** value_new, depends_on (vedi `arbitrati.csv`)

#### R0337 · S5 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 430); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `At 389,492 spatial bins with resolution parameter 0.1, local optima abound, and the leidenalg (CPU) and cuGraph (GPU) implementations explore this landscape ...`
- **Valore:** leidenalg → igraph
- **Istruzione:** Riga 430: in 'the leidenalg (CPU) and cuGraph (GPU) implementations' sostituire leidenalg con igraph (flavor='igraph' in benchmark_spatial_cpu.py righe 322-337). In S5 confermare che il rerun di S1 usa lo stesso flavor.
- **Fonte:** righe_da_pianificare.csv id=R0337 campo recomputed (SPATIAL/scripts/benchmark_spatial_cpu.py righe 322-337)
- **Nota:** Come A0265 (Metodi, T2).

#### R0719 · S7 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** tabella:Table 2 riga PCA loading (riga 101); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `| PCA loading |rho| |`
- **Valore:** PCA loading |rho| → \|rho\|
- **Istruzione:** Table 2, riga 101: le barre non protette in "PCA loading |rho|" spezzano la cella in pandoc. Scrivere "PCA loading \|rho\|" (come nella copia di stile) oppure "PCA loading mean absolute rho". Farlo nel .md prima della rigenerazione LaTeX.
- **Fonte:** righe_da_pianificare.csv id=R0719 campo note


## L2 · riformulazione (186 voci)

#### R0001 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 2); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `title: "GPU-accelerated single-cell and spatial transcriptomics on NVIDIA DGX H100: a systematic benchmark of speed, scalability, and biological concordance"`
- **Valore:** on NVIDIA DGX H100 → (da rileggere, vedi fonte)
- **Istruzione:** Riga 2: 'on NVIDIA DGX H100' copre anche lo spatial, la cui GPU e' la RTX 4090 della workstation (dopo S1 la CPU di riferimento spatial e' il nodo DGX poddgx02, D-11). Qualunque titolo scelga il PI in R0730 deve nominare l'hardware per modalita' (es. "single-cell (NVIDIA DGX H100) and spatial (RTX 4090)") oppure non nominare hardware. Controllare la stessa attribuzione nelle righe 14 e 44.
- **Decisione o convenzione:** PI-S3
- **Fonte:** righe_da_pianificare.csv R0001 recomputed (gpu_name RTX 4090 nei JSON spatial); S1.md (riferimento CPU DGX)
- **Dipende da:** R0730; D-11
- **Assorbe:** R0253, R0559

#### R0007 · S3 · P2 (dataset Census) · correggere
- **Bersaglio:** prosa (riga 14); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `We present a systematic benchmark comparing Scanpy (CPU, 100 cores) against rapids-singlecell (GPU, 1-8 NVIDIA H100 80 GB) on the 1.3-million mouse brain cel...`
- **Valore:** on the 1.3-million mouse brain cell dataset → 2025-11-08
- **Istruzione:** Riga 14, frase 'on the 1.3-million mouse brain cell dataset': il dataset non e' il 10x E18 di Zheng2017 ma 1.300.000 cellule di cervello di topo campionate da CELLxGENE Census (release 2025-11-08; 39.182 geni dopo QC, incompatibili con i 27.998 del file 10x). Sostituire con "on up to 1.3 million mouse brain cells sampled from CELLxGENE Census" (forma breve per l'abstract), coerente con la correzione dei Metodi riga 53. Applicare nel nuovo abstract di R0731.
- **Fonte:** righe_da_pianificare.csv R0007 recomputed (scripts/download_data.py, Census 2025-11-08)
- **Dipende da:** R0731; R0024
- **Nota:** R0024 = riga dei Metodi sul dataset (T2), da applicare prima per coerenza.

#### R0240 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 14); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `Multi-GPU scaling was sublinear due to CPU preprocessing dominance`
- **Valore:** Multi-GPU scaling was sublinear due to CPU preprocessing dominance. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 14, frase 'Multi-GPU scaling was sublinear due to CPU preprocessing dominance.': nessuno step e' stato distribuito (PCA e vicini su GPU 0; PCA+vicini 17.23/16.99/17.01 s con 2/4/8 GPU a 1.3M). Per D-02 sostituire con "In the multi-GPU configuration tested, additional GPUs did not take part in the computation." (oppure toglierla se l'abstract supera 250 parole: la frase dei Metodi/Risultati resta). Righe 37-39 dell'Introduction, nella stessa sessione dell'abstract (la riga 37 e' anche l'ancora di R0732: comporre il testo in una sola passata). A riga 38 (ancora "relative to Scanpy on identical hardware") togliere "on identical hardware": CPU e GPU scRNA sono girati su nodi e allocazioni diversi (R0448) e lo spatial confronta macchine diverse (D-11). A riga 39 (ancora "Second, scalability: how does the pipeline scale from 1 to 8 GPUs") la domanda per D-02 va riscritta: proposta "Second, multi-GPU allocation: does allocating more GPUs of the node change runtime in the configuration used?" oppure togliere la domanda e scrivere "four questions".
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv R0240 recomputed (tracks/A_work/a03_multigpu.py); decisioni_D01_D13.txt D-02
- **Dipende da:** R0731; D-02
- **Assorbe:** R0638
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0565 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `We present a systematic benchmark comparing Scanpy (CPU, 100 cores) against rapids-singlecell (GPU, 1-8 NVIDIA H100 80 GB) on the 1.3-million mouse brain cel...`
- **Valore:** Scanpy (CPU, 100 cores) against rapids-singlecell (GPU, 1-8 NVIDIA H100 80 GB) → (da rileggere, vedi fonte)
- **Istruzione:** Riga 14, frase 'Scanpy (CPU, 100 cores) against rapids-singlecell (GPU, 1-8 NVIDIA H100 80 GB) ... with five independent repeats': (a) '100 cores' sono 100 CPU logiche (SLURM --cpus-per-task=100 su nodo da 224 CPU logiche): scrivere "100 logical CPUs"; (b) '1-8 NVIDIA H100' suggerisce calcolo distribuito, che non c'e' stato (D-02): scrivere "NVIDIA H100 GPUs" e togliere 'multi-GPU scalability' dall'elenco di cio' che si valuta; (c) le ripetizioni girano nello stesso processo Python: scrivere "five repeats per configuration" senza 'independent'. Applicare nel nuovo abstract di R0731 e nella frase corrispondente dei Metodi.
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv R0565 recomputed; slurm/cpu_benchmark.sh; scripts/benchmark_multigpu.py
- **Dipende da:** R0731; D-02
- **Nota:** S2_P1_threads.csv: lo scRNA CPU non ha il difetto dei thread, ma le ripetizioni restano nello stesso processo; 'independent' va tolto comunque.

#### R0566 · S3 · P8 (peso del Wilcoxon nel 120x) · riformulare
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `The GPU pipeline achieved up to 120-fold end-to-end speedup at 1.3M cells (435 s vs 52,056 s on CPU), reducing a 14.5-hour analysis to 7.3 minutes`
- **Valore:** 120-fold → 119.6 (8 GPU allocate, r1-5); 105.5 (2 GPU, r1-5); DE 93.5%; senza DE 7.9-9.2
- **Istruzione:** Riga 14, frase '120-fold end-to-end speedup at 1.3M cells (435 s vs 52,056 s on CPU)': i numeri tornano con la convenzione A (media r1-5: 119.62x con il run a 8 GPU allocate), ma (a) con 2 GPU lo speedup e' 105.5x e la differenza e' tutta nel caricamento dati su nodi diversi (D-02); (b) il Wilcoxon di Scanpy e' il 93.5% del tempo CPU a 1.3M e senza DE lo speedup e' 7.9-9.2x. Riscrivere: "At 1.3 million cells the GPU pipeline took 435 s against 52,056 s on CPU (119.6-fold; 105.5-fold in a run that differed only in data loading). Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold." Si puo' tenere '14.5 hours to 7.3 minutes' solo se le parole lo consentono.
- **Decisione o convenzione:** CONV
- **Fonte:** S2_P3_convenzione.csv n=1300000 gpu=gpu8 e gpu=gpu2 colonna spd_r1_5; righe_da_pianificare.csv R0566 recomputed (tracks/F_work/f02_speedup_with_without_DE.csv)
- **Dipende da:** CONV; D-02; R0558; R0082
- **Nota:** Con la convenzione 2-5 il valore a 8 GPU sarebbe 121.9 (S2_P3_convenzione.csv spd_r2_5): la voce si rigenera se il PI sceglie diversamente.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0567 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Biological concordance was high: HVG selection was identical (Jaccard = 1.0), PCA loadings perfectly correlated (Spearman |rho| = 1.0), and Leiden clustering...`
- **Valore:** Biological concordance was high → (da rileggere, vedi fonte)
- **Istruzione:** Riga 14, frase 'Biological concordance was high: HVG selection was identical (Jaccard = 1.0), PCA loadings perfectly correlated (Spearman |rho| = 1.0), and Leiden clustering concordance ranged from ARI = 0.908 to 0.963': i valori sono giusti ma misurati solo a 10.000 cellule, su un run dell'11 marzo diverso da quelli cronometrati; la letteratura riporta ARI CPU-GPU intorno a 0.5 a scala maggiore. Togliere 'Biological concordance was high' come proprieta' del benchmark e scrivere "At 10,000 cells, HVG selection was identical (Jaccard = 1.0), PCA loadings were perfectly correlated (Spearman |rho| = 1.0) and Leiden clustering agreed with ARI 0.908-0.963." Applicare in R0731.
- **Fonte:** righe_da_pianificare.csv R0567 recomputed (results/concordance_10000_r1.json)
- **Dipende da:** R0731
- **Nota:** Valori invariati (R0009 PASS).

#### R0568 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `A memory-optimised pipeline processed 11.9 million cells on a single DGX H100 node, with CPU RAM as the binding constraint (GPU VRAM at 7.6% of capacity)`
- **Valore:** (GPU VRAM at 7.6% of capacity) → 3,436,470
- **Istruzione:** Riga 14, frase 'A memory-optimised pipeline processed 11.9 million cells on a single DGX H100 node, with CPU RAM as the binding constraint (GPU VRAM at 7.6% of capacity)': oltre 3,436,470 cellule il dataset e' replicato con copie esatte (non dichiarato); il 7.6% misura pool RMM riservati; il vincolo di RAM host e' della pipeline con preprocessing Scanpy su CPU. Riscrivere: "A memory-optimised pipeline processed 11.9 million cells, built from copies of a 3,436,470-cell dataset, on one node, limited by host RAM." Togliere '(GPU VRAM at 7.6% of capacity)' o riscriverlo come pool riservato. Applicare in R0731.
- **Fonte:** righe_da_pianificare.csv R0568 recomputed (scripts/benchmark_maxpower.py resize_dataset)
- **Dipende da:** R0731

#### R0639 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `These results identify CPU-side preprocessing as the primary bottleneck and provide practical guidance for deploying GPU-accelerated workflows at atlas scale`
- **Valore:** CPU-side preprocessing as the primary bottleneck → (da rileggere, vedi fonte)
- **Istruzione:** Riga 14, 'These results identify CPU-side preprocessing as the primary bottleneck': il preprocessing e' su CPU per scelta della pipeline ibrida (rsc 0.14.1 ha percorsi GPU/Dask) e nella pipeline a 1 GPU a 100k QC+normalizzazione+HVG pesano 0.30 s su 14.77 s (caricamento 5.65 s); a 1.3M il peso dominante sul lato CPU e' il Wilcoxon (R0566). Versione ponderata: "In this hybrid pipeline, the steps left on the CPU and the choice of differential expression test bounded the achievable speedup." Togliere 'primary bottleneck' e 'practical guidance ... at atlas scale' se non c'e' spazio. Stessa formula alla riga 44 (R0256) e nelle Conclusioni righe 437 e 441 (traccia T4).
- **Fonte:** righe_da_pianificare.csv R0639 recomputed (tracks/F_work/f00_runs.csv); R0566
- **Dipende da:** R0731; R0566
- **Nota:** La riga dei Risultati che la sostiene va scelta in S3 (scomposizione per step, Results riga 183 e seguenti).

#### R0471 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 22); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Single-cell RNA sequencing has become the standard technology for dissecting cellular heterogeneity in complex tissues [@Regev2017]`
- **Valore:** has become the standard technology → (da rileggere, vedi fonte)
- **Istruzione:** Riga 22, 'has become the standard technology for dissecting cellular heterogeneity in complex tissues [@Regev2017]': Regev2017 (white paper del 2017) non dice che scRNA-seq sia lo standard. Riscrivere: "Single-cell RNA sequencing is now widely used to dissect cellular heterogeneity in complex tissues [@Heumos2023]." (Heumos2023 e' gia' nel .bib).
- **Fonte:** righe_da_pianificare.csv R0471 recomputed; cibb2026_references.bib chiave Heumos2023
- **Assorbe:** R0013

#### R0472 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 23); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Recent atlas-scale projects such as the Human Cell Atlas [@Regev2017], Tabula Sapiens [@TabulaSapiens2022], and the Allen Brain Atlas [@Yao2023] routinely ge...`
- **Valore:** the Allen Brain Atlas [@Yao2023] routinely generate → (da rileggere, vedi fonte)
- **Istruzione:** Riga 23, 'Recent atlas-scale projects such as the Human Cell Atlas [@Regev2017], Tabula Sapiens [@TabulaSapiens2022], and the Allen Brain Atlas [@Yao2023] routinely generate datasets ...': Regev2017 e' il white paper di un progetto proposto e non riporta dataset; Yao2023 e' l'atlante Allen dell'intero cervello murino, non l''Allen Brain Atlas' ISH. Riscrivere: "Atlas-scale projects such as Tabula Sapiens [@TabulaSapiens2022] and the whole-mouse-brain atlas of the Allen Institute [@Yao2023] have produced datasets of hundreds of thousands to millions of cells, and the Human Cell Atlas initiative [@Regev2017] plans to extend such maps to all human tissues, placing severe computational demands on analysis pipelines." Se il PI vuole tenere HCA fra chi genera dataset, serve una citazione di un dataset HCA o del portale.
- **Fonte:** righe_da_pianificare.csv R0472 recomputed (Crossref 10.1126/science.abl4896, 10.1038/s41586-023-06812-z; eLife 27041)
- **Assorbe:** R0014
- **Nota:** La parte 'plans to extend ... to all human tissues' parafrasa lo scopo del white paper: S3 la controlla sul testo di Regev2017 prima di scriverla.

#### R0015 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 24); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `The dominant analysis framework, Scanpy [@Wolf2018], executes on CPU and relies on NumPy, SciPy, and scikit-learn for linear algebra and graph operations`
- **Valore:** The dominant analysis framework → (da rileggere, vedi fonte)
- **Istruzione:** Riga 24, 'The dominant analysis framework, Scanpy [@Wolf2018], executes on CPU and relies on NumPy, SciPy, and scikit-learn': track E (R0473, PASS) conferma le dipendenze ma 'dominant' non e' nella fonte. Riscrivere: "The widely used analysis framework Scanpy [@Wolf2018] runs on the CPU and builds on NumPy, SciPy and scikit-learn for linear algebra and graph operations."
- **Fonte:** revisione_n2_log.csv R0473 (PASS, nota su 'dominant')
- **Nota:** UNVERIFIABLE del track A risolta dalla lettura del track E.

#### R0020 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 35); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `[-@Gardner2025] recently evaluated accuracy-performance trade-offs for GPU single-cell analysis, but their study was limited to a single GPU and did not expl...`
- **Valore:** but their study was limited to a single GPU → 0.45-0.55
- **Istruzione:** Riga 35, 'Gardner et al. [-@Gardner2025] ... but their study was limited to a single GPU and did not explore multi-GPU configurations or stress-test hardware limits': la limitazione citata e' vera (R0478 PASS) ma, con D-02, il capitolo non ha misurato calcolo multi-GPU e non puo' usarla come contrasto; inoltre la citazione omette il risultato principale di Gardner sulla concordanza (ARI CPU-GPU mediana 0.45-0.55). Riscrivere: "Gardner et al. [-@Gardner2025] evaluated accuracy-performance trade-offs on a single H100 and found that CPU and GPU clusterings were not interchangeable (median ARI 0.45-0.55)." Il confronto con il proprio ARI (solo a 10.000 cellule) va nella Discussione.
- **Decisione o convenzione:** D-02
- **Fonte:** peer_review.md sezione 1, riga Gardner et al. 2025 (colonna Concordanza)
- **Dipende da:** R0538; D-02
- **Nota:** Riga del track A UNVERIFIABLE: la fonte e' stata letta dal track F; il valore va ricontrollato sul PDF di Gardner2025 in S3.

#### R0732 · S3 · P1 (titolo, abstract, estensione) · aggiungere
- **Bersaglio:** prosa (riga 37); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Here we present a comprehensive benchmark addressing five questions simultaneously.`
- **Istruzione:** Il capitolo deve dichiarare l'aspetto esteso rispetto allo short paper. Per D-01 l'estensione e' il nuovo riferimento CPU spatial. Nell'Introduzione, alla fine del paragrafo dei contributi, aggiungere: "This chapter extends our CIBB 2026 short paper with a new CPU reference for the spatial benchmark, in which every repeat runs in a fresh process and CPU and GPU spatial statistics use the same cell groups; it corrects a thread-count defect in the original CPU timings and reveals an integer-overflow error in GPU co-occurrence at Visium HD 8 um that rapids-singlecell 0.15.1 fixes." La stessa estensione deve comparire nell'abstract nuovo (R0731) e, se il PI vuole, nel titolo (R0730). Se le voci su DE (R0558) e determinismo (R0249) sono applicate, si possono citare come analisi aggiunte.
- **Decisione o convenzione:** D-01
- **Fonte:** decisioni_D01_D13.txt D-01; S1.md In breve; revisione_n2_log.csv R0732
- **Dipende da:** D-01;R0730;R0731;R0646;R0655
- **Nota:** La proposta del registro (baseline spatial, pseudo-bulk sui conteggi, multi-GPU vero) e' superata: D-02 e D-04 escludono nuovi run, resta solo D-01.
- **Modificata in arbitrato:** anchor, line, quality (vedi `arbitrati.csv`)

#### R0022 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 41); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Fourth, capacity: what is the maximum dataset size a single DGX H100 node can process, and what limits it?`
- **Valore:** what is the maximum dataset size a single DGX H100 node can process → (da rileggere, vedi fonte)
- **Istruzione:** Riga 41, 'Fourth, capacity: what is the maximum dataset size a single DGX H100 node can process, and what limits it?': la capacita' misurata e' quella della pipeline ibrida (preprocessing Scanpy su CPU) su dati replicati oltre 3,436,470 cellule, non dell'hardware. Riscrivere: "Fourth, capacity: how many cells can the hybrid pipeline process on one DGX H100 node, and which resource limits it?"
- **Fonte:** righe_da_pianificare.csv R0568 recomputed; peer_review.md sezione 1 punto 4 (Capacita')
- **Dipende da:** R0568
- **Nota:** Riga UNVERIFIABLE (domanda senza numeri) risolta con riformulazione (regola 4).

#### R0256 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 44); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `We benchmark both modalities on NVIDIA DGX H100 and RTX 4090 hardware, provide all code and containers for full reproducibility, and identify CPU-side prepro...`
- **Valore:** provide all code and containers for full reproducibility → (da rileggere, vedi fonte)
- **Istruzione:** Riga 44, 'We benchmark both modalities on NVIDIA DGX H100 and RTX 4090 hardware, provide all code and containers for full reproducibility, and identify CPU-side preprocessing as the primary bottleneck': (a) lo scRNA gira sul DGX (CPU e GPU), lo spatial ha GPU RTX 4090 e, dopo S1, CPU di riferimento sul nodo DGX poddgx02 con controllo sulla CPU della workstation (D-11); (b) 'full reproducibility' non regge per lo spatial di marzo (Dockerfile non pinnato, script delle figure 7-9 che non riproducono i PNG); S1 usa un'immagine identificata dal digest (D-12). Riscrivere: "We ran single-cell analyses on an NVIDIA DGX H100 node and spatial analyses on an RTX 4090 workstation against the same 100-CPU DGX reference, and we release code, container images identified by digest and per-run results." La parte sul collo di bottiglia segue R0639.
- **Decisione o convenzione:** D-11
- **Fonte:** righe_da_pianificare.csv R0256 recomputed; decisioni_D01_D13.txt D-11, D-12
- **Dipende da:** R0639; D-11; D-12
- **Nota:** Gli script delle figure 7-9 si rifanno in S5; la frase si tiene solo se S5 li rende riproducibili.

#### R0024 · S3 · P2 (dataset Census) · correggere
- **Bersaglio:** prosa (riga 53); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `All single-cell experiments used the 10x Genomics 1.3-million mouse brain cell dataset (E18) [@Zheng2017], obtained as a pre-processed AnnData h5ad file from...`
- **Valore:** the 10x Genomics 1.3-million mouse brain cell dataset (E18) [@Zheng2017], obtained as a pre-processed AnnData h5ad file from the RAPIDS single-cell examples repository → 2025-11-08; 1,300,000; 3,436,470; 202
- **Istruzione:** Riga 53: sostituire l'intera frase "All single-cell experiments used the 10x Genomics 1.3-million mouse brain cell dataset (E18) [@Zheng2017], obtained as a pre-processed AnnData h5ad file from the RAPIDS single-cell examples repository." con: "All single-cell experiments used mouse brain cells from the CZ CELLxGENE Census (version 2025-11-08) [@CZCellxGene2025]: primary-data cells (`is_primary_data`) with `tissue_general` = brain profiled with 10x Genomics 3' chemistry (v1 to v3), 3,436,470 cells from multiple studies. For the scaling benchmark we drew 1,300,000 of these cells uniformly at random without replacement (seed = 42)." Aggiungere al .bib la voce CZ CELLxGENE Discover (Nucleic Acids Research, 2025) con chiave CZCellxGene2025 e metadati letti da Crossref in S3 (non presenti nel pacchetto). Prima di scrivere rileggere sul server, in sola lettura, scripts/download_data.py (CENSUS_VERSION, obs_filter, download_from_census) per confermare filtro e versione; il numero di donatori 202 e' contato sul sottocampione da 3,4M del DE (de_benchmark_pseudobulk.json, 3,399,892 cellule) e va nella frase del DE (R0425), non qui; se si vuole il numero di donatori della selezione completa, contarlo in S3 in sola lettura (donor_id delle 3,436,470 cellule) e scriverlo solo dopo il conteggio.
- **Fonte:** righe_da_pianificare.csv id=R0024 campo recomputed (census_version, 1,300,000, 202 donatori); id=R0547 campo recomputed (3,436,470); server: scripts/download_data.py righe 25-100
- **Assorbe:** R0384, R0547
- **Nota:** Primaria P2. Ripercussioni fuori traccia: abstract, Limitazioni riga 432 (R0223, R0619), confronti con Nolet2022 e Dicks2026 'sullo stesso dataset'.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0479 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** prosa; bib:Zheng2017 (riga 53); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `All single-cell experiments used the 10x Genomics 1.3-million mouse brain cell dataset (E18) [@Zheng2017]`
- **Valore:** [@Zheng2017] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 53: togliere [@Zheng2017] come fonte del dataset (Zheng2017 descrive il sistema a goccioline e i 68k PBMC, non un dataset di 1,3M cellule di cervello E18) e citare al suo posto CZ CELLxGENE Census (R0024). Poi cercare nel .md le altre occorrenze di @Zheng2017 (oggi solo riga 53): se non ne restano, togliere la voce Zheng2017 dal .bib. Se nei Risultati o nella Discussione resta un confronto con Nolet2022 o Dicks2026 sul dataset 10x E18, lì va citata la pagina dataset 10x Genomics (2017) come risorsa, non Zheng2017.
- **Fonte:** righe_da_pianificare.csv id=R0479 campo recomputed (Crossref 10.1038/ncomms14049)
- **Dipende da:** R0024

#### R0025 · S3 · P2 (dataset Census) · togliere
- **Bersaglio:** prosa (riga 54); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `This dataset is the canonical large-scale single-cell benchmark and contains approximately 1.3 million cells with gene expression measured by the 10x Chromiu...`
- **Valore:** This dataset is the canonical large-scale single-cell benchmark and contains approximately 1.3 million cells with gene expression measured by the 10x Chromium platform. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 54: togliere la frase "This dataset is the canonical large-scale single-cell benchmark and contains approximately 1.3 million cells with gene expression measured by the 10x Chromium platform." Chimica e numero di cellule sono già nel nuovo testo di R0024; il dataset analizzato non è il benchmark canonico 10x. Se serve il numero dopo QC, metterlo in Table 4 e non qui.
- **Fonte:** righe_da_pianificare.csv id=R0025 campo recomputed (1,299,956 dopo QC)
- **Dipende da:** R0024
- **Assorbe:** R0385, R0715

#### R0386 · S3 · P2 (dataset Census) · correggere
- **Bersaglio:** prosa (riga 56); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `To evaluate performance across scales, we created reproducible subsamples of 10,000, 50,000, 100,000, and 500,000 cells by uniform random sampling without re...`
- **Valore:** NumPy 2.2.6, seed = 42), in addition to the full 1.3M cell dataset → (da rileggere, vedi fonte)
- **Istruzione:** Riga 56: nella parentesi "(`numpy.random.choice`, NumPy 2.2.6, seed = 42)" togliere "NumPy 2.2.6" (la versione usata al momento del sottocampionamento non è registrata; 2.2.6 è quella dei benchmark) e sostituire "in addition to the full 1.3M cell dataset" con "in addition to the 1.3M-cell sample". Prima di scrivere leggere sul server create_subsamples in scripts/download_data.py (righe 107-136) per stabilire da quale file sono estratti i sottocampioni da 10k a 500k (campione da 1,3M o selezione Census) e correggere di conseguenza la riga 57 ("derived from the same parent dataset").
- **Fonte:** righe_da_pianificare.csv id=R0386 campo recomputed; server: scripts/download_data.py righe 80-83 e 107-136
- **Dipende da:** R0024
- **Assorbe:** R0026
- **Nota:** Il target make download-data usa --max-cells 100000 (Makefile riga 35): gestito in R0454.

#### R0387 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 61); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Both the CPU and GPU pipelines implemented the standard Scanpy best-practices workflow [@Luecken2019; @Heumos2023] with identical parameters`
- **Valore:** with identical parameters → (da rileggere, vedi fonte)
- **Istruzione:** Riga 61: sostituire la frase con "Both the CPU and GPU pipelines implemented the standard Scanpy workflow (cf. [@Luecken2019; @Heumos2023]) with the same parameter values, except for the implementation-specific settings listed in Table 1 (Leiden iterations, PCA solver and neighbour search)." Le differenze vanno scritte nelle righe di Table 1 degli step 6, 7 e 8 (righe 76, 77 e 78 del .md) (R0398, R0391, R0400).
- **Fonte:** righe_da_pianificare.csv id=R0387 campo recomputed (benchmark_cpu.py righe 236-240; benchmark_gpu.py righe 306-308)
- **Dipende da:** R0391; R0398; R0400
- **Assorbe:** R0651
- **Nota:** La differenza di iterazioni di Leiden incide su ARI e NMI: la Discussione sulla concordanza va adeguata nelle tracce T3 e T5.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0480 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 61); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Both the CPU and GPU pipelines implemented the standard Scanpy best-practices workflow [@Luecken2019; @Heumos2023] with identical parameters`
- **Valore:** standard Scanpy best-practices workflow [@Luecken2019; @Heumos2023] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 61: "implemented the standard Scanpy best-practices workflow [@Luecken2019; @Heumos2023]" diventa "implemented the standard Scanpy workflow (cf. [@Luecken2019; @Heumos2023])" (frase completa in R0387). Luecken2019 raccomanda scran e nessuno scaling, mentre la pipeline usa normalize_total con log1p e scaling: non è la loro best practice. In S3 aprire Heumos2023 (testo non letto nella revisione) e, se non sostiene nemmeno il flusso, lasciare solo 'cf.'.
- **Fonte:** righe_da_pianificare.csv id=R0480 campo recomputed
- **Dipende da:** R0387
- **Assorbe:** R0027

#### R0029 · S3 · P5 (bibliografia) · verificare-in-step
- **Bersaglio:** prosa; bib:Virshup2024 (riga 63); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Both pipelines shared the AnnData format [@Virshup2024] for data interchange`
- **Istruzione:** Riga 63: nessuna modifica del testo attesa. In S3 confrontare la voce Virshup2024 del .bib (anndata, JOSS 9(101):4371, doi 10.21105/joss.04371) con Crossref; se titolo, autori e anno coincidono, chiudere la voce senza modifiche.
- **Fonte:** cibb2026_references.bib voce Virshup2024; Crossref doi 10.21105/joss.04371

#### R0390 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 65); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The pipeline comprised ten steps, each timed independently using `time.perf_counter()` (Table 1)`
- **Valore:** each timed independently using `time.perf_counter()` → (da rileggere, vedi fonte)
- **Istruzione:** Riga 65: sostituire "The pipeline comprised ten steps, each timed independently using `time.perf_counter()` (Table 1)." con "The pipeline comprised ten steps (Table 1), timed with `time.perf_counter()`; scaling (step 5) was timed together with PCA (step 6), and each of the three Leiden resolutions had its own timer. The reported total is the sum of the timed steps, not the wall-clock time of the job: RMM initialisation, the GPU warm-up, the copy of `adata.raw`, HVG subsetting and Dask cluster start-up and shutdown were not timed." In Table 1, step 5 Scaling (riga 75 del .md), aggiungere nella nota "timed with PCA".
- **Fonte:** righe_da_pianificare.csv id=R0390 campo recomputed (11 chiavi di timing); peer_review.md H10
- **Assorbe:** R0030
- **Nota:** Lo speedup 'PCA' dei Risultati include lo scaling: da dire nella traccia T3.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0391 · S3 · P10 (concordanza) · correggere
- **Bersaglio:** tabella:Table 1 (riga 67); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `: **Table 1.** Pipeline steps, parameters, and implementations for the scRNA-seq benchmark. All steps used identical parameters for the CPU and GPU pipelines...`
- **Valore:** All steps used identical parameters for the CPU and GPU pipelines except where noted. → (da rileggere, vedi fonte)
- **Istruzione:** Didascalia di Table 1 (riga 67): la frase "All steps used identical parameters for the CPU and GPU pipelines except where noted." resta, ma diventa vera solo se la tabella indica le differenze: step 6 PCA, riga 76 (R0398); step 7 vicini, riga 77 ("CPU: Scanpy default k-NN; GPU: brute-force k-NN, rapids-singlecell default"); step 8 Leiden, riga 78 (R0400). Per la riga 7 leggere in benchmark_cpu.py il metodo dei vicini effettivamente chiamato prima di scrivere 'Scanpy default'.
- **Fonte:** righe_da_pianificare.csv id=R0387 campo recomputed (GPU default algorithm brute); server: scripts/benchmark_cpu.py
- **Dipende da:** R0398; R0400
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0398 · S3 · P10 (concordanza) · correggere
- **Bersaglio:** tabella:Table 1 riga 6 PCA (riga 76); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `| 6 | PCA | 50 components, seed = 42 | Truncated SVD |`
- **Valore:** Truncated SVD → (da rileggere, vedi fonte)
- **Istruzione:** Table 1, riga 6, colonna Implementation note: sostituire "Truncated SVD" con "CPU: scikit-learn PCA (ARPACK) on the dense scaled matrix; GPU: cuML PCA (`svd_solver` auto)". La PCA a covarianza dello stress test si descrive in riga 110 (R0420).
- **Fonte:** righe_da_pianificare.csv id=R0398 campo recomputed (sklearn PCA con arpack; cuML PCA, svd_solver auto)

#### R0704 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 82); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Only the pool corresponding to the BLAS library that NumPy was linked against at build time is actually active at runtime; the other variables are harmlessly...`
- **Valore:** to 100 (the usable core count) → (da rileggere, vedi fonte)
- **Istruzione:** Riga 82: riscrivere il paragrafo come "For the CPU pipeline, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `NUMBA_NUM_THREADS` were set to 100, the number of CPUs allocated by SLURM, before any numerical library was imported, so that the OpenMP, BLAS and Numba thread pools used by NumPy, SciPy, scikit-learn and umap-learn were all sized to the allocation." Togliere le frasi "Only the pool corresponding to the BLAS library ... harmlessly ignored." e "We set all four ... NumPy is linked against OpenBLAS." (contraddittorie: OpenMP e Numba sono attivi a prescindere dalla BLAS). Anche "(the usable core count)" va tolto: con CR_CORE e 2 thread per core 100 CPU sono 50 core fisici con 100 thread (D-12 punto 3); prima di scriverlo leggere slurm/cpu_benchmark.sh sul server.
- **Fonte:** righe_da_pianificare.csv id=R0704; decisioni_D01_D13.txt D-12 punto 3; server: slurm/cpu_benchmark.sh
- **Assorbe:** R0460
- **Nota:** Il '100 = usable core count' non è nel registro: segnalato qui da D-12 e da peer_review.md (100 CPU su 224 logiche).

#### R0459 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 83); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `For single-GPU runs, the RMM pool allocator was initialised to pre-reserve GPU VRAM and amortise allocation cost across many small operations; a GPU warmup s...`
- **Valore:** the RMM pool allocator was initialised to pre-reserve GPU VRAM and amortise allocation cost across many small operations; a GPU warmup step was then executed to absorb CUDA contex → initial_pool 50%; 100x100
- **Istruzione:** Riga 83: sostituire la frase con "For single-GPU runs, RMM was initialised with a pool allocator reserving 50% of the device memory for cuML and cuGraph; CuPy was not redirected to RMM, so CuPy arrays, which hold most rapids-singlecell data, were allocated outside the pool. Before timing, a 100 x 100 matrix product created the CUDA context; it does not compile the rapids-singlecell kernels, so the first repeat also includes JIT compilation." Prima di scrivere rileggere scripts/benchmark_gpu.py righe 159-207 sul server (rmm.reinitialize, assenza di set_allocator).
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0459 campo recomputed; server: scripts/benchmark_gpu.py righe 159-207
- **Dipende da:** CONV
- **Nota:** La frase sulla prima ripetizione vale per la convenzione A (r1 inclusa).

#### R0044 · S3 · P3 (multi-GPU) · verificare-in-step
- **Bersaglio:** prosa (riga 87); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `For datasets exceeding single-GPU VRAM capacity (500k and 1.3M cells), we employed a hybrid multi-GPU pipeline using Dask-CUDA [@Rocklin2015]`
- **Valore:** For datasets exceeding single-GPU VRAM capacity (500k and 1.3M cells) → (da rileggere, vedi fonte)
- **Istruzione:** Prima di scrivere l'ultima frase del paragrafo di R0407 cercare sul server, in sola lettura, log SLURM o output dei job a 1 GPU a 500000 e 1300000 cellule (file non tracciati, D-07; per esempio *.out o logs/ sotto slurm/) con l'errore di memoria. Se il log c'è, scrivere "Results at 500k and 1.3M cells come only from this configuration, because the single-GPU pipeline ran out of device memory at these sizes."; se non c'è, scrivere "The single-GPU pipeline was not run at 500k and 1.3M cells; results at these sizes come only from this configuration." e allineare Table 4 e Limitazioni riga 432 (R0627, traccia T5).
- **Fonte:** server: log SLURM dei job gpu_1 (non nel pacchetto); righe_da_pianificare.csv id=R0044
- **Nota:** Nessun JSON gpu_500000 o gpu_1300000 nel repo; la RMM pool non usata da CuPy (R0459) può aver contribuito all'OOM.

#### R0487 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** prosa (riga 87); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `we employed a hybrid multi-GPU pipeline using Dask-CUDA [@Rocklin2015]`
- **Valore:** Dask-CUDA [@Rocklin2015] → (da rileggere, vedi fonte)
- **Istruzione:** Nel nuovo paragrafo di R0407 la citazione è "a Dask [@Rocklin2015] and Dask-CUDA [@RAPIDS2024] cluster": Rocklin2015 descrive Dask su CPU e non Dask-CUDA. RAPIDS2024 è già nel .bib.
- **Fonte:** righe_da_pianificare.csv id=R0487 campo note
- **Dipende da:** R0407

#### R0539 · S3 · P12 (novità e posizionamento) · aggiungere
- **Bersaglio:** prosa riga 418 (Discussione) (riga 88); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `within that path only PCA and neighbour graph construction had distributed GPU implementations usable for the pipeline as configured here`
- **Valore:** n.d. → 8 V100; 8 B300; 100M cellule
- **Istruzione:** Nei Metodi la frase 'only PCA and neighbour graph construction had distributed GPU implementations' cade con R0407. Nella Discussione, riga 418, dove si propone di distribuire il preprocessing come lavoro futuro (primaria R0583, traccia T5), aggiungere: "Distributed GPU preprocessing with Dask has already been demonstrated, with RAPIDS on 8 V100 GPUs for 1.3 million cells [@Nolet2022] and with rapids-singlecell on 8 B300 GPUs for 100 million cells [@Dicks2026]."
- **Fonte:** righe_da_pianificare.csv id=R0539 campo recomputed (Nolet2022 Table 1; Dicks2026 righe 160-170)
- **Dipende da:** R0407; R0583
- **Nota:** Il '1.3 million cells' di Nolet2022 viene da peer_review.md (tabella di confronto); 8 V100 e 8 B300 dal registro.

#### R0050 · S3 · P5 (bibliografia) · verificare-in-step
- **Bersaglio:** prosa (riga 94); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `The panel follows the metric families adopted in published scRNA-seq method benchmarks [@Tian2019; @Duo2020; @Luecken2022], progressing from deterministic up...`
- **Valore:** [@Tian2019; @Duo2020; @Luecken2022] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 94: aprire Tian2019, Duo2020 e Luecken2022 e controllare quali famiglie di metriche usano (ARI, NMI, sovrapposizione di vicini, concordanza HVG o DE). Luecken2022 non usa una Jaccard sui vicini (R0489). Se il pannello non è sostenuto da tutte e tre, riscrivere "The panel follows the metric families adopted in published scRNA-seq method benchmarks [...]" citando solo le fonti che lo sostengono, per esempio "The clustering metrics follow published benchmarks [@Duo2020; @Luecken2022]".
- **Fonte:** testi di Tian2019, Duo2020, Luecken2022 (non nel pacchetto); righe_da_pianificare.csv id=R0489
- **Assorbe:** R0410

#### R0705 · S3 · PM (arrotondamenti e minori) · riformulare
- **Bersaglio:** prosa (riga 94); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `we selected six concordance metrics, one for each major stage of the analysis pipeline`
- **Valore:** six concordance metrics, one for each major stage of the analysis pipeline → (da rileggere, vedi fonte)
- **Istruzione:** Riga 94: "we selected six concordance metrics, one for each major stage of the analysis pipeline" diventa "we selected six concordance metrics covering five stages of the analysis pipeline (two for clustering)" (Table 2: ARI e NMI hanno entrambe ambito Clustering).
- **Fonte:** full_paper_LNBI.md righe 98-105 (Table 2)

#### R0489 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** prosa (riga 102); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Mean per-cell Jaccard overlap of k-nearest-neighbour sets (k = 15) [@Luecken2022]`
- **Valore:** (k = 15) [@Luecken2022] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 102, Table 2: sostituire [@Luecken2022] con [@Gardner2025] nella definizione della kNN Jaccard (Luecken2022 non contiene questa metrica). Prima di scrivere controllare nel PDF di Gardner2025 che la metrica 'kNN Jaccard' sia definita così; in alternativa citare Nolet2022 (percentuale di vicini conservati). La definizione va anche precisata sull'inclusione della cellula stessa nel suo insieme di vicini (tetto 0,9375 = 15/16, primaria R0652, traccia T6).
- **Fonte:** righe_da_pianificare.csv id=R0489 campo note; PDF Gardner2025
- **Dipende da:** R0652 (assorbita in R0371)

#### R0490 · S3 · P5 (bibliografia) · verificare-in-step
- **Bersaglio:** prosa; bib:Hubert1985 (riga 103); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Adjusted Rand Index of Leiden cluster assignments, adjusted for chance [@Hubert1985]`
- **Istruzione:** Riga 103: attribuzione canonica dell'ARI, nessuna modifica del testo attesa. In S3 confrontare la voce Hubert1985 del .bib con Crossref (doi 10.1007/BF01908075, J Classif 2(1):193-218) e chiudere la voce se coincide.
- **Fonte:** righe_da_pianificare.csv id=R0490 campo source (Crossref 10.1007/BF01908075)

#### R0492 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa; bib:Kuhn1955 (riga 105); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Spearman rho of log-fold-changes for top 100 DE genes per cluster, after Hungarian matching [@Soneson2018]`
- **Valore:** after Hungarian matching [@Soneson2018] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 105, Table 2: sostituire la definizione con "Spearman rho of log-fold-changes of the top 100 DE genes per cluster, after matching CPU and GPU clusters with the Hungarian algorithm [@Kuhn1955]; metric defined for this study". Aggiungere al .bib Kuhn1955 (The Hungarian method for the assignment problem, Naval Research Logistics Quarterly) con metadati da Crossref. Prima di togliere Soneson2018 tentare di leggere il testo principale: se definisce questa metrica, mantenere la citazione accanto a Kuhn1955.
- **Fonte:** righe_da_pianificare.csv id=R0492 campo note; Crossref per Kuhn1955 (non nel pacchetto)

#### R0462 · S3 · P6 (stress test replicato) · aggiungere
- **Bersaglio:** prosa (riga 109); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `To determine the maximum dataset size processable on a single DGX H100 node, we implemented a memory-optimised pipeline variant`
- **Valore:** To determine the maximum dataset size processable on a single DGX H100 node, we implemented a memory-optimised pipeline variant. → 3,436,470; 6.9M = 2 copie, 10.3M = 3, 11.9M = 3 copie piu 1,590,590; 41,344; 42,394; 44,158
- **Istruzione:** Riga 109: dopo la prima frase aggiungere "The stress test used the 3,436,470-cell Census selection described above (and random subsets of it at 1.7M and 3.4M cells). Sizes above this number were built by concatenating whole copies of the dataset with renamed cell identifiers (6.9M cells: 2 copies; 10.3M: 3 copies; 11.9M: 3 copies plus 1,590,590 randomly drawn cells), so duplicated cells are present in the expression matrix and in the k-NN graph. Because duplicated cells reach the `min_cells` = 3 threshold, the number of genes passing QC grew with replication (41,344 at 3.44M, 42,394 at 6.87M and 44,158 from 10.3M cells). DE was skipped during the search (`--skip-de`)." Per le righe di Table 5 a 3,4M, 6,9M e 10,3M dichiarare il clustering usato (cuML KMeans invece di Leiden): configuration.clustering_algorithm = kmeans con k = 50, 100 e 200 (n_clusters_0.5/1.0/1.5) in results/maxpower_{3436470,6872940,10309410}_8gpu_results.json (copia nel pacchetto S2 in scrna_json/results/).
- **Fonte:** righe_da_pianificare.csv id=R0462 campo recomputed (benchmark_maxpower.py righe 468-524; results_summary.n_genes_after_qc); id=R0547 campo recomputed (3,436,470)
- **Dipende da:** R0024
- **Nota:** Primaria P6 per la provenienza dei dati dello stress test. L'interpretazione del limite 11,9M nell'abstract è della traccia T1.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0420 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 110); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The key optimisations were: (i) scaling on CPU rather than GPU (leveraging 2 TB system RAM); (ii) a distributed covariance PCA that scatters the scaled matri...`
- **Valore:** which is mathematically equivalent to standard PCA via the covariance method → DASK_RMM_POOL_SIZE = 2GB
- **Istruzione:** Riga 110: (ii) sostituire "a distributed covariance PCA that scatters the scaled matrix across all 8 GPUs, ..., which is mathematically equivalent to standard PCA via the covariance method" con "a covariance PCA in which the parent process scattered the scaled matrix across the 8 GPUs, computed per-GPU partial products (2,000 x 2,000), summed and eigendecomposed them on GPU 0 and projected locally; the matrix was not re-centred after clipping at `max_value` = 10 and partial products were accumulated in float32, so the result approximates, but is not identical to, standard PCA"; (iv) sostituire "a reduced RMM pool (2 GB per worker)" con "a reduced RMM pool (2 GB) for each Dask-CUDA worker; the workers were started but performed no computation".
- **Fonte:** righe_da_pianificare.csv id=R0420 campo recomputed (benchmark_maxpower.py righe 346-461, 616-667)
- **Nota:** 'mathematically equivalent' ricompare in Limitazioni riga 432 (traccia T5).

#### R0252 · S3 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** trasversale: riga 111, Tables 4-6, righe 250 e 262 (riga 111); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `CPU memory was recorded as the resident set size of the parent Python process (`psutil.Process().memory_info().rss`)`
- **Valore:** n.d. → 535 GiB = 574 GB
- **Istruzione:** Uniformare le unità di memoria: tutte le misure (RSS psutil e NVML) sono divise per 1024**3, quindi GiB. Dichiararlo una volta in riga 111 ("all memory values are in GiB") e usare GiB nelle intestazioni di Tables 4-6; le stime in GB decimali (Table 6, 96 GB; riga 250, 10.4 GB) vanno convertite in GiB o etichettate come GB.
- **Fonte:** righe_da_pianificare.csv id=R0252 campi recomputed e note (get_peak_ram_gb, get_vram_used_gb)

#### R0461 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** prosa (riga 111); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `CPU memory was recorded as the resident set size of the parent Python process (`psutil.Process().memory_info().rss`), sampled immediately before and after ea...`
- **Valore:** preceded by an explicit garbage collection → 302.34
- **Istruzione:** Riga 111: "sampled immediately before and after each pipeline step and preceded by an explicit garbage collection" diventa "sampled immediately before and after each pipeline step, with an explicit garbage collection before each pre-step sample". Aggiungere dopo la frase sul limite inferiore: "The replication of the dataset for sizes above 3,436,470 cells ran between data loading and QC, outside any timed step: at 11.9M cells it accounts for the 302.34 GiB increase between these two samples, and its transient peak was not sampled. GPU memory was recorded with NVML as device memory in use, summed over the eight GPUs; it includes the RMM pools of the Dask-CUDA workers." La correzione di 'belongs to no timed step' (Risultati riga 262 e Table 6) è nella traccia T3.
- **Fonte:** righe_da_pianificare.csv id=R0461 campo recomputed (426.10 - 123.76 = 302.34; maxpower_11900000_8gpu_results.json)
- **Dipende da:** R0462; R0252
- **Nota:** Il registro scrive GB ma le misure sono rss/1024**3, quindi GiB (R0252).

#### R0706 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 111); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `We conducted a binary search from 3.4M to 13.7M cells to identify the failure point`
- **Valore:** We conducted a binary search from 3.4M to 13.7M cells to identify the failure point. → Non in Table 5: 1.7M, 3.4M (3,400,000 cells, Leiden; la riga 3.4M di Table 5 e' il run KMeans a 3,436,470), 8.5M, 9.4M, 9.8M, 10.0M, 10.1M, 10.2M, 11.1M, 11.7M, 11.8M; in totale 16 taglie non chunked con JSON (results/maxpower_*_8gpu_results.json) piu' il run chunked a 12.0M; 12.0M non chunked e 13.7M senza JSON di risultato
- **Istruzione:** Riga 111: "We conducted a binary search from 3.4M to 13.7M cells to identify the failure point." non descrive i run: in results/ ci sono anche 1.7M, 8.5M, 9.4M, 9.8M, 10.0M, 10.1M, 10.2M, 11.1M, 11.7M e 11.8M, mentre Table 5 ne riporta 7. In S3 elencare sul server (sola lettura) i maxpower_*_8gpu_results.json, poi scrivere "We ran the memory-optimised pipeline at N sizes between 1.7M and 13.7M cells, refining the step size near the failure point; Table 5 lists [criterion]." con N e criterio letti dai file (per esempio 'the sizes at which a component first failed'). Se il PI preferisce, Table 5 riporta tutti i punti.
- **Fonte:** righe_da_pianificare.csv id=R0706 campo recomputed; server: ls results/maxpower_*
- **Nota:** 13.7M è 'a separate test' alla riga 260: chiarirlo insieme.
- **Modificata in arbitrato:** value_new (vedi `arbitrati.csv`)

#### R0422 · S3 · P7 (espressione differenziale) · correggere
- **Bersaglio:** prosa (riga 115); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `At 3.4 million cells and 41,000 genes the raw count matrix (`adata.raw.X`) occupies approximately 121 GB in sparse CSR format, exceeding the 80 GB VRAM of an...`
- **Valore:** the raw count matrix (`adata.raw.X`) occupies approximately 121 GB in sparse CSR format, exceeding the 80 GB VRAM of any single H100 device; running GPU DE naively is therefore impossible → 3,399,892; 41,321
- **Istruzione:** Riga 115, seconda frase: sostituire "At 3.4 million cells and 41,000 genes the raw count matrix (`adata.raw.X`) occupies approximately 121 GB in sparse CSR format, exceeding the 80 GB VRAM of any single H100 device; running GPU DE naively is therefore impossible, and the tests we benchmark either scatter genes across multiple GPUs or stream gene chunks through a single GPU." con "At this size (3,399,892 cells and 41,321 genes) the matrix used for DE, `adata.raw.X`, which in this pipeline holds log-normalised values rather than raw counts, was too large to process on one H100 as a whole, so the GPU tests either scatter gene chunks across GPUs or stream them through a single GPU." Il 121 GB non è in nessun JSON: o lo si toglie, o in S3 si legge in sola lettura la dimensione di raw/X/data dal h5ad sul server e la si scrive con la fonte. 'impossible' va tolto: maxpower_3400000_8gpu_results.json registra de_testing = 209.9 s a 3,4M dentro la pipeline.
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0422 campo recomputed (de_benchmark_*.json; test_de_benchmark.py righe 130-140); server: h5ad brain_full_3436470 per nnz
- **Assorbe:** R0062
- **Nota:** La frase 'too large to process on one H100 as a whole' resta da confermare con nnz; se non confermabile scrivere solo la strategia.

#### R0423 · S3 · P7 (espressione differenziale) · correggere
- **Bersaglio:** prosa (riga 115); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `We evaluated seven DE strategies in a factorial design crossing test type (Wilcoxon, t-test, pseudo-bulk) with GPU strategy (none, scatter-by-genes across 8 ...`
- **Valore:** We evaluated seven DE strategies in a factorial design crossing test type (Wilcoxon, t-test, pseudo-bulk) with GPU strategy (none, scatter-by-genes across 8 GPUs, chunk-and-stream on 1 GPU). → pseudobulk, ttest_cpu, ttest_scatter, ttest_scatter_clean, ttest_chunk, wilcoxon_scatter, wilcoxon_chunk
- **Istruzione:** Riga 115: sostituire "We evaluated seven DE strategies in a factorial design crossing test type (Wilcoxon, t-test, pseudo-bulk) with GPU strategy (none, scatter-by-genes across 8 GPUs, chunk-and-stream on 1 GPU)." con "We timed six DE configurations (Table 7): a t-test on CPU (Scanpy); a t-test and a Wilcoxon test with gene chunks scattered across 8 GPUs; the same two tests with gene chunks streamed through one GPU; and pseudo-bulk aggregation followed by a Wilcoxon test on CPU. A Wilcoxon test on CPU was not run at this size and pseudo-bulk was not run on GPU, so the design is not a full factorial. In the scatter strategy a single host thread processed the chunks in sequence, alternating devices, so the GPUs did not work concurrently." In Table 7 togliere la voce duplicata ttest_scatter_clean se compare (traccia T3).
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0423 campo recomputed (test_de_benchmark.py righe 387-616 e 815-824; de_benchmark_*.json)
- **Assorbe:** R0063, R0685

#### R0425 · S3 · P7 (espressione differenziale) · correggere
- **Bersaglio:** prosa (riga 115); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Pseudo-bulk aggregation summed raw counts by donor x cluster, normalised to counts per million, log-transformed, and applied the Wilcoxon test on the aggrega...`
- **Valore:** Pseudo-bulk aggregation summed raw counts by donor x cluster, normalised to counts per million, log-transformed, and applied the Wilcoxon test on the aggregated matrix [@Squair2021]. → n_donors 202; n_pseudobulk_samples 2431; 81 cluster
- **Istruzione:** Riga 115: sostituire "Pseudo-bulk aggregation summed raw counts by donor x cluster, normalised to counts per million, log-transformed, and applied the Wilcoxon test on the aggregated matrix [@Squair2021]." con "Pseudo-bulk aggregation summed the values of `adata.raw.X` (log-normalised, not raw counts, in this pipeline) over donor x cluster groups (Census `donor_id`, 202 donors; groups with fewer than 5 cells discarded; 2,431 pseudo-samples over 81 clusters), re-normalised the sums to counts per million, applied a second log transformation and compared clusters with a Wilcoxon test." La frase sulla citazione è in R0493.
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0425 campi recomputed e source (test_de_benchmark.py righe 619-739; de_benchmark_pseudobulk.json)
- **Nota:** Risultati riga 321 ('a few hundred pseudo-samples per cluster') contro 30 per cluster: traccia T3. Conclusione riga 439 ('most statistically rigorous'): D-04, traccia T5.

#### R0463 · S3 · P7 (espressione differenziale) · aggiungere
- **Bersaglio:** prosa (riga 115); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `We evaluated seven DE strategies in a factorial design crossing test type (Wilcoxon, t-test, pseudo-bulk) with GPU strategy (none, scatter-by-genes across 8 ...`
- **Istruzione:** Riga 115, dopo la frase sui chunk da 500 geni: aggiungere "The GPU tests were custom CuPy kernels, not `rank_genes_groups`: the Wilcoxon kernel assigned ordinal ranks without averaging ties and computed neither p-values nor a multiple-testing correction, so it yields a rank-sum statistic used here for timing only. GPU timings start after `adata.raw.X` was converted to CSC format, a conversion that is included in the CPU timings."
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0463 campo recomputed (test_de_benchmark.py righe 169-313, 403-421, 468-482)
- **Dipende da:** R0423
- **Nota:** Necessaria per presentare il DE come confronto di tempi (D-04).

#### R0493 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 115); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Pseudo-bulk aggregation summed raw counts by donor x cluster, normalised to counts per million, log-transformed, and applied the Wilcoxon test on the aggrega...`
- **Valore:** applied the Wilcoxon test on the aggregated matrix [@Squair2021] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 115, dopo il testo di R0425 (che non cita piu' Squair2021): aggiungere in coda alla frase la frase "We use this aggregation as a timing proxy for pseudo-bulk analysis; count-based methods such as edgeR or DESeq2 are recommended for pseudo-bulk DE between conditions [@Squair2021]." (Squair2021 valuta confronti fra condizioni, non fra cluster, con metodi su conteggi). Prima di scrivere, rileggere in Squair2021 il passaggio sui metodi pseudo-bulk (regola 8).
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0493 campo recomputed (Squair2021, web_evidence_part2.txt)
- **Dipende da:** R0425
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0687 · S3 · P2 (dataset Census) · aggiungere
- **Bersaglio:** prosa (riga 115); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Pseudo-bulk aggregation summed raw counts by donor x cluster, normalised to counts per million, log-transformed, and applied the Wilcoxon test on the aggrega...`
- **Valore:** n.d. → 3,399,892; 41,321
- **Istruzione:** Righe 113-115 (Differential expression at scale): all'inizio della sottosezione dire su quali dati gira il DE: "DE was benchmarked on a 3,400,000-cell subset of the Census selection (3,399,892 cells and 41,321 genes in `adata.raw` after QC)." I sette JSON results/de_benchmark_*.json danno n_cells 3,399,892 e n_genes_raw 41,321, uguali a results/maxpower_3400000_8gpu_results.json dopo QC, mentre la selezione completa (maxpower_3436470) da' 3,436,361 cellule e 41,344 geni. Prima di scrivere, S3 conferma in sola lettura in test_de_benchmark.py il file di ingresso e come e' stato estratto il sottocampione; scrivere 'random' solo se il codice lo conferma. Se il file fosse la selezione completa, la discordanza 3,399,892 contro 3,436,361 va spiegata prima di scrivere. La definizione di 'donor' (Census donor_id, 202 donatori) e' in R0425, la costruzione delle taglie oltre 3,4M in R0462.
- **Fonte:** righe_da_pianificare.csv id=R0422 campo recomputed; id=R0062 campo recomputed (n_cells 3,399,892, n_genes_raw 41,321)
- **Dipende da:** R0024; R0425; R0462
- **Nota:** Il 39,182 contro 41,000 geni (righe 250 e 308) si spiega con la sorgente diversa (1,3M contro 3,4M): da dire nei Risultati (traccia T3).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0259 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 122); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The second is Visium HD Mouse Brain (CytAssist, FFPE), benchmarked at two bin sizes: 8 um (393,543 bins) and 2 um (subsampled from the native 6.3 million dow...`
- **Valore:** Visium HD Mouse Brain (CytAssist, FFPE) → Visium_HD_Tiny_3prime_Dataset; Space Ranger 4.0.1
- **Istruzione:** Riga 122: sostituire "Visium HD Mouse Brain (CytAssist, FFPE)" con "the Visium HD 3' mouse brain example dataset distributed by 10x Genomics as `Visium_HD_Tiny_3prime_Dataset` (Space Ranger 4.0.1), which has subsampled reads and is not intended for biological conclusions". Applicare solo dopo la verifica di R0426 sull'identità dei file analizzati. I numeri di bin sono in R0428.
- **Fonte:** s1_evaluation.json provenance.VISIUM_HD_URL e VISIUM_HD_ARCHIVE; S3.md 'Dataset Visium HD (da S1)'; righe_da_pianificare.csv id=R0259 campo recomputed (pagina 10x)
- **Dipende da:** R0426
- **Nota:** 'FFPE' non corrisponde alla chimica 3' del dataset scaricato.

#### R0426 · S3 · P11 (ambiente e hardware) · verificare-in-step
- **Bersaglio:** prosa (riga 122); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Spatial benchmarks used two 10x Genomics public datasets, both downloaded programmatically from the 10x Genomics public data portal`
- **Valore:** both downloaded programmatically from the 10x Genomics public data portal → (da rileggere, vedi fonte)
- **Istruzione:** Prima di scrivere il nome del dataset (R0259) chiarire una incoerenza: 10x descrive il Tiny 3' come ridotto a un angolo del tessuto (297 MB), mentre i JSON riportano 393,543 bin a 8 um e 6,296,688 a 2 um. In S3, in sola lettura sul server: leggere in SPATIAL/results_v2 (metadata) il percorso dei file caricati, confrontarne dimensione e md5 con l'archivio Visium_HD_Tiny_3prime_Dataset_outs.zip e leggere metrics_summary.csv degli outs. Se i file sono il Tiny, applicare R0259; se no, identificare dataset e URL e scriverli al posto del Tiny.
- **Fonte:** server: SPATIAL/results_v2/*/spatial_*_visium_hd_*_r1_results.json metadata, SPATIAL/data, SPATIAL/scripts/download_spatial_data.py righe 26-52 e 202-232
- **Nota:** S1 e S3.md danno per certo il Tiny leggendo lo script di download; il conteggio dei bin non è stato riconciliato.

#### R0553 · S3 · P5 (bibliografia) · aggiungere
- **Bersaglio:** tabella:Table 3 righe 9 e 14; bib (riga 133); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Delaunay triangulation (scipy.spatial)`
- **Valore:** Delaunay triangulation (scipy.spatial) → (da rileggere, vedi fonte)
- **Istruzione:** Table 3: riga 9 ("Delaunay triangulation (scipy.spatial)") aggiungere la citazione di SciPy [@Virtanen2020]; riga 14 ("Cell communication inference") scrivere "Squidpy re-implementation of CellPhoneDB [@Palla2022; @Efremova2020]". Aggiungere al .bib Virtanen2020 e Efremova2020 con metadati da Crossref. La citazione del metodo ungherese è in R0492. Pesare le aggiunte con il limite di pagine (D-03).
- **Decisione o convenzione:** D-03
- **Fonte:** righe_da_pianificare.csv id=R0553 campo recomputed (Palla2022: re-implementation of CellphoneDB); Crossref (non nel pacchetto)
- **Dipende da:** R0492
- **Modificata in arbitrato:** anchor, line, quality (vedi `arbitrati.csv`)

#### R0657 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 144); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Co-occurrence and neighbourhood enrichment were skipped when cluster counts exceeded 500`
- **Valore:** Co-occurrence and neighbourhood enrichment were skipped when cluster counts exceeded 500, as their O(k^2) memory complexity becomes prohibitive. → (da rileggere, vedi fonte)
- **Istruzione:** Metodi righe 144-145 e Table 3 riga 132: nessuna voce di frase copre queste soglie. Sostituire le due frasi con "Co-occurrence and neighbourhood enrichment were skipped when the number of clusters exceeded 500, because their memory grows with the square of the number of clusters, and ligand-receptor analysis was skipped above 100,000 spots. These limits and the Leiden resolution of 0.1 for Visium HD were practical choices to keep memory and run time tractable; we did not test their sensitivity." Avviso per S5: con i gruppi di S1 il Leiden CPU del DGX a HD 2 um da' 3027 gruppi, quindi la soglia di 500 esclude li' co-occorrenza e arricchimento; lo speedup HD 2 um va detto senza questi step. La soglia rho > 0.97 di riga 242 e' la voce R0709; gli ARI vanno riportati senza aggettivi o con il criterio dichiarato.
- **Fonte:** full_paper_LNBI.md righe 132, 144-145; s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um.dgx_cpu
- **Dipende da:** R0709
- **Modificata in arbitrato:** anchor, line, quality (vedi `arbitrati.csv`)

#### R0445 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 154); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Single-cell benchmarks ran on a single node of the UPSCALE/CONVECS DGX H100 cluster at the University of Padova, comprising 8 x NVIDIA H100 80 GB SXM GPUs co...`
- **Valore:** ran on a single node of the UPSCALE/CONVECS DGX H100 cluster → 535.247.01; 535.183.01; 224
- **Istruzione:** Riga 154: sostituire "Single-cell benchmarks ran on a single node of the UPSCALE/CONVECS DGX H100 cluster at the University of Padova, comprising ..." con "Single-cell benchmarks ran on DGX H100 nodes of the UPSCALE/CONVECS cluster at the University of Padova; each node has 8 x NVIDIA H100 80 GB SXM GPUs connected via NVLink 4.0, two Intel Xeon Platinum 8480C CPUs (112 cores, 224 hardware threads) and 2 TB of DDR5 RAM [@NVIDIADGXH100]." I nodi effettivamente usati sono in R0448; la citazione della scheda tecnica è in R0549.
- **Fonte:** righe_da_pianificare.csv id=R0445 campo recomputed (driver_timeline.py, meta_dump.py; n_cpus 224)
- **Dipende da:** R0448; R0549
- **Nota:** Modello CPU, NVLink e RAM non registrati nei JSON: si reggono sulla scheda tecnica (R0549).

#### R0549 · S3 · P5 (bibliografia) · aggiungere
- **Bersaglio:** prosa; bib:NVIDIADGXH100 (riga 154); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `comprising 8 x NVIDIA H100 80 GB SXM GPUs connected via NVLink 4.0, dual Intel Xeon Platinum 8480C CPUs (112 cores total), and 2 TB DDR5 RAM`
- **Istruzione:** Riga 154: le specifiche del DGX H100 sono corrette ma senza fonte. Aggiungere al .bib la NVIDIA DGX H100 User Guide o la scheda tecnica NVIDIA (chiave NVIDIADGXH100, URL e data di accesso da leggere in S3) e citarla nella frase di R0445. La pagina PNY del registro è solo un ripiego.
- **Fonte:** righe_da_pianificare.csv id=R0549 campo source (pny.com); documentazione NVIDIA (non nel pacchetto)
- **Dipende da:** R0445

#### R0554 · S3 · P5 (bibliografia) · aggiungere
- **Bersaglio:** prosa riga 156; bib (riga 156); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Key software versions: Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, Dask 2026.1.1, Dask-CUDA 26.2.0, Python 3.12.12`
- **Valore:** Key software versions: Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, Dask 2026.1.1, Dask-CUDA 26.2.0, Python 3.12.12. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 156: aggiungere le citazioni dei componenti centrali senza riferimento: CuPy (Okuta et al. 2017), cuML (Raschka et al. 2020), igraph, NumPy (Harris et al. 2020), SciPy (Virtanen et al. 2020, già richiesta da R0553). Metadati da Crossref in S3; le fonti sono elencate nei riferimenti 2, 11, 12 e 14 di Dicks2026. Tenere conto del limite di pagine (D-03): SLURM, Singularity e psutil possono restare senza citazione.
- **Decisione o convenzione:** D-03
- **Fonte:** righe_da_pianificare.csv id=R0554 campi recomputed e source (tracks/E_work/pdf_txt/2603.02402v1.txt); Crossref (non nel pacchetto)
- **Dipende da:** R0553

#### R0448 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 157); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Jobs were submitted via SLURM on a dedicated DGX H100 node (`poddgx02`)`
- **Valore:** Jobs were submitted via SLURM on a dedicated DGX H100 node (`poddgx02`). → 535.247.01 (1/2/4 GPU); 535.183.01 (8 GPU e stress test con --nodelist=poddgx02); 16/32/56/200 per 1/2/4/8 GPU, 100 per la CPU
- **Istruzione:** Riga 157: sostituire "Jobs were submitted via SLURM on a dedicated DGX H100 node (`poddgx02`)." con "Jobs were submitted via SLURM without exclusive allocation. The single-GPU, 2-GPU and 4-GPU runs ran concurrently on one node (NVIDIA driver 535.247.01) with 16, 32 and 56 allocated CPUs; the 8-GPU runs (200 CPUs) ran on a node with driver 535.183.01, the driver of node `poddgx02`, to which the stress test and the DE benchmark were pinned; the CPU baseline used 100 CPUs on a node that was not recorded." Facoltativo in S3: cercare nei log SLURM non tracciati sul server (sola lettura) l'hostname dei job gpu_8 e cpu_benchmark per sostituire 'a node with driver 535.183.01' con il nome del nodo. In coda al testo proposto aggiungere: "The 8-GPU job that gives the 1.3M-cell speedup therefore had twice as many CPUs for host-side steps as the CPU baseline." (200 contro 100; le CPU allocate per job vengono dal registro R0642 e R0448, script SLURM).
- **Fonte:** righe_da_pianificare.csv id=R0642 campo recomputed; id=R0448 campo recomputed (--nodelist=poddgx02 in maxpower*, de_benchmark); id=R0242 campo recomputed (RAM richiesta)
- **Assorbe:** R0069, R0242, R0642, R0645
- **Nota:** Il report (P3) dà il run a 8 GPU su poddgx02: nessun artefatto lo lega al nodo, solo il driver uguale. Le differenze di nodo spiegano il 12% (D-02, R0407).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0276 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 159); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Spatial benchmarks ran on a local workstation equipped with an NVIDIA RTX 4090 (24 GB GDDR6X), 100 CPU cores, and 256 GB DDR5 RAM, driven by a more recent NV...`
- **Valore:** a local workstation equipped with an NVIDIA RTX 4090 (24 GB GDDR6X), 100 CPU cores, and 256 GB DDR5 RAM, driven by a more recent NVIDIA driver (550.x) → AMD Ryzen Threadripper PRO 5995WX, 64 core e 128 thread; driver 580.126.09 a marzo; 595.99.02 nel rerun; P3 visium 0.941, visium_hd_square_008um 1.038, visium_hd_square_002um 1.041
- **Istruzione:** Riga 159: sostituire la frase con "GPU spatial benchmarks ran on a workstation with an NVIDIA GeForce RTX 4090 (24 GB) and an AMD Ryzen Threadripper PRO 5995WX CPU (64 cores, 128 threads). The CPU reference ran on DGX node `poddgx02`, reserved exclusively, as a SLURM step with 100 CPUs (50 physical cores with two hardware threads each), the same allocation as the scRNA-seq CPU baseline; the workstation CPU at 128 threads was measured as a control. CPU reference and GPU therefore ran on different machines. The NVIDIA driver of the workstation was 580.126.09 for preliminary runs in March 2026 and 595.99.02 for the runs reported here; GPU times of the steps that do not depend on the cell groups changed by a factor of 0.94 to 1.04 between the two." Il rapporto del driver (previsione P3 di S1) è visium 0.941, visium_hd_square_008um 1.038, visium_hd_square_002um 1.041: arrotondare a 0.94-1.04. La RAM ("256 GB DDR5") non è registrata in nessun file: o la si legge sul server in sola lettura (free -g) o si toglie; 'DDR5' va comunque verificato, perché la piattaforma Threadripper PRO 5000WX usa DDR4 (da confermare, non da file del pacchetto).
- **Decisione o convenzione:** D-11;D-10
- **Fonte:** S3.md 'Workstation e driver (da S1)'; s1_evaluation.json predictions.P3.<piattaforma>.ratio; decisioni_D01_D13.txt D-11 e D-12 punto 3
- **Dipende da:** D-10; D-11; D-12
- **Assorbe:** R0070, R0449, R0643
- **Nota:** Primaria P11 per il paragrafo spatial (righe 159-160). Se il PI preferisce, la frase sul driver si accorcia; D-10 chiede una frase breve perché la previsione è confermata.

#### R0536 · S3 · P5 (bibliografia) · correggere
- **Bersaglio:** bib:Marconato2024 (riga 160); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Marconato2024`
- **Valore:** n.d. → Marconato, Palla, Yamauchi KA, Virshup, Heidari, Treis, Vierdag, Toth, Stockhaus, Shrestha, Rombaut, Pollaris, Lehner, Voehringer, Kats, Saeys, Saka, Huber, Gerstung, Moore, Theis, Stegle; 22(1) 58-62
- **Istruzione:** Voce Marconato2024 del .bib: sostituire l'elenco autori (contiene Yaber, Chierici, Puente-Lelievre, Nabavi, Rattray, che non sono autori) con i 22 autori di Crossref nell'ordine dato, con nomi completi letti da Crossref (doi 10.1038/s41592-024-02212-x); numero 1, pagine 58-62; anno 2025, coerente con il volume 22 (online 2024-03-20). Lasciare la chiave Marconato2024 per non toccare il testo.
- **Fonte:** righe_da_pianificare.csv id=R0536 campo recomputed (api.crossref.org/works/10.1038/s41592-024-02212-x)
- **Nota:** Stesso difetto nello short paper (D-06: non si tocca).
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)

#### R0451 · S3 · P11 (ambiente e hardware) · verificare-in-step
- **Bersaglio:** prosa (riga 161); registro: UNVERIFIABLE, major
- **Ancora (univoca nel .md):** `DGX-scale spatial benchmarks were not feasible within the study timeline: although the scRNA pipeline executed successfully on the DGX node via CUDA forward-...`
- **Valore:** DGX-scale spatial benchmarks were not feasible within the study timeline → (da rileggere, vedi fonte)
- **Istruzione:** Riga 161: la frase "DGX-scale spatial benchmarks were not feasible within the study timeline" non vale più, perché il riferimento CPU spatial ora gira sul DGX (D-11). La spiegazione del fallimento GPU ("caps CUDA runtime at 12.2") non ha log e contrasta con la compatibilità documentata da NVIDIA. In S3 cercare sul server, in sola lettura, log del tentativo spatial GPU sul DGX e leggere SPATIAL/SPATIAL.md righe 255-270. Se il log c'è, riportare il messaggio d'errore reale; se no, scrivere "The GPU part of the spatial pipeline was run only on the workstation." senza spiegazione del driver. Il testo finale dipende dalla scelta del PI in R0279.
- **Decisione o convenzione:** D-11
- **Fonte:** server: SPATIAL/SPATIAL.md righe 255-270 e log SLURM spatial (non nel pacchetto); righe_da_pianificare.csv id=R0546 campo recomputed (note di rilascio CUDA)
- **Dipende da:** D-11; R0279
- **Assorbe:** R0072, R0278, R0546
- **Nota:** Stessa affermazione nelle Limitazioni riga 432 (R0226, R0339, R0623, traccia T5).

#### R0466 · S3 · P9 (convenzione sulle ripetizioni) · riformulare
- **Bersaglio:** prosa (riga 165); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Each benchmark configuration was repeated five times; we report mean +/- standard deviation`
- **Valore:** Each benchmark configuration was repeated five times; we report mean +/- standard deviation. → ddof=1; 19.90 s contro circa 1.12 s; picchi = media dei picchi per ripetizione
- **Istruzione:** Righe 165-166 (convenzione A, in attesa del PI): sostituire la riga 165 con "Each benchmark configuration was run five times; we report the mean +/- sample standard deviation (n = 5, ddof = 1) of all five repeats. The five scRNA-seq repeats ran in the same process, so the first includes JIT compilation and library loading (for example, CPU neighbour search at 10k cells took 19.90 s in the first repeat and 1.12 s on average in the others). Peak RAM and VRAM are means of per-repeat peaks. The stress test, the DE benchmark and the concordance analysis were run once." La riga 166 (spatial) si riscrive con R0453. Se il PI sceglie un'altra convenzione questa voce si rigenera.
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0466 campo recomputed (generate_figures.py righe 144-146); id=R0246 campo source; S2_P1_threads.csv n=10000 step=neighbors (r1 19.9029, mean25 1.121575)
- **Dipende da:** CONV; R0453
- **Assorbe:** R0246, R0647, R0662, R0703
- **Nota:** S2_P1_threads.csv: lo scRNA CPU non mostra il difetto dei thread (r2-5/r1 al massimo 1,05 negli step da almeno 1 s), quindi il processo unico non va dichiarato come difetto.

#### R0453 · S3 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 166); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `For spatial benchmarks, the first repeat served as a JIT/warmup run and was excluded; we report the mean of repeats 2-5`
- **Valore:** the first repeat served as a JIT/warmup run and was excluded; we report the mean of repeats 2-5 → numba threads 100 prima di nhood_enrichment, [1, 1] dopo
- **Istruzione:** Riga 166: sostituire "For spatial benchmarks, the first repeat served as a JIT/warmup run and was excluded; we report the mean of repeats 2-5." con "For the spatial benchmarks each repeat ran in a new process with empty Numba and CuPy JIT caches, so every repeat includes JIT compilation and, for ligand-receptor analysis, the download of the OmniPath database. Co-occurrence, neighbourhood enrichment and ligand-receptor analysis used the same cell groups in all runs, the Leiden labels of the first CPU reference repeat. Squidpy 1.8.1 sets the Numba thread count to one during neighbourhood enrichment and keeps it for the rest of the process, so ligand-receptor analysis, which follows it, ran with one Numba thread in both pipelines." Facoltativo, a scelta del PI: aggiungere "In earlier runs in which the five repeats shared one process, this setting slowed the CPU co-occurrence after the first repeat by a factor of about 49; the results reported here do not have this defect." I valori 6.4x e 29.3x ricalcolati dalla revisione non si usano: i numeri spatial vengono da S1 (R0280).
- **Decisione o convenzione:** D-12;CONV
- **Fonte:** s1_evaluation.json predictions.P2 (n_cpus, threads_after_nhood); S1.md 'Esito delle attese' P2 e G4; decisioni_D01_D13.txt D-12 punti 1 e 2; revisione_n2_report.md P4 (3.573/73,5 = 48,6)
- **Dipende da:** D-01; D-12; CONV; R0466
- **Nota:** Le cifre proposte dalla revisione (6,4x, 29,3x) sono superate da S1, ma la frase dei Metodi si riformula comunque: per questo l'esito è riformulare e non superata-da-S1.

#### R0454 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 170); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `All code, Dockerfiles, SLURM submission scripts, and result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX>`
- **Valore:** All code, Dockerfiles, SLURM submission scripts, and result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX>. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 170: sostituire con "All code, Dockerfiles, SLURM submission scripts and result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX> (release [tag], commit [hash], archived at [DOI]). Per-cell outputs (cluster labels, HVG lists, DE tables, k-NN indices, PCA loadings, Moran's I and Geary's C values) and SLURM logs are not in the repository because of their size; the stress-test results at 1.7M and 3.4M cells and the chunked 12M-cell run were produced by intermediate versions of the scripts that were not committed." Tag, commit e DOI (per esempio Zenodo) li decide e crea il PI; dove depositare gli output per cella è una sua scelta. Anche il target make download-data (--max-cells 100000, Makefile riga 35) non ricrea i dati del capitolo: o si corregge il Makefile in un passo successivo o si scrive nel README il comando usato (slurm/download.sh, --max-cells 1300000).
- **Decisione o convenzione:** PI-S3
- **Fonte:** righe_da_pianificare.csv id=R0454 campi recomputed e note (.gitignore righe 127-135; git log scripts/benchmark_maxpower_chunked.py); id=R0024 campo source (slurm/download.sh)
- **Nota:** FAIR: senza identificatore persistente e senza hash git nei JSON il legame fra risultati e codice non è ricostruibile.

#### R0455 · S3 · P11 (ambiente e hardware) · correggere
- **Bersaglio:** prosa (riga 171); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `All benchmarks ran in Python 3.12 inside a Singularity container built from the Docker image `lucavd/sc-benchmark:latest` (base image `nvcr.io/nvidia/rapidsa...`
- **Valore:** which pins the full package environment → sha256:738c8cc7301590c95a3ddc3b7dd74bafeefee1f1ce188063e14a166a707a6ddd; sha256:4fbe1a15d8e225715828d776921c3032e88f41080dcc1145301683d0440fed2d
- **Istruzione:** Riga 171: sostituire con "The scRNA-seq benchmarks ran in a Singularity container built from the Docker image `lucavd/sc-benchmark:latest` (digest [scRNA digest]); the spatial benchmarks ran in Docker (workstation) and Apptainer (DGX CPU reference) containers from `lucavd/sc-benchmark-spatial:latest` (image id sha256:738c8cc7301590c95a3ddc3b7dd74bafeefee1f1ce188063e14a166a707a6ddd). Both images derive from `nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`; their Dockerfiles do not pin package versions, so the versions used are those recorded at runtime in each result file (Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, RMM 26.2.0, NumPy 2.2.6, igraph 1.0.0)." Il digest dell'immagine scRNA non è nel pacchetto: leggerlo in S3 in sola lettura (docker image inspect sul server o metadati del SIF sul DGX). L'immagine derivata con rapids-singlecell 0.15.1 della verifica D-13 va citata dove si descrive la verifica (R0343).
- **Fonte:** decisioni_D01_D13.txt D-12 punto 3 (immagine spatial); S1.md verifica V1 (immagine 0.15.1); righe_da_pianificare.csv id=R0455 campo recomputed (Dockerfile righe 19-38; constraints.txt)
- **Dipende da:** R0343
- **Assorbe:** R0076, R0707
- **Nota:** constraints.txt (RAPIDS 24.06) non è usato dal Dockerfile e contraddice le versioni registrate: non citarlo.

#### R0496 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 173); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `We note that GPU floating-point arithmetic is non-deterministic due to non-associative parallel reductions [@Shanmugavelu2024; @Collange2015]`
- **Valore:** We note that GPU floating-point arithmetic is non-deterministic due to non-associative parallel reductions [@Shanmugavelu2024; @Collange2015] → a 10k le etichette GPU sono identiche nelle 5 ripetizioni; non determinismo osservato solo da 50k
- **Istruzione:** Riga 173: sostituire con "GPU reductions that use atomic operations can make results vary between runs because floating-point addition is not associative [@Collange2015; @Shanmugavelu2024]. In our runs GPU Leiden labels were identical across the five repeats at 10,000 cells but differed between repeats from 50,000 cells upward. CPU-GPU differences also arise from different algorithms and settings (Leiden implementation and iterations, PCA solver, neighbour search), which the concordance metrics capture together with numerical effects."
- **Fonte:** righe_da_pianificare.csv id=R0078 campo note; id=R0496 campo recomputed (abstract Collange2015, Shanmugavelu2024); revisione_n2_report.md PoW determinismo
- **Dipende da:** R0400; R0398
- **Assorbe:** R0078

#### R0558 · S3 · P8 (peso del Wilcoxon nel 120x) · aggiungere
- **Bersaglio:** prosa (riga 183); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `At 1.3 million cells, the 8-GPU pipeline completed the full analysis in 435.2 +/- 16.2 s (7.3 min), compared with 52,056.2 +/- 392.0 s (14.5 h) for the CPU p...`
- **Valore:** n.d. → 93.5%
- **Istruzione:** Dopo la frase a riga 183 ("... a 119.6-fold speedup.") aggiungere: "Wilcoxon differential expression accounted for 93.5% of the CPU time at 1.3M cells (48,688.3 s of 52,056.2 s); excluding it, the speedup was 9.2x with 8 GPUs and 7.9x with 2 GPUs. Dicks et al. report, on the 10x Genomics mouse brain dataset and excluding differential expression and I/O, more than 120-fold on one B200 and 110-fold on one H200 against a 32-core workstation CPU [@Dicks2026]; in our hybrid pipeline a similar end-to-end factor arises mainly from the CPU Wilcoxon test." Non scrivere "same dataset": il dataset scRNA e' un sottocampione CELLxGENE Census (P2, traccia T2). Passaggio letto in S2 (arXiv 2603.02402v1, Results 'Performance and reproducibility' e Methods): il testo dice '1 million cells from the 10x Genomics mouse brain dataset', la didascalia della Figura 2 '1.3 million cell dataset', quindi nessun numero di cellule si attribuisce a Dicks2026 senza averlo chiarito; B200 26 s, '>120' speedup; H200 110x; CPU AMD Threadripper Pro 7975WX, 32 core; timing senza I/O; workflow senza DE. In S3 rileggere il passaggio nella fonte e verificarne i metadati su Crossref o arXiv prima di scrivere (regola 8).
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0558 campo recomputed (e_numbers.py); revisione_n2_report.md P8 (9,2x con 8 GPU, 7,9x con 2); peer_review.md PoW-C e tabella sezione 1 riga Dicks
- **Dipende da:** CONV
- **Assorbe:** R0648, R0661
- **Nota:** Valori con convenzione r1-5. Coordinare con R0566 (abstract, T1) e R0648/R0661 (T6).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0082 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 185); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The speedup increased monotonically with dataset size: 33.6x at 50k, 43.7x at 100k, 34.9x at 500k (2 GPU), and 119.6x at 1.3M (8 GPU), reflecting the GPU's s...`
- **Valore:** 33.6x at 50k, 43.7x at 100k → 33.7x; 43.8x
- **Istruzione:** Sostituire la frase a riga 185 ("The speedup increased monotonically with dataset size: 33.6x at 50k, 43.7x at 100k, 34.9x at 500k (2 GPU), and 119.6x at 1.3M (8 GPU), reflecting ...") con: "With a single GPU the speedup grew from 12.0x at 10k to 33.7x at 50k and 43.8x at 100k. At 500k and 1.3M cells only the hybrid pipeline could run (Section \"Multi-GPU pipeline\"), and the speedup was 34.9x at 500k (2 GPUs) and 119.6x at 1.3M (8 GPUs, 105.5x with 2 GPUs); because the series mixes two pipelines, it is not a monotonic function of dataset size." Togliere "reflecting the GPU's superior arithmetic throughput on larger matrices".
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0082 campo recomputed (a02_perstep.py, medie r1-r5); S2_P3_convenzione.csv n=50000/100000 gpu spd_r1_5; n=1300000 gpu2 spd_r1_5 (105.5)
- **Dipende da:** CONV; R0352
- **Assorbe:** R0640, R0678
- **Nota:** 33.6 e 43.7 erano rapporti di medie gia' arrotondate. R0640 e R0678 assorbite.

#### R0700 · S3 · PM (arrotondamenti e minori) · riformulare
- **Bersaglio:** prosa (riga 215); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `### Per-step speedup varies over two orders of magnitude`
- **Valore:** varies over two orders of magnitude → (da rileggere, vedi fonte)
- **Istruzione:** Titolo a riga 215 "### Per-step speedup varies over two orders of magnitude" incoerente con il testo ("nearly two") e con i dati (0.36x-329x, quasi tre ordini). Sostituire con: "### Per-step speedup differs widely between operations". Allineare con la frase corretta in R0349.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0349 campo recomputed (c01_fig1_heatmap.py)
- **Dipende da:** R0349; CONV

#### R0349 · S3 · PM (arrotondamenti e minori) · riformulare
- **Bersaglio:** prosa (riga 217); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `reveal that GPU advantage varies dramatically by operation type, ranging across nearly two orders of magnitude`
- **Valore:** nearly two orders of magnitude → 2.96
- **Istruzione:** A riga 217 sostituire "ranging across nearly two orders of magnitude depending on algorithmic structure and data size" con: "from 0.36x (Leiden at resolution 0.5, 10k cells) to 329x (normalisation, 10k cells), nearly three orders of magnitude; both extremes are set by the first repeat (see below)". Il rimando a Fig. 1 e Fig. 2 resta.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0349 campo recomputed (c01_fig1_heatmap.py, medie r1-r5)
- **Dipende da:** CONV; R0367
- **Nota:** Con convenzione A gli estremi restano 0.36x (Leiden a risoluzione 0.5, 10k) e 329x (normalizzazione, 10k). Se il PI sceglie r2-5 gli estremi diventano 0.78x (data loading, 100k) e 137.4x (normalizzazione, 100k), non 115.1x e 1.12x (valori a 10k): la voce si rigenera con questi.
- **Modificata in arbitrato:** note (vedi `arbitrati.csv`)

#### R0114 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 223); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Data loading from disk was actually faster on CPU across all scales (0.76-0.85x GPU/CPU), because the fixed overhead of CUDA context initialisation and RMM p...`
- **Valore:** (0.76-0.85x GPU/CPU) → +0.096 s (10k), +0.552 s (50k), +1.377 s (100k)
- **Istruzione:** A riga 223 sostituire da "Data loading from disk was actually faster on CPU across all scales (0.76-0.85x GPU/CPU), because ..." fino a "... the transfer completes in milliseconds." con: "Data loading was slightly slower on GPU at all three sizes (0.76-0.85x, CPU time divided by GPU time). The GPU timer covers reading the file and copying the matrix to the device (`anndata_to_GPU`), whereas CUDA context creation and RMM pool allocation happen before the timer starts; the GPU excess grew with dataset size (0.10 s at 10k, 0.55 s at 50k and 1.38 s at 100k cells), so it is a size-dependent transfer cost rather than a fixed overhead." La frase successiva su GDS resta.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0114 campo recomputed (a02_perstep.py; scripts/benchmark_gpu.py run_pipeline righe 228-229)
- **Dipende da:** CONV
- **Assorbe:** R0677
- **Nota:** Nel testo i tre valori arrotondati a 2 decimali (0.10, 0.55, 1.38 s). Il rapporto e' CPU/GPU, non GPU/CPU. Stessa affermazione in Discussione l. 416 (T5).

#### R0116 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 223); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Similarly, Leiden clustering showed a clear dependence on problem size: at 10k cells, CPU was faster (0.36x) due to cuGraph's higher constant-time overhead f...`
- **Valore:** CPU was faster (0.36x) due to cuGraph's higher constant-time overhead → (da rileggere, vedi fonte)
- **Istruzione:** A riga 223 sostituire "Similarly, Leiden clustering showed a clear dependence on problem size: at 10k cells, CPU was faster (0.36x) due to cuGraph's higher constant-time overhead for graph partitioning operations on small graphs, but GPU performance improved ... achieving 3.58x speedup at 100k cells." con: "For Leiden clustering at resolution 0.5 (the value shown in Fig. 1), the CPU was faster at 10k cells (0.36x), but this reflects the first cuGraph call of the first repeat (1.70 s against 0.09 s in later repeats); at resolutions 1.0 and 1.5 the GPU was already faster at 10k cells (1.36x and 1.60x). At resolution 0.5 the GPU was 1.80x faster at 50k and 3.58x faster at 100k cells." Il confronto con lo short paper (8.8x) non si scrive (D-06).
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0116 campo recomputed (a02_perstep.py); revisione_n2_log.csv id=R0367 campo recomputed (GPU r1 1.703 s contro 0.091-0.230 s)
- **Dipende da:** CONV; R0367; D-06
- **Nota:** Stessa interpretazione in Discussione l. 416 (R0500, T5).

#### R0367 · S3 · P9 (convenzione sulle ripetizioni) · aggiungere
- **Bersaglio:** prosa (riga 223); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `at 10k cells, CPU was faster (0.36x) due to cuGraph's higher constant-time overhead for graph partitioning operations on small graphs`
- **Valore:** n.d. → 115.1x; 1.12x
- **Istruzione:** Con la convenzione A (media r1-5) i valori di riga 217, 223 e Fig. 1 restano, ma va dichiarato il peso della ripetizione 1. Aggiungere alla fine del paragrafo di riga 223: "The first repeat of each configuration includes one-off library loading and compilation on both CPU and GPU, and it sets the extreme per-step values at 10k cells: excluding it, normalisation was 115.1x faster on GPU (instead of 329x) and Leiden at resolution 0.5 was 1.12x faster (instead of 0.36x). End-to-end speedups changed by at most 6% from 100k cells upwards."
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0367 campo recomputed (results/{cpu,gpu}_{10000,50000,100000}_r{1..5}_results.json, c01_fig1_heatmap.py colonna excl_r1); S2_P3_convenzione.csv colonna ratio (n>=100000)
- **Dipende da:** CONV
- **Nota:** Se il PI sceglie r2-5 la voce si rigenera. Il 6% viene da SPEC/S2_P3 (da 100k in su differiscono al massimo del 6%). La parte 'convenzioni diverse fra scRNA e spatial' si chiude con CONV.

#### R0548 · S3 · P5 (bibliografia) · togliere
- **Bersaglio:** prosa (riga 223); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `PCIe Gen5 bandwidth (128 GB/s) is not saturated at these sub-gigabyte dataset sizes`
- **Valore:** PCIe Gen5 bandwidth (128 GB/s) → (da rileggere, vedi fonte)
- **Istruzione:** La frase "PCIe Gen5 bandwidth (128 GB/s) is not saturated at these sub-gigabyte dataset sizes, and the transfer completes in milliseconds" esce con la riscrittura di R0114 (il trasferimento non dura millisecondi). Non serve quindi la citazione della scheda NVIDIA. Se S3 decidesse di tenere la cifra, citarla come banda bidirezionale aggregata della scheda NVIDIA H100 (nuova voce bib).
- **Fonte:** revisione_n2_log.csv id=R0548 campo recomputed (https://www.nvidia.com/en-us/data-center/h100/)
- **Dipende da:** R0114
- **Nota:** La stessa cifra compare in Discussione l. 416 (T5).

#### R0352 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 227); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Adding GPUs beyond two provided diminishing returns (Fig. 3)`
- **Valore:** Adding GPUs beyond two provided diminishing returns → (da rileggere, vedi fonte)
- **Istruzione:** Sostituire l'intera sottosezione righe 225-232 (titolo "### Multi-GPU scaling is sublinear: CPU preprocessing dominates" e righe 227-232) con un solo paragrafo: "### Multi-GPU configuration" / "At 500k and 1.3M cells only the hybrid Dask-CUDA pipeline could run. In the configuration used, the expression matrix was passed to PCA and neighbour search as a CuPy array on one device, so these steps ran on a single GPU whatever the number of GPUs allocated: PCA plus neighbour search took 17.23, 16.99 and 17.01 s with 2, 4 and 8 GPUs at 1.3M cells, and 2.98, 2.97 and 3.00 s at 500k cells, where total wall time was 124.5, 125.0 and 124.6 s. At 1.3M cells the 8-GPU run (435.2 s) was 12% faster than the 2-GPU run (493.3 s), but the difference arose in CPU-side data loading (149.0 s against 90.6 s), the jobs ran concurrently, and the 8-GPU job ran on a different node. The aggregate VRAM of the multi-GPU runs reflects the RMM pools pre-allocated by the Dask workers (78.6 GB added at cluster start-up, at 10k as at 1.3M cells), not distributed data. Multi-GPU scaling was therefore not measured. Between 10k and 100k cells the 2-GPU hybrid pipeline was 49-82% slower than the single-GPU pipeline, because it runs preprocessing on the CPU." I rimandi a Fig. 3 e Fig. 4 spariscono (figure tolte, R0354 e R0355). Nessun nuovo run (D-02).
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0352 campo recomputed (results/gpu{,2,4,8}_{N}_r*.json); revisione_n2_log.csv id=R0121 campo recomputed (a03_multigpu.py); revisione_n2_log.csv id=R0117 campo recomputed; revisione_n2_log.csv id=R0368 campo recomputed; revisione_n2_log.csv id=R0641 campo recomputed; revisione_n2_report.md P3
- **Dipende da:** D-02; CONV
- **Assorbe:** R0117
- **Nota:** Primaria del paragrafo multi-GPU. Il report scrive +49% a 10k, R0352 +48%: S3 lo rilegge da results/gpu_10000 e gpu2_10000 timings.total prima di scrivere. Coordinare con Metodi l. 87-90 (R0045, R0404, T2) e Discussione l. 418 (T5). Sulla concorrenza le fonti divergono (R0368: 2, 4 e 8 GPU intercalati; report P3 e peer_review H2: 1, 2 e 4 GPU in parallelo, 8 GPU su poddgx02): S3 rilegge metadata.timestamp e hostname nei JSON gpu{2,4,8}_1300000 prima di scrivere la frase sulla concorrenza.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0368 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 229); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `At 1.3M cells, 8 GPUs (435.2 s) were only 12% faster than 2 GPUs (493.3 s)`
- **Valore:** only 12% faster than 2 GPUs → (da rileggere, vedi fonte)
- **Istruzione:** La frase a riga 229 ("At 1.3M cells, 8 GPUs (435.2 s) were only 12% faster than 2 GPUs (493.3 s).") e' sostituita dal paragrafo di R0352; verificare che il paragrafo attribuisca il 12% al caricamento dati su CPU (149.0 s contro 90.6 s) e ai job su nodi diversi e concorrenti. Non scrivere le allocazioni 32/56/200 core salvo che S3 le metta nei Metodi (traccia T2, P11).
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0368 campo recomputed (slurm/gpu_{2,4,8}.sh righe 13-15)
- **Dipende da:** R0352

#### R0353 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 231); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `in a representative 8-GPU run at 1.3M cells (total 463.4 s), CPU preprocessing (data loading + QC + normalisation + HVG selection) consumed 348.7 s (75%)`
- **Valore:** representative 8-GPU run at 1.3M cells (total 463.4 s) → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la frase a riga 231 ("The timing breakdown (Fig. 4) reveals why: in a representative 8-GPU run at 1.3M cells (total 463.4 s), ... single-GPU operations ... took 97.2 s (21%)."): con D-02 la scomposizione multi-GPU e Fig. 4 escono. Se S3 volesse conservare una quota, usare la media su 5 ripetizioni (78.0% / 3.9% / 18.1%) e non la ripetizione 1.
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0353 campo recomputed (c04_fig4_multigpu.py)
- **Dipende da:** D-02; R0352
- **Assorbe:** R0247, R0708
- **Nota:** Primaria per R0247 e R0708. r1 e' la ripetizione piu' lenta (463.4 contro 422.7-432.4 s).

#### R0121 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 232); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `Since CPU preprocessing is constant regardless of GPU count, and Leiden/UMAP/DE execute on a single GPU, only the PCA and neighbour steps benefit from additi...`
- **Valore:** a classic instance of Amdahl's law → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la frase a riga 232 ("Since CPU preprocessing is constant regardless of GPU count, ... a classic instance of Amdahl's law [@Amdahl1967]."): il preprocessing CPU non e' costante (399.53 / 388.94 / 339.36 s) e PCA e vicini non beneficiano di piu' GPU. D-02 toglie la lettura Amdahl. Se Amdahl1967 non resta citato altrove dopo T5, togliere la voce bib.
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0121 campo recomputed (a03_multigpu.py)
- **Dipende da:** D-02; R0352
- **Nota:** Verificato dal capo. Coordinare con R0467/R0582 (Discussione l. 418, T5).

#### R0244 · S3 · P10 (concordanza) · aggiungere
- **Bersaglio:** prosa (riga 240); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Concordance analysis on the 10,000-cell dataset (Fig. 5) demonstrated that the two pipelines yield near-identical biological conclusions`
- **Istruzione:** Dopo la prima frase di riga 240 ("Concordance analysis on the 10,000-cell dataset (Fig. 5) demonstrated ...") dichiarare la provenienza: "Concordance was computed on a separate pair of 10,000-cell runs made on 11 March 2026, before the timed benchmark; in that run the CPU pipeline found 31, 40 and 45 clusters at resolutions 0.5, 1.0 and 1.5, against 31, 41 and 46 in all five benchmark repeats." Sostituire anche "near-identical biological conclusions" con "closely agreeing outputs".
- **Fonte:** revisione_n2_log.csv id=R0244 campo recomputed (a04_concordance.py: results/concordance_10000_r1.json cpu_timestamp/gpu_timestamp)
- **Dipende da:** R0498
- **Nota:** Alternativa L4 (rifare la concordanza sui run del benchmark, PoW-H): scelta del PI, vedi pi_choices.

#### R0371 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 240); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `though some variation in the k-nearest neighbours across the graph was expected due to floating-point precision differences`
- **Valore:** due to floating-point precision differences → 0.9375
- **Istruzione:** A riga 240 sostituire "though some variation in the k-nearest neighbours across the graph was expected due to floating-point precision differences" con: "This value is bounded by construction: the CPU and GPU neighbour sets compared have different sizes (the maximum and the median per-cell Jaccard are both 0.9375 = 15/16, and no cell reaches 1), so at least half of the cells reach that maximum and differ only by the size mismatch. The remaining differences are consistent with approximate neighbour search on CPU (PyNNDescent, the Scanpy default at this size) against exact brute-force search on GPU [@Gardner2025], rather than with floating-point precision."
- **Fonte:** revisione_n2_log.csv id=R0371 campo recomputed (results/concordance_10000_r1.json knn_concordance; scripts/compare_results.py compare_knn); revisione_n2_log.csv id=R0541 campo recomputed (scanpy pp.neighbors, rapids-singlecell pp.neighbors, Gardner2025)
- **Assorbe:** R0245, R0541, R0652
- **Nota:** Primaria per R0245 e R0541. La causa esatta della differenza di cardinalita' (self incluso o k contro k-1) non e' verificabile senza i *_knn.npz: non scriverla. Correggere coerentemente Fig. 5 (R0376) e Table 2 riga kNN Jaccard (T2, R0489). Alternativa L4 PoW-M (Jaccard senza self): pi_choices.

#### R0128 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 242); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The slightly lower concordance at resolution 1.0, where both pipelines identified 40 clusters, reflects the inherent stochasticity of the Leiden algorithm an...`
- **Valore:** reflects the inherent stochasticity of the Leiden algorithm → (da rileggere, vedi fonte)
- **Istruzione:** A riga 242 sostituire "The slightly lower concordance at resolution 1.0, where both pipelines identified 40 clusters, reflects the inherent stochasticity of the Leiden algorithm and minor differences in the underlying graph-partitioning implementations provided by cuGraph (GPU) versus igraph (CPU), rather than indicating any systematic bias." con: "The lower agreement at resolution 1.0 (40 clusters in both pipelines in the concordance run) does not reflect run-to-run stochasticity: at 10,000 cells each pipeline returned identical labels in all five benchmark repeats. It reflects differences between the two implementations, igraph with `n_iterations=2` on CPU and cuGraph with up to 100 iterations on GPU."
- **Fonte:** revisione_n2_log.csv id=R0128 campo recomputed (a04_concordance.py); peer_review.md H8 (n_iterations=2 contro max_iter=100)
- **Nota:** Coordinare con Table 1 'identical parameters' (T2) e Discussione l. 422 (R0693, T5).

#### R0709 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 242); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `with 30 of the 40 pairs exceeding the stringent threshold of rho > 0.97`
- **Valore:** the stringent threshold of rho > 0.97 → (da rileggere, vedi fonte)
- **Istruzione:** A riga 242 togliere "the stringent threshold of": scrivere "with 34 of the 40 pairs above rho = 0.97". La soglia e' descrittiva e non e' definita nei Metodi; non serve aggiungerla alla Table 2.
- **Fonte:** revisione_n2_log.csv id=R0709 campo recomputed
- **Dipende da:** R0129

#### R0680 · S3 · PM (arrotondamenti e minori) · riformulare
- **Bersaglio:** prosa (riga 250); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `CPU RAM usage scaled approximately linearly with cell count, from 1.2 GB at 10k to 107.4 GB at 1.3M cells`
- **Valore:** scaled approximately linearly → 0.93
- **Istruzione:** A riga 250 sostituire "CPU RAM usage scaled approximately linearly with cell count" con "CPU RAM grew roughly in proportion to cell count (log-log slope 0.92 over 10k-1.3M cells, least squares on the five mean peaks; steeper, 1.35, between 500k and 1.3M cells)". Fonte: results/cpu_{10000,50000,100000,500000,1300000}_r{1..5}_results.json memory.peak_ram_gb, media r1-5 (1.18, 3.56, 6.65, 29.69, 107.35 GiB). La didascalia di Fig. 6 si allinea in R0359 (togliere "super-linearly").
- **Fonte:** revisione_n2_log.csv id=R0139 campo recomputed (a01_table4.py)
- **Dipende da:** R0359
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0138 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 252); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Per-device VRAM traces (available in the benchmark result JSON files in the code repository) show balanced usage across workers during the PCA and neighbour ...`
- **Valore:** Per-device VRAM traces (available in the benchmark result JSON files in the code repository) → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la frase di riga 252 "Per-device VRAM traces (available in the benchmark result JSON files in the code repository) show balanced usage across workers ...": i JSON salvano solo la somma su tutte le GPU (get_total_vram_used_gb). Esce con il paragrafo (R0641).
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0138 campo recomputed (scripts/benchmark_multigpu.py time_step)
- **Dipende da:** R0641

#### R0248 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 252); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Second, we verified through direct scheduler queries (`client.run_on_scheduler()`) that all requested workers were in the `running` state throughout each ben...`
- **Valore:** client.run_on_scheduler() → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la frase di riga 252 "Second, we verified through direct scheduler queries (`client.run_on_scheduler()`) that all requested workers were in the `running` state throughout each benchmark, after identifying and fixing a reporting bug ...": il controllo e' entrato nel codice il 20 marzo (commit 07031f4), dopo i run del 15 marzo, e nessuno dei 75 JSON contiene actual_n_workers. Esce con il paragrafo (R0641).
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0248 campo recomputed (git log scripts/benchmark_multigpu.py; metadata.configuration.dask_cluster)
- **Dipende da:** R0641

#### R0550 · S3 · P11 (ambiente e hardware) · togliere
- **Bersaglio:** prosa (riga 252); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `which are implemented as single-GPU operations in cuGraph 26.2`
- **Valore:** single-GPU operations in cuGraph 26.2 → (da rileggere, vedi fonte)
- **Istruzione:** La frase "... which are implemented as single-GPU operations in cuGraph 26.2" esce con il paragrafo di riga 252 (R0641). Se altrove (Metodi l. 90, Discussione) resta l'attribuzione, scrivere che Leiden gira su una GPU "as called by rapids-singlecell" e che UMAP e' in cuML, non in cuGraph.
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0550 campo recomputed (docs cuGraph; Dicks2026 righe 300-305)
- **Dipende da:** R0641

#### R0551 · S3 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 252); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `rather than silently collapsing onto a single GPU, as reported for some Dask-CUDA configurations`
- **Valore:** as reported for some Dask-CUDA configurations → (da rileggere, vedi fonte)
- **Istruzione:** La frase "(rather than silently collapsing onto a single GPU, as reported for some Dask-CUDA configurations)" esce con il paragrafo di riga 252 (R0641); non serve cercare una citazione.
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0551 campo recomputed
- **Dipende da:** R0641

#### R0641 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 252); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `First, the aggregate peak VRAM at 1.3M cells with 8 GPUs (134.2 GB) exceeds the 80 GB capacity of any single H100 device; this working set could not have fit...`
- **Valore:** this working set could not have fit on one GPU alone → 78.6 GB
- **Istruzione:** Togliere l'intero paragrafo di riga 252 ("To verify that distributed computation was actually occurring across all workers ... single-GPU operations in cuGraph 26.2."): la prova della VRAM aggregata misura gli 8 pool RMM preallocati (+78.6 GB all'avvio del cluster Dask, gia' a 10k cellule), non dati distribuiti, e D-02 riduce il multi-GPU al paragrafo di R0352, che contiene la frase sui pool RMM. Nella stessa sottosezione, a riga 250, sostituire "For multi-GPU runs, aggregate VRAM scaled with worker count: at 1.3M cells with 8 GPUs, the aggregate peak was 134.2 GB (mean 16.8 GB per device, 21% of 80 GB capacity), well below the per-device limit." con "For multi-GPU runs, aggregate VRAM grew with the number of Dask workers, each of which pre-allocates an RMM pool (134.2 GB with 8 GPUs at 1.3M cells, averaged over five repeats)."
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0641 campo recomputed (results/gpu8_1300000_r1_results.json memory.detailed scale_vram_after_gb, pca_vram_before_gb)
- **Dipende da:** D-02; R0352
- **Assorbe:** R0137, R0372, R0681
- **Nota:** Verificato dal capo. Primaria per R0137, R0372, R0681 (stessa frase). Le altre frasi del paragrafo (R0138, R0248, R0550, R0551) escono con esso.

#### R0142 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** prosa (riga 260); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `A binary search for the maximum processable cell count (Table 5) showed that the pipeline succeeded at 11.9 million cells (119 min) and failed at 12.0 millio...`
- **Valore:** (Leiden out-of-memory, SLURM signal 9) → (da rileggere, vedi fonte)
- **Istruzione:** A riga 260 sostituire "failed at 12.0 million cells (Leiden out-of-memory, SLURM signal 9)" con "failed at 12.0 million cells (killed by SLURM for exceeding the memory allocation, signal 9; the operation at which the limit was exceeded was not recorded)". 119 min resta (7,150.62 s). Allineare con Table 5 (R0164) e con l'attribuzione unica di R0674.
- **Fonte:** revisione_n2_log.csv id=R0142 campo recomputed (a05_stress_de.py: maxpower_limit_8gpu.json first_oom_at)
- **Dipende da:** R0674; R0164
- **Nota:** Se S3 trova nel log SLURM lo step del kill (R0164), scriverlo al posto di 'was not recorded'.

#### R0143 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 260); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `A separate test at 13.7 million cells failed earlier, during the CPU-side sparse-to-dense scaling step`
- **Valore:** A separate test at 13.7 million cells failed earlier → (da rileggere, vedi fonte)
- **Istruzione:** S3 cerca sul server (sola lettura, repo 2026.scRNA_DGX) un JSON o un log SLURM del run a 13,745,880 cellule (results/, slurm/ logs, sacct se conservato) che indichi lo step del fallimento. Se lo trova, citare il file nei Metodi o nel repository; se non lo trova, riscrivere la frase di riga 260 come "A separate run at 13.7 million cells failed during the CPU-side scaling step, according to the job log" solo se il log esiste, altrimenti togliere lo step: "A separate run at 13.7 million cells also failed."
- **Fonte:** results/ (nessun JSON a 13.7M); log SLURM sul server da cercare
- **Nota:** Il diario CLAUDE.md non vale come fonte. Stesso esito governa R0152, R0165, R0153.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0243 · S3 · P6 (stress test replicato) · aggiungere
- **Bersaglio:** prosa (riga 260); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `A binary search for the maximum processable cell count (Table 5) showed that the pipeline succeeded at 11.9 million cells (119 min)`
- **Valore:** n.d. → 135,710/142,959/147,154; 58/66/87
- **Istruzione:** Dopo la prima frase di riga 260 aggiungere la dichiarazione della replicazione: "Above 3,436,470 cells the input was built by concatenating whole copies of the source dataset plus a random remainder, so these runs contain duplicated cells; the construction happens between data loading and QC and is not timed. 'Pass' therefore denotes computational completion only: at 11.9M cells Leiden returned 135,710, 142,959 and 147,154 clusters at the three resolutions, against 58, 66 and 87 in a Leiden run on a 3,400,000-cell subset of the source dataset, a run not listed in Table 5." Dichiararlo anche nei Metodi (Stress test, traccia T2). I valori 58/66/87 sono di results/maxpower_3400000_8gpu_results.json (Leiden, cugraph); la riga 3.4M di Table 5 e' il run KMeans a 3,436,470 cellule (k = 50/100/200).
- **Fonte:** revisione_n2_log.csv id=R0243 campo recomputed (results/maxpower_*_8gpu_results.json n_clusters_*; scripts/benchmark_maxpower.py resize_dataset righe 468-524, 580-582)
- **Nota:** Fa parte delle correzioni 'Comunque' del report (P6). Coordinare con abstract (T1) e Discussione l. 424 (T5).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0145 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 262); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Neither figure explains why 12M cells fails, and our instrumentation cannot close the gap`
- **Valore:** Neither figure explains why 12M cells fails → (da rileggere, vedi fonte)
- **Istruzione:** La frase di riga 262 "Neither figure explains why 12M cells fails, and our instrumentation cannot close the gap." resta se S3 non trova dati del run a 12M (stesso controllo di R0164: log SLURM e sacct MaxRSS del job a 12M). Se il log indica lo step o la memoria al kill, riportarli qui.
- **Fonte:** log SLURM e sacct del job a 12,000,000 cellule sul server (da cercare); results/maxpower_limit_8gpu.json
- **Dipende da:** R0164

#### R0148 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** prosa (riga 262); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `First, RAM rises from 124 GB at the end of data loading to 426 GB at the start of quality control, an increase of 302 GB that belongs to no timed step`
- **Valore:** an increase of 302 GB that belongs to no timed step → (da rileggere, vedi fonte)
- **Istruzione:** A riga 262 sostituire "First, RAM rises from 124 GB at the end of data loading to 426 GB at the start of quality control, an increase of 302 GB that belongs to no timed step." con "First, RAM rises from 124 GB at the end of data loading to 426 GB at the start of quality control; this 302 GB increase is the construction of the replicated 11.9M-cell dataset from the 3.4M-cell source, which runs between the two timed steps." Riformulare "Two features of the 11.9M trace make the shortfall explicit" in "Two features of the 11.9M trace show what between-step sampling misses".
- **Fonte:** revisione_n2_log.csv id=R0148 campo recomputed (scripts/benchmark_maxpower.py resize_dataset righe 580-582)
- **Dipende da:** R0243
- **Nota:** Il +302 non e' 'unattributed': si propaga a Table 6 (R0176).

#### R0151 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 262); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `What the data do exclude is clustering as the CPU-side culprit: at 11.9M the three Leiden calls together added less than 1 GB of host RAM, because Leiden exe...`
- **Valore:** aggregate VRAM rose from 28.8 GB to 48.8 GB across those calls → 0.48
- **Istruzione:** A riga 262 sostituire "because Leiden executes on GPU through cuGraph (aggregate VRAM rose from 28.8 GB to 48.8 GB across those calls)" con "(+0.48 GB); the 20 GB rise in aggregate VRAM before the first Leiden call corresponds to the re-initialisation of the RMM pool on device 0, not to Leiden itself". La parte "What the data do exclude ..." si riscrive in R0674.
- **Fonte:** revisione_n2_log.csv id=R0151 campo recomputed (scripts/benchmark_maxpower.py riga 678 rmm.reinitialize)
- **Dipende da:** R0674

#### R0152 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 262); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `The 13.7M failure is a distinct event, occurring during the CPU-side sparse-to-dense scaling step`
- **Valore:** The 13.7M failure is a distinct event → (da rileggere, vedi fonte)
- **Istruzione:** La frase di riga 262 "The 13.7M failure is a distinct event, occurring during the CPU-side sparse-to-dense scaling step." dipende dallo stesso controllo di R0143 (log del run a 13.7M); in ogni caso togliere la frase come ripetizione (R0727).
- **Fonte:** log SLURM del run 13,745,880 sul server (da cercare)
- **Dipende da:** R0143; R0727

#### R0674 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 262); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `What the data do exclude is clustering as the CPU-side culprit`
- **Valore:** What the data do exclude is clustering as the CPU-side culprit → (da rileggere, vedi fonte)
- **Istruzione:** Rendere unica l'attribuzione del fallimento a 12M in Table 5, righe 260 e 262, Table 6 (riga 300) e Discussione (riga 424, T5). Attribuzione proposta, salvo diverso esito di R0164: il job e' stato terminato da SLURM per superamento della memoria allocata e l'operazione che ha superato il limite non e' identificata (nessun JSON o log registra lo step). A riga 262 sostituire "What the data do exclude is clustering as the CPU-side culprit: at 11.9M the three Leiden calls together added less than 1 GB of host RAM" con "At 11.9M the three Leiden calls together changed between-step host RAM by less than 1 GB (+0.48 GB), which, as for normalisation and HVG selection, does not exclude transient allocations within the calls".
- **Fonte:** revisione_n2_log.csv id=R0674 campo recomputed (benchmark_maxpower.py:714 OOMs above ~12M cells); revisione_n2_log.csv id=R0164 campo recomputed (results/maxpower_limit_8gpu.json)
- **Dipende da:** R0164; R0151
- **Nota:** Attribuzione da confermare con il log del job a 12M (R0164): se il log dice altro, S3 cambia la frase. Discussione l. 424: R0211, R0598 (T5). Abstract: R0568 (T1). Contestata: il registro afferma che il kill avviene durante Leiden, ma R0142 e R0164 dicono che lo step non e' registrato.

#### R0153 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 264); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `We also tested cuML KMeans as a GPU-native clustering alternative to Leiden, but the failure point was identical (13.7M) because the out-of-memory event occu...`
- **Valore:** the failure point was identical (13.7M) → (da rileggere, vedi fonte)
- **Istruzione:** S3 cerca sul server un JSON o log di un run KMeans a 13.7M (i JSON KMeans presenti sono 3.44M, 6.87M, 10.31M, tutti Pass). Se non esiste, sostituire a riga 264 "but the failure point was identical (13.7M) because the out-of-memory event occurred during CPU preprocessing, before clustering was invoked" con "in runs up to 10.3 million cells (Table 5)" e togliere l'affermazione sul punto di fallimento.
- **Fonte:** da cercare: results/maxpower_*_8gpu_results.json (metodo di clustering registrato nel JSON) e log SLURM in logs/; l'istruzione prevede che il run a 13.7M possa non esistere
- **Dipende da:** R0143
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0154 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 265); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Similarly, a sparse-scatter optimisation that avoided the CPU-side dense matrix was tested at 14M cells but failed during Scanpy's HVG selection step, confir...`
- **Valore:** tested at 14M cells but failed during Scanpy's HVG selection step → (da rileggere, vedi fonte)
- **Istruzione:** S3 cerca sul server un JSON o log del run sparse-scatter a 14M. Se non esiste, a riga 265 togliere "confirming that Scanpy's CPU-side preprocessing is the ultimate capacity bottleneck" e scrivere "a sparse-scatter variant that avoided the CPU-side dense matrix also failed at 14M cells, during HVG selection according to the job log" solo se il log c'e'; altrimenti togliere la frase.
- **Fonte:** log del run sparse-scatter 14M sul server (da cercare)
- **Dipende da:** R0710
- **Nota:** Il diario CLAUDE.md non vale come fonte. Stessa fonte per R0185 (629 GB).

#### R0710 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 267); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Inspired by the chunked-preprocessing strategy of ScaleSC [@Hu2025], we also implemented a third variant`
- **Valore:** Inspired by the chunked-preprocessing strategy of ScaleSC [@Hu2025] → (da rileggere, vedi fonte)
- **Istruzione:** Le varianti sparse-scatter (riga 265) e chunked (riga 267) e la 'variant pipeline at 14M cells' (riga 304) sono descritte solo nei Risultati. Spostare nei Metodi (Stress test, righe 107-111, traccia T2) una frase per variante (cosa cambia rispetto alla pipeline memory-optimised) e lasciare nei Risultati solo esiti e numeri. Se S6 deve tagliare (D-03), la variante sparse-scatter senza JSON (R0154) e' la prima candidata.
- **Decisione o convenzione:** D-03
- **Fonte:** revisione_n2_log.csv id=R0710 campo recomputed
- **Dipende da:** R0154; R0156

#### R0164 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** tabella:Table 5 riga 12.0M (riga 278); registro: UNVERIFIABLE, major
- **Ancora (univoca nel .md):** `12.0M | --- | --- | --- | Leiden | Fail (Leiden OOM)`
- **Valore:** Fail (Leiden OOM) → (da rileggere, vedi fonte)
- **Istruzione:** S3 cerca sul server il log SLURM e, se disponibile, sacct (State, MaxRSS) del job a 12,000,000 cellule. Se il log indica lo step, Status = "Fail (OOM during <step>)"; altrimenti sostituire "Fail (Leiden OOM)" con "Fail (OOM, step not recorded)". Il valore deve coincidere con R0142 e R0674.
- **Fonte:** results/maxpower_limit_8gpu.json first_oom_at; log SLURM e sacct del job a 12M sul server (da cercare)
- **Nota:** Il commento di scripts/benchmark_maxpower.py riga 714 attribuisce l'OOM a Leiden: non e' una misura.

#### R0165 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** tabella:Table 5 riga 13.7M (riga 279); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `13.7M | --- | --- | --- | Leiden | Fail (scale OOM)`
- **Valore:** Fail (scale OOM) → (da rileggere, vedi fonte)
- **Istruzione:** Stesso controllo di R0143 (log del run a 13.7M). Se il log conferma lo scaling, lasciare "Fail (scale OOM)"; altrimenti "Fail (OOM, step not recorded)". Nella colonna Clustering scrivere quanto risulta dal log.
- **Fonte:** log SLURM del run 13,745,880 sul server (da cercare)
- **Dipende da:** R0143

#### R0166 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 281); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The three smaller rows were benchmarked with cuML KMeans rather than Leiden to isolate the CPU preprocessing cost from the clustering cost; KMeans and Leiden...`
- **Valore:** KMeans and Leiden exhibit the same CPU-RAM and CPU-preprocessing footprint → (da rileggere, vedi fonte)
- **Istruzione:** Sostituire la frase di riga 281 ("The three smaller rows were benchmarked with cuML KMeans rather than Leiden ... valid ascending points on the runtime/memory curves.") con: "The three smaller rows were run with cuML KMeans instead of Leiden. Peak CPU RAM was similar for the two clustering methods at about 10M cells (465.4 GB with KMeans at 10.31M, 460.5 GB with Leiden at 10.2M), but runtimes were not (91.5 against 69.2 min, with QC taking 3,156 against 2,218 s; the runs were made on different days), so the runtime column combines two series and should not be read as a single curve."
- **Fonte:** revisione_n2_log.csv id=R0166 campo recomputed (results/maxpower_*_8gpu_results.json)
- **Dipende da:** R0153; R0727
- **Assorbe:** R0682
- **Nota:** Primaria per R0682. Il registro riporta GiB; il manoscritto usa 'GB' per gli stessi valori psutil: S3 uniforma l'unita' (P11/PM).

#### R0177 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** tabella:Table 6 riga adata.raw copy (riga 295); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** ``adata.raw = adata.copy()` (estimated) | +400`
- **Valore:** +400 → (da rileggere, vedi fonte)
- **Istruzione:** Tenere "`adata.raw = adata.copy()` (estimated)" come stima, ma dichiarare in nota la formula: una copia della matrice sparsa completa, circa 420 GB, transitorio non campionato fra HVG e scale. Sostituire +400 con il valore della copia sparsa usato in R0171.
- **Fonte:** revisione_n2_log.csv id=R0177 campo recomputed; R0171
- **Dipende da:** R0171; R0167

#### R0178 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** tabella:Table 6 riga sc.pp.scale (riga 296); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Sparse to dense scaling, `sc.pp.scale` (estimated) | +200`
- **Valore:** +200 → 81.71
- **Istruzione:** Tenere "Sparse to dense scaling, `sc.pp.scale` (estimated) | +200" come stima con formula in nota, e affiancare il delta netto misurato fra HVG e scale (+81.71 GiB, R0252) per mostrare che il picco transitorio non e' campionato.
- **Fonte:** revisione_n2_log.csv id=R0178 campo recomputed
- **Dipende da:** R0167
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0179 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** tabella:Table 6 riga CSR-CSC (riga 297); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `CSR to CSC layout conversion (estimated) | +190`
- **Valore:** +190 → (da rileggere, vedi fonte)
- **Istruzione:** Tenere "CSR to CSC layout conversion (estimated) | +190" solo con la formula in nota (una copia della matrice sparsa nell'altro layout); poiche' la copia sparsa e' circa 420 GB e non 190 (R0171), ricalcolare la stima con la stessa formula oppure scrivere n.q.
- **Fonte:** revisione_n2_log.csv id=R0179 campo recomputed; R0171
- **Dipende da:** R0171; R0167

#### R0180 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** tabella:Table 6 riga HVG (riga 298); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Scanpy `highly_variable_genes` internal temporaries | n.q`
- **Valore:** n.q. → (da rileggere, vedi fonte)
- **Istruzione:** La voce "Scanpy `highly_variable_genes` internal temporaries | n.q." resta n.q. salvo che S3 trovi il log del run a 14M citato a riga 304 (R0185); in quel caso aggiungere in nota il valore e la fonte.
- **Fonte:** log del run variante a 14M sul server (da cercare)
- **Dipende da:** R0185

#### R0181 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** tabella:Table 6 riga Dask workers (riga 299); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Eight Dask-CUDA worker processes | n.q`
- **Valore:** n.q. → (da rileggere, vedi fonte)
- **Istruzione:** S3 controlla se sacct conserva MaxRSS per i job a 11.9M e 12M (la memoria dei worker Dask e' nel cgroup ma non nel campionamento del processo padre). Se c'e', riportarlo in nota come misura del job intero; altrimenti la voce resta n.q.
- **Fonte:** sacct -j <jobid> --format=JobID,State,MaxRSS sui job a 11.9M e 12M (sola lettura, da cercare)

#### R0182 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** tabella:Table 6 riga Leiden (riga 300); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Leiden internal structures (executes on GPU; host delta at 11.9M < 1 GB) | ~50`
- **Valore:** ~50 → 0.48
- **Istruzione:** Sostituire "Leiden internal structures (executes on GPU; host delta at 11.9M < 1 GB) | ~50" con "Leiden calls (host delta between steps at 11.9M) | < 1": i ~50 GB non hanno fonte e contraddicono il delta misurato (+0.48 GB).
- **Fonte:** revisione_n2_log.csv id=R0182 campo recomputed
- **Dipende da:** R0167; R0674

#### R0185 · S3 · P6 (stress test replicato) · verificare-in-step
- **Bersaglio:** prosa (riga 304); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Scanpy's `highly_variable_genes` was observed to trigger an out-of-memory event from a 629 GB baseline in a variant pipeline at 14M cells, implying internal ...`
- **Valore:** 629 GB baseline → (da rileggere, vedi fonte)
- **Istruzione:** S3 cerca sul server il JSON o log della variante a 14M (baseline 629 GB, OOM in highly_variable_genes). Se esiste, citare il file; se no, a riga 304 sostituire "was observed to trigger an out-of-memory event from a 629 GB baseline in a variant pipeline at 14M cells, implying internal temporaries in excess of 1,100 GB; it is the largest single transient we have direct evidence for" con "failed with an out-of-memory error in a variant pipeline at 14M cells (Section on variants above)" senza cifre.
- **Fonte:** log della variante 14M sul server (da cercare); stessa fonte di R0154
- **Dipende da:** R0154

#### R0688 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 306); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `### Differential expression: pseudo-bulk is fastest and most correct`
- **Valore:** pseudo-bulk is fastest and most correct → (da rileggere, vedi fonte)
- **Istruzione:** Titolo a riga 306 "### Differential expression: pseudo-bulk is fastest and most correct": sostituire con "### Differential expression: run-time comparison". A riga 308 sostituire "revealed important trade-offs between computational efficiency and statistical rigor" con "compares run times only; statistical properties of the tests were not assessed". D-04: nessuna affermazione di rigore statistico.
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0688 campo recomputed; decisioni_D01_D13.txt D-04
- **Dipende da:** D-04
- **Nota:** Le stesse affermazioni in Metodi l. 115 (T2), Discussione l. 426 (R0603, R0609, T5), Conclusioni l. 439 (R0635, T4).

#### R0686 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 308); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `a CPU Wilcoxon baseline at this scale was infeasible to measure (extrapolation from smaller subsamples places it above four hours)`
- **Valore:** was infeasible to measure → (da rileggere, vedi fonte)
- **Istruzione:** A riga 308 sostituire "a CPU Wilcoxon baseline at this scale was infeasible to measure (extrapolation from smaller subsamples places it above four hours)" con "a CPU Wilcoxon baseline was not run at this scale". L'estrapolazione si tiene solo se S3 trova sul server lo script o il log che la produce (metodo e numeri); altrimenti si toglie.
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0686 campo recomputed; script/log dell'estrapolazione sul server (da cercare)
- **Dipende da:** D-04
- **Nota:** La pipeline CPU a 1.3M ha girato 5 volte per 14.5 h: 4 h non dimostrano infattibilita'.

#### R0196 · S3 · P7 (espressione differenziale) · correggere
- **Bersaglio:** prosa (riga 321); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Pseudo-bulk aggregation emerged as the dominant strategy: aggregating raw counts by donor and cluster reduced the analysis from 3.4 million individual cells ...`
- **Valore:** a few hundred pseudo-samples per cluster → 2,431; 30.0; 127.47; 43.91
- **Istruzione:** Sostituire la prima frase di riga 321 ("Pseudo-bulk aggregation emerged as the dominant strategy: aggregating raw counts by donor and cluster reduced the analysis from 3.4 million individual cells to a few hundred pseudo-samples per cluster, completing in 128 seconds (2.1 minutes), a 43.7x speedup relative to the cell-level CPU t-test baseline (5,598 s, 93 minutes).") con: "Pseudo-bulk aggregation was the fastest strategy: aggregating log-normalised expression by donor and cluster reduced 3.4 million cells to 2,431 pseudo-samples (about 30 per cluster), and the analysis completed in 127 s (2.1 min), 43.9 times sooner than the cell-level CPU t-test (5,598 s, 93 min)." "raw counts" e' sbagliato: lo pseudo-bulk somma valori gia' log-normalizzati (report P7, D-04).
- **Decisione o convenzione:** D-04
- **Fonte:** revisione_n2_log.csv id=R0196 campo recomputed (results/de_benchmark_pseudobulk.json results.pseudobulk); revisione_n2_report.md P7
- **Dipende da:** D-04; R0191
- **Assorbe:** R0469, R0557
- **Nota:** Primaria per R0469 e R0557. Coordinare con Metodi l. 115 'a few hundred pseudo-samples' (R0687, T2).

#### R0571 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 412); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Our benchmark demonstrates that rapids-singlecell on NVIDIA H100 GPUs delivers consistent, large-magnitude speedups over Scanpy for the standard scRNA-seq an...`
- **Valore:** nearly 12 million cells → 11.9 million cells
- **Istruzione:** Riga 412, prima frase della Discussione. Sostituire 'delivers consistent, large-magnitude speedups over Scanpy for the standard scRNA-seq analysis pipeline, with high biological concordance and practical scalability to nearly 12 million cells on a single DGX H100 node' con: "shortened the standard Scanpy pipeline by one to two orders of magnitude, with speedups that grew with dataset size and that, at 1.3M cells, were driven mainly by CPU differential expression (Table 4); CPU and GPU results agreed closely at 10,000 cells, and the memory-optimised variant processed up to 11.9 million cells, obtained by replicating a 3.4M-cell dataset." Non mettere cifre di speedup in questa frase: restano nei Risultati (Table 4 e frase sul peso del DE, traccia T3).
- **Fonte:** full_paper_LNBI.md riga 260 (massimo della variante memory-optimised); report P6 e P8
- **Dipende da:** R0082
- **Nota:** 'Consistent' non regge (lo speedup dipende da pipeline e peso del DE) e 12M sono copie di 3.4M. Coordinare con le voci T3 su P6 (replica) e P8 (peso del Wilcoxon). Il ricalcolo del registro '8-46x (1 GPU 10k-100k)' mescola configurazioni e convenzioni: vedi contested_rows.

#### R0575 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 416); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Normalisation and neighbour graph construction represent ideal GPU workloads, achieving speedups of 88-329x and 44-88x respectively, because they involve hig...`
- **Valore:** because they involve high arithmetic intensity → 173-329x
- **Istruzione:** Riga 416: sostituire 'Normalisation and neighbour graph construction represent ideal GPU workloads, achieving speedups of 88-329x and 44-88x respectively, because they involve high arithmetic intensity and are trivially parallelisable across many data elements.' con: "Normalisation (173-329x), an element-wise operation limited by memory bandwidth rather than by arithmetic, and neighbour graph construction (44-88x) benefited most from the GPU." I Risultati (riga 217) descrivono la normalizzazione come 'only element-wise division and logarithm'.
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0575 campo recomputed; full_paper_LNBI.md riga 217
- **Dipende da:** R0199; CONV
- **Assorbe:** R0543, R0679
- **Nota:** Il meccanismo 'high arithmetic intensity' è l'opposto di un'operazione element-wise e contraddice il roofline citato due frasi dopo.

#### R0576 · S3 · P9 (convenzione sulle ripetizioni) · riformulare
- **Bersaglio:** prosa (riga 416); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `In contrast, data loading from disk and Leiden clustering on small graphs show no GPU advantage or even a CPU advantage, but for different reasons`
- **Valore:** show no GPU advantage or even a CPU advantage → 0.36x; 1.36x; 1.60x
- **Istruzione:** Riga 416: sostituire 'In contrast, data loading from disk and Leiden clustering on small graphs show no GPU advantage or even a CPU advantage, but for different reasons.' con: "In contrast, data loading was slower on the GPU at every size tested (0.76-0.85x), and Leiden at 10,000 cells was slower on the GPU only at the first resolution (0.36x, mean of five repeats), an effect of the first cuGraph call in the first repeat; at resolutions 1.0 and 1.5 the GPU was faster (1.36x and 1.60x)."
- **Decisione o convenzione:** CONV
- **Fonte:** righe_da_pianificare.csv id=R0576 campo recomputed (tracks/F_work/f02_scrna_pow.py PoW-4); data loading da full_paper_LNBI.md riga 223
- **Dipende da:** CONV; R0116; R0114; R0367
- **Nota:** Con la convenzione 2-5 il Leiden a 10k sarebbe 1.12x anche alla prima risoluzione e la frase perderebbe la parte sul vantaggio CPU.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0577 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 416); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `For data loading the culprit is not bandwidth: at sub-gigabyte dataset sizes PCIe Gen5 (128 GB/s) is far from saturated and the transfer itself completes in ...`
- **Valore:** fixed overhead of CUDA context initialisation and RMM pool allocation → +0.10 / +0.55 / +1.38 s
- **Istruzione:** Riga 416: sostituire la frase da 'For data loading the culprit is not bandwidth:' a '...rather than via GPU Direct Storage.' con: "For data loading, CUDA context initialisation and RMM pool allocation took place before the timer (Methods), so the timed GPU step comprised reading the h5ad file through CPU RAM and transferring the matrix to the device; its excess over the CPU (+0.10, +0.55 and +1.38 s from 10k to 100k cells) grew with dataset size, which is consistent with reading and conversion costs rather than with a fixed overhead." Prima di scrivere, S3 conferma in tracks/A_work/a02_perstep.py che i tre valori corrispondono a 10k, 50k e 100k.
- **Fonte:** righe_da_pianificare.csv id=R0200 campo recomputed; scripts/benchmark_gpu.py righe 225-245; Methods riga 83
- **Dipende da:** R0114; R0459
- **Assorbe:** R0200
- **Nota:** La spiegazione attuale attribuisce lo 0.76-0.85x a costi esclusi dal cronometro e contraddice i Methods (riga 83). La stessa spiegazione è nei Risultati, riga 223 (traccia T3).

#### R0578 · S3 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa; bib:Williams2009 (riga 416); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Leiden clustering on small graphs is limited by low arithmetic intensity: consistent with the roofline model [@Williams2009], cuGraph's constant-time overhea...`
- **Valore:** consistent with the roofline model [@Williams2009] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 416: togliere la frase 'Leiden clustering on small graphs is limited by low arithmetic intensity: consistent with the roofline model [@Williams2009], cuGraph's constant-time overhead exceeds CPU's short runtime when the graph has few nodes, and the GPU compute units are not saturated.'. La spiegazione corretta (prima chiamata cuGraph) è già nella frase riscritta da R0576. Se serve un cenno, aggiungere: "The two Leiden implementations also did different amounts of work (igraph with two iterations, cuGraph with up to 100; Methods)." Williams2009 è citato solo in questa riga: toglierlo da cibb2026_references.bib.
- **Fonte:** righe_da_pianificare.csv id=R0578 campo recomputed (n_iterations=2 in scripts/benchmark_cpu.py; max_iter=100 default di rsc 0.14.1); cibb2026_references.bib
- **Dipende da:** R0576
- **Assorbe:** R0201, R0500
- **Nota:** Il roofline (Williams2009) non modella overhead fissi; i due Leiden non fanno lo stesso lavoro. La Table 1 ('identical parameters') va corretta nei Metodi (T2).

#### R0579 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 416); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `This heterogeneous speedup landscape has important practical implications for practitioners: GPU acceleration is most valuable for large datasets where the c...`
- **Valore:** on small datasets the overhead of GPU operations may outweigh their benefits → 12.0; 54.9%
- **Istruzione:** Riga 416, ultima frase: sostituire 'This heterogeneous speedup landscape has important practical implications for practitioners: GPU acceleration is most valuable for large datasets where the compute-heavy operations dominate overall runtime, whereas on small datasets the overhead of GPU operations may outweigh their benefits.' con: "In practice, the GPU advantage grew with dataset size, but even at the smallest size tested (10,000 cells) the GPU pipeline was 12.0-fold faster end to end, partly because CPU differential expression took 54.9% of the CPU time; we did not observe a size at which GPU overhead outweighed its benefit." Facoltativo, dopo verifica in Dicks2026 in S3: "Dicks et al. [@Dicks2026] report such an overhead below about 50,000 cells without differential expression."
- **Decisione o convenzione:** CONV
- **Fonte:** S2_P3_convenzione.csv n=10000 gpu=gpu spd_r1_5; righe_da_pianificare.csv id=R0579 campo note
- **Dipende da:** CONV
- **Assorbe:** R0712
- **Nota:** Il riferimento a Dicks2026 viene dalla nota del registro ('sotto ~50k celle senza DE'), non letto nel PDF in questa sessione.

#### R0586 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 420); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Related to this, most of the practical value of the GPU speedup is accessible without a DGX at all`
- **Valore:** most of the practical value of the GPU speedup is accessible without a DGX at all → (da rileggere, vedi fonte)
- **Istruzione:** Riga 420: sostituire 'Related to this, most of the practical value of the GPU speedup is accessible without a DGX at all.' con: "Because only one GPU computed in our multi-GPU configuration, we expect most of the benefit to be available on a single H100, although we did not run the hybrid pipeline with one GPU at 500k or 1.3M cells." Se il PI sceglie di togliere il paragrafo sul costo (pi_choices, D-03), questa frase resta sola, come chiusura del paragrafo multi-GPU.
- **Fonte:** righe_da_pianificare.csv id=R0586 campo recomputed (results/: nessun gpu_500000_* o gpu_1300000_*)
- **Dipende da:** R0581; D-02
- **Nota:** Plausibile perché tutto il calcolo GPU stava su GPU 0, ma non misurato: va scritto come attesa.

#### R0587 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 420); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `At dataset sizes below 500,000 cells the full standard pipeline fits on a single H100 GPU, and the memory-optimised variant described here extends single-GPU...`
- **Valore:** below 500,000 cells → 10k/50k/100k
- **Istruzione:** Riga 420: sostituire 'At dataset sizes below 500,000 cells the full standard pipeline fits on a single H100 GPU, and the memory-optimised variant described here extends single-GPU feasibility to 1.3M cells and beyond.' con: "The standard pipeline ran on a single H100 up to 100,000 cells, the largest single-GPU size we measured; the memory-optimised variant was run only with 8 GPUs."
- **Fonte:** righe_da_pianificare.csv id=R0587 campo recomputed (results/gpu_*; results/maxpower_*_8gpu_results.json metadata.n_gpus=8)
- **Dipende da:** R0586
- **Assorbe:** R0206, R0691
- **Nota:** La soglia fra 100k e 500k non è determinata; 'single-GPU feasibility to 1.3M and beyond' non è stata testata.

#### R0589 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 420); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Access to a full DGX is therefore not a prerequisite for adopting these methods; the results are directly relevant to individual researchers and small groups...`
- **Valore:** Access to a full DGX is therefore not a prerequisite for adopting these methods → (da rileggere, vedi fonte)
- **Istruzione:** Riga 420: sostituire 'Access to a full DGX is therefore not a prerequisite for adopting these methods; the results are directly relevant to individual researchers and small groups with pay-as-you-go cloud budgets.' con: "If confirmed on a single GPU, this would make the approach usable without a DGX, for example on rented cloud GPUs." In S6, con D-03, valutare di fondere R0586-R0589 in due frasi.
- **Fonte:** righe_da_pianificare.csv id=R0589 campo recomputed
- **Dipende da:** R0586; R0587; R0588
- **Nota:** Dipende da misure single-GPU a 1.3M che non esistono: si scrive come ipotesi.

#### R0590 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 422); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `The biological outputs of GPU and CPU pipelines show high agreement despite computing on fundamentally different architectures and hardware`
- **Valore:** show high agreement despite computing on fundamentally different architectures and hardware → (da rileggere, vedi fonte)
- **Istruzione:** Riga 422: sostituire 'The biological outputs of GPU and CPU pipelines show high agreement despite computing on fundamentally different architectures and hardware.' con: "At 10,000 cells, the only size at which we measured concordance, the biological outputs of the GPU and CPU pipelines agreed closely."
- **Fonte:** righe_da_pianificare.csv id=R0590 campo recomputed (results/concordance_10000_r1.json)

#### R0592 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 422); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `The adjusted Rand indices for Leiden clustering range from 0.908 to 0.963 across different resolutions, entirely consistent with the algorithm's inherent sto...`
- **Valore:** entirely consistent with the algorithm's inherent stochasticity → (da rileggere, vedi fonte)
- **Istruzione:** Riga 422: sostituire 'The adjusted Rand indices for Leiden clustering range from 0.908 to 0.963 across different resolutions, entirely consistent with the algorithm's inherent stochasticity across implementations (igraph vs cuGraph) and with published benchmarks of clustering variability in scRNA-seq workflows [@Duo2020].' con: "The adjusted Rand indices for Leiden clustering ranged from 0.908 to 0.963 across resolutions, in a concordance run separate from the timed repeats. Since each pipeline returned identical labels in all five timed repeats at this size, these differences reflect the two implementations and their settings (igraph with two iterations, cuGraph with up to 100) rather than run-to-run stochasticity." Togliere [@Duo2020] da questa frase (Duo2020 non confronta implementazioni dello stesso algoritmo); resta citato alle righe 94 e 244.
- **Fonte:** righe_da_pianificare.csv id=R0592 campo recomputed (tracks/F_work/f02_determinism.csv; scripts/benchmark_cpu.py righe 236-240; results/concordance_10000_r1.json)
- **Dipende da:** R0578; R0540 (assorbita in R0498)
- **Assorbe:** R0502
- **Nota:** La concordanza viene da un run dell'11 marzo diverso dal benchmark (CPU 40/45 cluster contro 41/46).

#### R0593 · S3 · P10 (concordanza) · togliere
- **Bersaglio:** prosa (riga 422); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Floating-point non-associativity in GPU parallel reductions contributes negligibly to observed differences, as the dominant source of variation is the Leiden...`
- **Valore:** contributes negligibly to observed differences → (da rileggere, vedi fonte)
- **Istruzione:** Riga 422: togliere 'Floating-point non-associativity in GPU parallel reductions contributes negligibly to observed differences, as the dominant source of variation is the Leiden algorithm's non-deterministic vertex ordering.'. Se serve una frase al suo posto: "We did not separate the contributions of numerical differences and of the clustering implementation."
- **Fonte:** righe_da_pianificare.csv id=R0593 campo recomputed (tracks/F_work/f02_determinism.csv)
- **Assorbe:** R0249, R0542, R0693
- **Nota:** A 10k entrambe le pipeline sono deterministiche fra ripetizioni; nessun esperimento GPU-GPU o grafo comune (PoW-H non eseguito).

#### R0594 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 422); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `This level of concordance is reassuring for practitioners: it indicates that GPU-accelerated and CPU-based analyses remain interchangeable for biological int...`
- **Valore:** remain interchangeable for biological interpretation and conclusions → (da rileggere, vedi fonte)
- **Istruzione:** Riga 422: sostituire 'This level of concordance is reassuring for practitioners: it indicates that GPU-accelerated and CPU-based analyses remain interchangeable for biological interpretation and conclusions.' con: "At 50,000 cells and above, however, GPU Leiden labels varied across repeats with a fixed seed, and other studies report CPU-GPU adjusted Rand indices near 0.5 at large sizes [@Gardner2025; @Nolet2022]; whether the two pipelines are interchangeable at atlas scale therefore remains to be shown." In S3 rileggere Gardner2025 (p. 355) e Nolet2022 (p. 6) per le cifre prima di scriverle.
- **Fonte:** righe_da_pianificare.csv id=R0594 campo recomputed (ARI ~0.5 Gardner 2025; ARI 0.54 a 1.3M Nolet 2022); tracks/F_work/f02_determinism.csv
- **Dipende da:** R0540 (assorbita in R0498); R0498
- **Assorbe:** R0650, R0664
- **Nota:** Stessa affermazione nei Risultati (riga 244, T3) e nelle Conclusioni (riga 436, T4): vanno allineate.

#### R0595 · S3 · P12 (novità e posizionamento) · riformulare
- **Bersaglio:** prosa (riga 424); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Perhaps most importantly, our findings reveal that CPU-side memory pressure during preprocessing, not GPU VRAM, is the binding constraint on scalability at e...`
- **Valore:** is the binding constraint on scalability at extreme scale → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: sostituire 'Perhaps most importantly, our findings reveal that CPU-side memory pressure during preprocessing, not GPU VRAM, is the binding constraint on scalability at extreme scale.' con: "In the memory-optimised pipeline we tested, CPU-side memory during Scanpy preprocessing, not GPU VRAM, limited the number of cells; ScaleSC [@Hu2025] and Dicks et al. [@Dicks2026] reach larger datasets with chunked or out-of-core preprocessing, so this limit belongs to the pipeline rather than to GPU analysis in general."
- **Fonte:** righe_da_pianificare.csv id=R0595 campo recomputed; peer_review.md sezione 1 (ScaleSC 13M su una A100; Dicks 2026 100M su 8 B300)
- **Dipende da:** R0633
- **Nota:** Vincolo della pipeline (preprocessing Scanpy in memoria), non dell'analisi GPU in generale.

#### R0596 · S3 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 424); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `This challenges the common intuition that GPU memory availability limits GPU-accelerated analysis`
- **Valore:** This challenges the common intuition that GPU memory availability limits GPU-accelerated analysis. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: togliere 'This challenges the common intuition that GPU memory availability limits GPU-accelerated analysis.' (nessuna fonte per la 'common intuition').
- **Fonte:** righe_da_pianificare.csv id=R0596 campo note

#### R0598 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 424); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Critically, the 12M-cell failure did not occur because CPU RAM was exhausted on average (535 GB is only 30% of the 1.8 TB job allocation): it occurred becaus...`
- **Valore:** it occurred because transient memory spikes → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: sostituire da 'Critically, the 12M-cell failure did not occur because CPU RAM was exhausted on average' a '...although our step-level sampling cannot establish which.' con: "The 12M-cell failure did not coincide with an exhausted average allocation (535 GB is 30% of the 1.8 TB job allocation); we hypothesise that transient allocations within preprocessing steps exceeded the SLURM cgroup limit, but our between-step sampling of the parent process cannot confirm this (Table 6)." Non indicare come causa la duplicazione di adata.raw: il salto di 302 GB è la replicazione del dataset (report P6).
- **Fonte:** righe_da_pianificare.csv id=R0598 campo recomputed (535/1800 = 29.7%); Results riga 262; Methods riga 111
- **Dipende da:** R0148; R0674
- **Assorbe:** R0211
- **Nota:** I Risultati (riga 262) dichiarano l'attribuzione irrisolta; Table 5 dice ancora 'Leiden OOM' (T3).

#### R0599 · S3 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 424); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `The bottleneck is therefore not "RAM being full" in the usual sense but a set of short-lived peaks that the scanpy preprocessing stack is structured to create`
- **Valore:** a set of short-lived peaks that the scanpy preprocessing stack is structured to create → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: togliere 'The bottleneck is therefore not "RAM being full" in the usual sense but a set of short-lived peaks that the scanpy preprocessing stack is structured to create.' (non misurato; vedi R0598).
- **Fonte:** righe_da_pianificare.csv id=R0599 campo recomputed
- **Dipende da:** R0598

#### R0600 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 424); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Substantial further gains in capacity could be realised through preprocessing frameworks that avoid these transient peaks (e.g., reference-only `adata.raw`, ...`
- **Valore:** streaming Leiden on partitions → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: sostituire 'Substantial further gains in capacity could be realised through preprocessing frameworks that avoid these transient peaks (e.g., reference-only `adata.raw`, streaming Leiden on partitions, chunked sparse-to-dense transforms), since GPU VRAM remains heavily underutilised even at near-maximum cell counts.' con: "Preprocessing that avoids dense or duplicated host-side intermediates, as in chunked approaches such as ScaleSC [@Hu2025], is the natural route to larger datasets." Via 'streaming Leiden' (i Risultati escludono il Leiden lato host, riga 262) e 'heavily underutilised' (la VRAM registrata è dominata dai pool RMM).
- **Fonte:** righe_da_pianificare.csv id=R0600 campo recomputed; Results riga 262
- **Dipende da:** R0598

#### R0601 · S3 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 424); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The capacity limit is more accurately described as a function of cells x HVGs rather than cell count alone, because the dense scaled matrix materialised duri...`
- **Valore:** 20M cells at 1,000 HVGs and 4M cells at 5,000 HVGs → (da rileggere, vedi fonte)
- **Istruzione:** Riga 424: togliere la frase 'The capacity limit is more accurately described as a function of cells x HVGs ... with 2,000 HVGs this suggests 20M cells at 1,000 HVGs and 4M cells at 5,000 HVGs as linear-extrapolation operating points.'. Le cifre non seguono da nessun modello coerente con i dati (23.8M e 4.76M con proporzionalità inversa; 13.1M e 9.4M con il bilancio di Table 6). Solo se il PI vuole un cenno (pi_choices): "The dense HVG matrix accounted for 16.6% of the recorded peak (88.7 of 534.6 GiB), so changing the number of HVGs would shift capacity only moderately."
- **Fonte:** righe_da_pianificare.csv id=R0601 campo recomputed (tracks/F_work/f04_capacity_hvg.csv)
- **Assorbe:** R0212, R0684
- **Nota:** Table 6 attribuisce alla matrice densa 96 GB su 535 GB: il limite non scala in proporzione inversa agli HVG.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0603 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 426); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Pseudo-bulk differential expression represents the optimal balance between computational efficiency and statistical rigour`
- **Valore:** represents the optimal balance between computational efficiency and statistical rigour → (da rileggere, vedi fonte)
- **Istruzione:** Riga 426, per D-04: sostituire 'Pseudo-bulk differential expression represents the optimal balance between computational efficiency and statistical rigour.' con: "In our timing comparison, pseudo-bulk aggregation was the fastest route to a differential expression result (Table 7)." Nella frase successiva togliere 'Our DE benchmark confirms that' (il benchmark non valuta il rigore) e scrivere: "Pseudo-bulk aggregation is recommended to avoid pseudoreplication [@Squair2021], and in our benchmark it was also 44 times faster than the cell-level t-test."
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0603 campo recomputed; decisioni_D01_D13.txt D-04; Table 7
- **Dipende da:** D-04; R0635
- **Nota:** La seconda frase (44x) non ha una riga propria in T5 ma va allineata a D-04; il 44x resta quello di Table 7 dopo i controlli di T3.

#### R0605 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 426); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `GPU acceleration of cell-level DE provides moderate speedups (3-7x) but is ultimately limited by the I/O cost of converting sparse matrices to dense gene chunks`
- **Valore:** limited by the I/O cost of converting sparse matrices to dense gene chunks → (da rileggere, vedi fonte)
- **Istruzione:** Riga 426: sostituire 'GPU acceleration of cell-level DE provides moderate speedups (3-7x) but is ultimately limited by the I/O cost of converting sparse matrices to dense gene chunks.' con: "Cell-level GPU tests finished 3-7 times sooner than the CPU t-test (Table 7); because the CPU Wilcoxon was not run at this scale, these ratios compare time to result rather than measure a within-method acceleration." Il meccanismo di I/O non è profilato: non si scrive.
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0605 campo recomputed; Results riga 308
- **Dipende da:** D-04
- **Assorbe:** R0215, R0656, R0714
- **Nota:** 3.38-6.77x (R0215) corretti come numeri; usati come accelerazione intra-metodo, cosa che i Risultati (riga 308) escludono.

#### R0606 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 426); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `Within cell-level tests on GPU the Wilcoxon rank-sum test actually outperformed the t-test (826 vs 1,656 s), a counterintuitive result that reflects the fact...`
- **Valore:** CuPy's `argsort` maps efficiently onto sparse data → 1,655
- **Istruzione:** Riga 426: sostituire 'Within cell-level tests on GPU the Wilcoxon rank-sum test actually outperformed the t-test (826 vs 1,656 s), a counterintuitive result that reflects the fact that CuPy's `argsort` maps efficiently onto sparse data whereas the t-test requires dense mean and variance tensors.' con: "On the GPU, our Wilcoxon rank-sum implementation, which computes rank statistics without tie correction or p-values (Methods), finished in 826 s and the t-test in 1,655 s; we did not profile the cause."
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0606 campo recomputed; righe_da_pianificare.csv id=R0216 campo recomputed; decisioni_D01_D13.txt D-04 (Wilcoxon GPU senza pareggi né p-value)
- **Dipende da:** R0216; D-04

#### R0607 · S3 · P7 (espressione differenziale) · togliere
- **Bersaglio:** prosa (riga 426); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Beyond these practical considerations, the use of pseudo-bulk becomes essential when interpreting results at scale: at 3.4 million cells, p-values from cell-...`
- **Valore:** virtually every gene reaches statistical significance → (da rileggere, vedi fonte)
- **Istruzione:** Riga 426: togliere 'Beyond these practical considerations, the use of pseudo-bulk becomes essential when interpreting results at scale: at 3.4 million cells, p-values from cell-level tests become uninformative because virtually every gene reaches statistical significance due to the enormous sample size.' (i JSON DE contengono solo tempi e il Wilcoxon GPU non produce p-value, D-04).
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0607 campo recomputed (results/de_benchmark_*.json)
- **Dipende da:** D-04
- **Assorbe:** R0217, R0552

#### R0608 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa; bib:DESeq2; bib:edgeR (riga 426); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Effect sizes (log-fold-changes) become the primary quantity of interest, and pseudo-bulk methods coupled with proper count-based models (DESeq2, edgeR) are t...`
- **Valore:** are the gold standard for multi-donor experiments [@Squair2021] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 426: sostituire 'Effect sizes (log-fold-changes) become the primary quantity of interest, and pseudo-bulk methods coupled with proper count-based models (DESeq2, edgeR) are the gold standard for multi-donor experiments [@Squair2021].' con: "For multi-donor designs, pseudo-bulk aggregation of raw counts analysed with count-based models such as DESeq2 [ref] or edgeR [ref] is recommended [@Squair2021]; our pseudo-bulk timing aggregated log-normalised values and used a Wilcoxon test, so it measures computational cost only." Aggiungere al .bib DESeq2 (Love 2014) ed edgeR (Robinson 2010): DOI da recuperare con CrossRef in S3 (non nel pacchetto). In S3 leggere in Squair2021 il passaggio sui modelli di conteggio (finora solo l'abstract).
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0608 campo recomputed; righe_da_pianificare.csv id=R0552 campo recomputed; decisioni_D01_D13.txt D-04
- **Dipende da:** D-04; R0603
- **Assorbe:** R0218
- **Nota:** UNVERIFIABLE sulla fonte, ma la frase va comunque indebolita: il benchmark usa Wilcoxon su CPM log, non modelli di conteggio.

#### R0609 · S3 · P7 (espressione differenziale) · togliere
- **Bersaglio:** prosa (riga 426); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `For contemporary single-cell studies, pseudo-bulk should therefore be the default approach on both statistical and computational grounds`
- **Valore:** should therefore be the default approach on both statistical and computational grounds → (da rileggere, vedi fonte)
- **Istruzione:** Riga 426: togliere 'For contemporary single-cell studies, pseudo-bulk should therefore be the default approach on both statistical and computational grounds.' (base statistica non testata qui; il vantaggio di tempo è già nella frase riscritta da R0603).
- **Decisione o convenzione:** D-04
- **Fonte:** righe_da_pianificare.csv id=R0609 campo recomputed
- **Dipende da:** R0603; D-04

#### R0339 · S3 · P11 (ambiente e hardware) · verificare-in-step
- **Bersaglio:** prosa (riga 432); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `This was not a design choice: the cluster's driver (535.183.01) caps the CUDA runtime at 12.2, and while the scRNA-seq pipeline ran there through forward com...`
- **Valore:** the container could not be downgraded to a driver-compatible RAPIDS release → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432, clausola 'and the container could not be downgraded to a driver-compatible RAPIDS release without breaking the spatial dependencies (Methods)'. In S3 leggere sul server (sola lettura) git log dei commit 524af6f, d65ff4d e 446fc86: risulta un container RAPIDS 24.06 / CUDA 12.2 validato sui test GPU del DGX e poi annullato. Poi sostituire la clausola con la storia documentata, per esempio: "a container with RAPIDS 24.06 and CUDA 12.2 passed GPU tests on the DGX but was not adopted for the spatial stack because [reason from the commit log]". Stessa correzione nei Metodi (T2).
- **Fonte:** righe_da_pianificare.csv id=R0339 campo recomputed; git log sul server (commit 524af6f, d65ff4d, 446fc86)
- **Dipende da:** R0623
- **Nota:** Report, sezione 4 punto 4: la frase è stata ripresa dai Metodi senza controllare la storia git.

#### R0556 · S3 · P5 (bibliografia) · aggiungere
- **Bersaglio:** prosa; bib:Harmony; bib:scVI (riga 432); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `integration methods (Harmony, scVI)`
- **Valore:** integration methods (Harmony, scVI) → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432: dopo 'integration methods (Harmony, scVI)' aggiungere le citazioni di Harmony e scVI (Korsunsky 2019; Lopez 2018); aggiungere le due voci a cibb2026_references.bib con DOI recuperati da CrossRef in S3 (non nel pacchetto). Facoltativo, dopo verifica in Dicks2026 (testo estratto, righe 150-160): "; GPU Harmony has been reported on 11.4M cells [@Dicks2026]".
- **Fonte:** righe_da_pianificare.csv id=R0556 campo recomputed; tracks/E_work/pdf_txt/2603.02402v1.txt righe 150-160 (sul server)

#### R0619 · S3 · P2 (dataset Census) · correggere
- **Bersaglio:** prosa (riga 432); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `The scRNA-seq benchmark used a single biological dataset (mouse brain E18); performance profiles may differ substantially for datasets with different sparsit...`
- **Valore:** a single biological dataset (mouse brain E18) → 3,436,470; 202
- **Istruzione:** Riga 432: sostituire 'The scRNA-seq benchmark used a single biological dataset (mouse brain E18); performance profiles may differ substantially for datasets with different sparsity patterns, gene counts, or biological characteristics.' con: "All scRNA-seq experiments used mouse brain cells from CELLxGENE Census: a random sample for the scaling benchmark and the full 3,436,470-cell selection for the stress test, replicated by concatenation beyond that size, and a 3.4M-cell subset of it (202 donors) for differential expression; performance profiles may differ for other tissues and for datasets with different sparsity patterns or gene counts."
- **Fonte:** righe_da_pianificare.csv id=R0619 campo recomputed (results/maxpower_3436470_8gpu_results.json; results/de_benchmark_pseudobulk.json n_donors)
- **Dipende da:** R0024
- **Assorbe:** R0223, R0654
- **Nota:** Allineare alla correzione del dataset nei Metodi (riga 53, T2) e alla citazione Census.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0624 · S3 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 432); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `A conservative driver policy on shared production hardware is reasonable, since driver upgrades routinely break unrelated Python environments for every other...`
- **Valore:** A conservative driver policy on shared production hardware is reasonable → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432: sostituire 'A conservative driver policy on shared production hardware is reasonable, since driver upgrades routinely break unrelated Python environments for every other user of the node, but it is itself a practical constraint on deploying GPU spatial pipelines, and one that the current software stack makes harder to work around than it should be.' con: "Driver versions on shared production hardware thus constrain which GPU software stack can be deployed."
- **Fonte:** revisione_n2_log.csv R0624 (opinione, nessun dato)
- **Dipende da:** R0339
- **Nota:** UNVERIFIABLE (opinione): si accorcia a un'osservazione senza giudizi.

#### R0625 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 432); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Scaling analysis was confined to a single DGX H100 node (1-8 GPUs); we did not benchmark multi-node configurations (e.g., 16 GPUs across two nodes interconne...`
- **Valore:** near-flat wall time observed from 2 to 8 GPUs → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432: sostituire 'because the near-flat wall time observed from 2 to 8 GPUs already indicates that the dominant bottleneck lies in CPU-side preprocessing and single-GPU graph operations (Leiden, UMAP), neither of which would benefit from additional nodes and both of which would be further penalised by inter-node communication latency' con: "since our multi-GPU configuration did not distribute any step (Results), it gives no indication of how a distributed pipeline would behave across nodes."
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0625 campo recomputed (tracks/F_work/f02_amdahl.csv)
- **Dipende da:** R0581; D-02
- **Assorbe:** R0227
- **Nota:** A 1.3M Leiden x3 + UMAP valgono 8.0 s su 435 (R0227): non sono il collo di bottiglia.

#### R0627 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 432); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Because the standard single-GPU pipeline exceeded 80 GB VRAM at 500k and 1.3M cells, those dataset sizes could only be run through the Dask-CUDA hybrid, in w...`
- **Valore:** the standard single-GPU pipeline exceeded 80 GB VRAM at 500k and 1.3M cells → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432: sostituire 'A further limitation concerns the multi-GPU configuration itself. Because the standard single-GPU pipeline exceeded 80 GB VRAM at 500k and 1.3M cells, those dataset sizes could only be run through the Dask-CUDA hybrid, in which the preprocessing steps had no distributed GPU route and therefore executed on the host CPU.' con: "A further limitation concerns the multi-GPU configuration itself: at 500k and 1.3M cells we ran only the Dask-CUDA hybrid, in which, as implemented, preprocessing ran in Scanpy on the host CPU; rapids-singlecell 0.14.1 provides Dask-based routes for [the functions verified at tag v0.14.1 in R0407] that we did not use." Non scrivere che la pipeline standard 'exceeded 80 GB VRAM' finché S3 non trova un log di fallimento sul server; stessa verifica per la didascalia di Table 4 e per Methods riga 88. L'elenco delle funzioni con ramo Dask deve essere identico a quello che R0407 verifica nel sorgente al tag v0.14.1 (registro discorde: R0405, R0045, R0627; peer_review.md ha verificato nel codice solo pca, normalize_total, log1p e neighbors).
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0627 campo recomputed; peer_review.md sezione 6 (in 0.14.1 verificati nel codice solo pca, normalize_total, log1p, neighbors)
- **Dipende da:** D-02; R0045 (assorbita in R0407); R0405 (assorbita in R0407)
- **Assorbe:** R0228
- **Nota:** Il limite è della configurazione, non dello stack.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0628 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 432); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `The 75% CPU-preprocessing fraction we report is thus a property of the software stack available at the time of benchmarking rather than an intrinsic limit of...`
- **Valore:** a property of the software stack available at the time of benchmarking → (da rileggere, vedi fonte)
- **Istruzione:** Riga 432: sostituire 'is thus a property of the software stack available at the time of benchmarking rather than an intrinsic limit of GPU acceleration, and it should be expected to shrink as distributed preprocessing implementations mature' con: "is thus a property of our configuration, which ran preprocessing in Scanpy on the CPU, rather than an intrinsic limit of GPU acceleration."
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0628 campo recomputed (tracks/F_work/f00_runs.csv)
- **Dipende da:** R0229; R0627; D-02

#### R0649 · S3 · P11 (ambiente e hardware) · aggiungere
- **Bersaglio:** prosa (riga 432); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Our study contains several limitations that should be considered when generalising these findings.`
- **Valore:** n.d. → <a> = 188.2 s (2 GPU, 32 CPU); <b> = 186.6 s (8 GPU, 200 CPU)
- **Istruzione:** Nelle Limitations della Discussione (paragrafo di riga 432) aggiungere una frase sulla baseline CPU, che nessuna voce di frase copre: "The CPU baseline was a SLURM allocation of 100 logical CPUs on a node with 224, and we did not measure how Scanpy runtimes scale with the number of threads. In the hybrid runs at 1.3M cells, Scanpy QC took <a> s with 32 allocated CPUs and <b> s with 200, which suggests that some steps are largely single-threaded; the speedups are therefore relative to this allocation, not per core." Leggere <a> e <b> (media r1-5) dai JSON indicati in source prima di scrivere. La parte sul costo di H6 e' nella voce R0588 (riga 420); l'abstract 'CPU, 100 cores' e' R0565.
- **Fonte:** results/gpu2_1300000_r{1..5}_results.json e results/gpu8_1300000_r{1..5}_results.json timings.qc_filtering, media r1-5 (188.15496 e 186.56794 s; copia nel pacchetto S2 in scrna_json/results/); CPU allocate 32 e 200: righe_da_pianificare.csv id=R0642 e id=R0448 campo recomputed (script SLURM); metadata.n_cpus = 224 e' la dimensione del nodo, non l'allocazione
- **Dipende da:** CONV;R0565;R0588
- **Nota:** Il confronto 32 contro 200 CPU e' confuso da nodo e concorrenza (H2): resta un indizio, da scrivere con 'suggests'.
- **Modificata in arbitrato:** source, value_new, anchor, line, quality (vedi `arbitrati.csv`)

#### R0632 · S3 · P8 (peso del Wilcoxon nel 120x) · riformulare
- **Bersaglio:** prosa (riga 436); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `GPU-accelerated single-cell analysis via rapids-singlecell on NVIDIA H100 GPUs reduces a 14.5-hour CPU pipeline to 7.3 minutes at 1.3M cells, with biological...`
- **Valore:** 14.5-hour | 7.3 minutes | with biologically concordant results → (da rileggere, vedi fonte)
- **Istruzione:** Riga 436: sostituire con "At 1.3M cells, rapids-singlecell on NVIDIA H100 GPUs reduced a 14.5-hour Scanpy pipeline to 7.3 minutes with 8 GPUs (8.2 minutes with 2), most of the gain coming from Wilcoxon differential expression, which accounted for 93.5% of the CPU time; CPU and GPU results agreed closely at 10,000 cells, the only size at which concordance was measured." Allineare cifre e formulazione all'abstract deciso in PI-S3.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv R0632 recomputed (52,056 s, 435.18 s, DE 93.5%, 2 GPU 8.2 min); tracks/F_work/f02_speedup_with_without_DE.csv
- **Dipende da:** CONV; PI-S3; R0558; R0588
- **Nota:** I valori sono r1-5, gia' convenzione A (S2_P3: a 1.3M le convenzioni differiscono al massimo del 6%).
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0633 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** prosa (riga 437); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `The principal scalability bottleneck is CPU-side preprocessing, not GPU VRAM: a single DGX H100 node processed 11.9M cells while using only 7.6% of total GPU...`
- **Valore:** The principal scalability bottleneck is CPU-side preprocessing, not GPU VRAM → (da rileggere, vedi fonte)
- **Istruzione:** Riga 437: sostituire con "In a stress test on replicated copies of a 3.4M-cell dataset, a single DGX H100 node processed 11.9M cells while the recorded GPU memory stayed at 7.6% of the total; the limit was set by CPU-side memory during Scanpy preprocessing."
- **Fonte:** results/maxpower_11900000_8gpu_results.json; peer_review.md H11
- **Dipende da:** R0568; R0697
- **Nota:** Allineare con la frase dello stress test replicato decisa in T3 (P6).
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0634 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 438); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `Multi-GPU scaling provides modest benefit (12% at 1.3M cells, 2 to 8 GPUs) due to the dominance of non-GPU-parallelised pipeline phases`
- **Valore:** 12% at 1.3M cells, 2 to 8 GPUs → (da rileggere, vedi fonte)
- **Istruzione:** Riga 438 (D-02): sostituire "Multi-GPU scaling provides modest benefit (12% at 1.3M cells, 2 to 8 GPUs) due to the dominance of non-GPU-parallelised pipeline phases." con "In the multi-GPU configuration we used, the expression matrix stayed on one GPU and the additional GPUs took no part in the computation, so multi-GPU scaling was not measured."
- **Decisione o convenzione:** D-02
- **Fonte:** decisioni_D01_D13.txt D-02; tracks/F_work/f02_steps_2v8_1300000.csv
- **Dipende da:** D-02
- **Assorbe:** R0233

#### R0635 · S3 · P7 (espressione differenziale) · riformulare
- **Bersaglio:** prosa (riga 439); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `For differential expression, pseudo-bulk aggregation is simultaneously the fastest (44x vs t-test) and most statistically rigorous approach`
- **Valore:** simultaneously the fastest (44x vs t-test) and most statistically rigorous approach → (da rileggere, vedi fonte)
- **Istruzione:** Riga 439 (D-04): sostituire con "For differential expression, pseudo-bulk aggregation was the fastest option, 44x faster than the cell-level CPU t-test." Togliere "most statistically rigorous approach".
- **Decisione o convenzione:** D-04
- **Fonte:** decisioni_D01_D13.txt D-04; results/de_benchmark_pseudobulk.json (43.9x)
- **Dipende da:** D-04; R0196
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0505 · S3 · P5 (bibliografia) · riformulare
- **Bersaglio:** prosa (riga 441); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `as single-cell and spatial datasets grow toward the billion-cell and billion-bin scales [@Regev2017]`
- **Valore:** billion-cell and billion-bin scales [@Regev2017] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 441: Regev 2017 non sostiene 'billion-cell' ne' 'billion-bin'. Sostituire con "These results provide practical guidance for analysing atlas-scale single-cell and spatial datasets [@Regev2017]." Prima di scrivere, S3 apre il testo completo (eLife 6:e27041, doi 10.7554/eLife.27041, open access) e conferma che parla di atlanti di cellule umane; se si vuole una scala numerica (>100M cellule) citare una fonte pertinente (per esempio Tahoe-100M, citato in Dicks2026).
- **Fonte:** cibb2026_references.bib Regev2017; tracks/E_work/web_evidence_part2.txt
- **Assorbe:** R0236, R0341, R0637
- **Nota:** R0716 propone di tagliare la frase in S6: se si taglia, questa voce decade.

#### R0237 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 450); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `The computational resources for the scRNA-seq benchmarks were provided by the`
- **Valore:** The computational resources for the scRNA-seq benchmarks were provided by the UPSCALE/CONVECS DGX H100 cluster at the University of Padova. → (da rileggere, vedi fonte)
- **Istruzione:** Ringraziamenti, righe 450-451 (non riga 154: l'ancora automatica ha preso l'occorrenza nei Metodi). La frase attribuisce al cluster solo i benchmark scRNA; con D-11 anche il riferimento CPU dello spatial gira sul nodo DGX poddgx02. Sostituire con "The computational resources for the scRNA-seq benchmarks and for the CPU reference of the spatial benchmarks were provided by the UPSCALE/CONVECS DGX H100 cluster at the University of Padova." Prima di scrivere chiedere al PI se il cluster richiede una formula di ringraziamento ufficiale e usarla al posto di questa. In S7 la frase va nell'ambiente credits di llncs (R0734).
- **Decisione o convenzione:** D-11
- **Fonte:** full_paper_LNBI.md righe 450-451; decisioni_D01_D13.txt D-11; S1.md (riferimento CPU sul DGX poddgx02)
- **Dipende da:** D-11
- **Nota:** Registro UNVERIFIABLE senza azione ('nessun numero'), ma dopo D-11 la frase e' incompleta. Ancora del pacchetto sbagliata (quality multipla): il testo e' alle righe 450-451.
- **Modificata in arbitrato:** anchor, line, quality (vedi `arbitrati.csv`)

#### R0383 · S4 · P9 (convenzione sulle ripetizioni) · riformulare
- **Bersaglio:** trasversale: didascalie Fig. 1-9, Tables 4, 8, 9 (riga 166); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `For spatial benchmarks, the first repeat served as a JIT/warmup run and was excluded; we report the mean of repeats 2-5`
- **Istruzione:** Le figure scRNA (1-6) e spatial (7-9) oggi usano convenzioni opposte senza dirlo. Con la convenzione A: in S4 la didascalia di ogni figura 1-6 e di Table 4 dice "mean of five repeats (first repeat included)"; in S5 le figure 7-9 e Tables 8-9 si rifanno da S1 con convention=1_5 e la stessa dicitura. La frase dei Metodi è in R0466 e R0453.
- **Decisione o convenzione:** CONV
- **Fonte:** S2_P3_convenzione.csv (speedup scRNA r1-5 e r2-5); s1_speedups.csv convention=1_5
- **Dipende da:** CONV; R0466; R0453
- **Nota:** Da 100k in su r1-5 e r2-5 differiscono al massimo del 6%, a 10k-50k dal 5 al 14% (S2_P3_convenzione.csv).

#### R0354 · S4 · P14 (figure) · togliere
- **Bersaglio:** fig:fig2_scaling_plot.png (riga 234); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `**Figure 3.** Total pipeline wall time vs number of GPUs (1, 2, 4, 8 H100), one line per dataset size. Error bars: SD over five repeats`
- **Valore:** Flat GPU curves demonstrate sublinear multi-GPU scaling → (da rileggere, vedi fonte)
- **Istruzione:** Togliere Figure 3 (riga 234, ../figures/fig2_scaling_plot.png) e la sua didascalia (D-02). Non rigenerare la figura; togliere la funzione o la chiamata fig_scaling_plot in scripts/generate_figures.py solo se S4 rigenera lo script (non toccare i file esistenti sul server senza step dedicato).
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0354 campo recomputed
- **Dipende da:** D-02
- **Assorbe:** R0122
- **Nota:** Primaria per R0122.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0355 · S4 · P14 (figure) · togliere
- **Bersaglio:** fig:fig6_multigpu_breakdown.png (riga 236); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `CPU preprocessing (blue) dominates wall time; the multi-GPU phase (PCA + neighbours, pink) is a small fraction, explaining flat multi-GPU scaling`
- **Valore:** CPU preprocessing (blue) dominates wall time → (da rileggere, vedi fonte)
- **Istruzione:** Togliere Figure 4 (riga 236, ../figures/fig6_multigpu_breakdown.png) e la sua didascalia (D-02). La barra CPU colorata come 'CPU preprocessing' (R0369) sparisce con la figura.
- **Decisione o convenzione:** D-02
- **Fonte:** revisione_n2_log.csv id=R0355 campo recomputed
- **Dipende da:** D-02
- **Assorbe:** R0369
- **Nota:** Primaria per R0369.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0655 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** trasversale (fuori dalla prosa); registro: UNSUPPORTED, major
- **Valore:** 3,272x → Q1_hd8_rsc0151_equal_intervals=49; hd8_rsc0141_equal_intervals=8
- **Istruzione:** I fatti della revisione (CPU 7 gruppi, GPU 3, concordanza 'shape_mismatch') sono superati da S1: CPU e GPU usano gli stessi gruppi (G5), le matrici hanno la stessa forma e la concordanza e' calcolata. S1 ha pero' trovato che a HD 8 um la co-occorrenza GPU con rapids-singlecell 0.14.1 e' sbagliata (overflow int32) e con 0.15.1 coincide con la CPU a tempo invariato. In S5, per D-13: togliere la co-occorrenza dagli speedup a Visium HD; riportare il difetto come risultato con i valori di cooc_check_eval.json (con 0.14.1 8 distanze su 49 uguali alla CPU, con 0.15.1 49 su 49 in 5 ripetizioni su 5, rapporto dei tempi 0.983 [0.951; 1.004]); Metodi riga 149 (R0343) descrive la concordanza della co-occorrenza come calcolata in S1.
- **Decisione o convenzione:** D-13
- **Fonte:** cooc_check_eval.json Q1_hd8_rsc0151_equal_intervals, hd8_rsc0141_equal_intervals, Q3_ratio, Q3_ci; S1.md anomalia 1; s1_extra_numbers.json hd8_cpu_gpu_same_groups
- **Dipende da:** D-13;R0646
- **Assorbe:** R0672
- **Modificata in arbitrato:** target (vedi `arbitrati.csv`)

#### R0658 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** trasversale (fuori dalla prosa); registro: UNSUPPORTED, minor
- **Valore:** n.d. → HD 8 um GPU: [3, 4, 3, 3, 3]; HD 2 um GPU: [538, 538, 538, 538, 538]
- **Istruzione:** Le evidenze di marzo (co-occorrenza GPU HD 8 um diversa fra r3 e r5; cluster GPU HD 2 um 534 contro 538) sono superate da S1. Nei nuovi run: Leiden GPU a HD 8 um da' [3, 4, 3, 3, 3] gruppi nelle 5 ripetizioni, a HD 2 um [538, 538, 538, 538, 538]; la co-occorrenza GPU con 0.15.1 e' identica fra ripetizioni (rsc0151_identical_across_reps = True). In S5 riportare il non determinismo di Leiden GPU a HD 8 um accanto alla concordanza (Figure 9, Table 10) e non presentare le differenze della co-occorrenza di marzo come non determinismo: con 0.14.1 il risultato era sbagliato per overflow (D-13).
- **Decisione o convenzione:** D-13
- **Fonte:** s1_extra_numbers.json own_leiden_clusters.*.server_gpu; cooc_check_eval.json rsc0151_identical_across_reps
- **Dipende da:** D-13;R0655
- **Nota:** Contesto l'interpretazione del registro: la differenza r3/r5 di marzo riguarda una matrice gia' corrotta dall'overflow int32.
- **Modificata in arbitrato:** target (vedi `arbitrati.csv`)

#### R0711 · S5 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 14); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `We extended the benchmark to spatial transcriptomics on three 10x Visium platforms`
- **Valore:** three 10x Visium platforms → (da rileggere, vedi fonte)
- **Istruzione:** Riga 14, 'We extended the benchmark to spatial transcriptomics on three 10x Visium platforms': i dataset sono due (Visium v1 e Visium HD), con Visium HD analizzato a due dimensioni di bin. In S5 verificare nell'abstract riscritto da R0731 (S3) che i dataset siano descritti come due e che lo speedup sia dato per piattaforma, non come un unico 'up to' attribuito a 'Visium HD'. Se la frase 'three 10x Visium platforms' e' ancora presente (R0731 non applicata), sostituirla con "on two 10x Visium datasets (Visium v1 and Visium HD at 8 and 2 um bins)". La riga 440 delle Conclusioni non contiene 'three platforms' ed e' riscritta per piattaforma da R0340: nessuna modifica propria. Se il PI rinomina la piattaforma HD 2 um (sottocampione di 400.000 bin, scelta in S5), usare il nome deciso.
- **Fonte:** righe_da_pianificare.csv R0711 recomputed; full_paper_LNBI.md riga 122 (Methods)
- **Dipende da:** R0254
- **Nota:** Il '10.8x' HD 2 um della nota del registro e' di marzo: superato da S1 (s1_speedups.csv).
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0343 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 149); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Finally, co-occurrence concordance was the Spearman rho between the full CPU and GPU co-occurrence matrices`
- **Valore:** co-occurrence concordance was the Spearman rho between the full CPU and GPU co-occurrence matrices → Q1 equal intervals 49/49; Q3 ratio 0.983 [0.951; 1.004]; 0.14.1 equal intervals 8/49
- **Istruzione:** Riga 149, ultima frase: a marzo la concordanza della co-occorrenza non fu mai calcolata (shape_mismatch); in S1 CPU e GPU usano gli stessi gruppi e le matrici hanno la stessa forma (cancello G5). In S5 riscrivere la frase con la metrica realmente salvata nei JSON di concordanza di SPATIAL/results_v2 (per esempio "Co-occurrence concordance was assessed as the number of distance intervals at which CPU and GPU matrices agreed within 1e-3 and as the Spearman rho between the full matrices.") e aggiungere "At Visium HD 8 um the GPU co-occurrence computed with rapids-singlecell 0.14.1 was wrong because 32-bit pair counters overflowed; with 0.15.1 it matched the CPU at 49 of 49 distance intervals at unchanged runtime." A HD 8 um la co-occorrenza esce dagli speedup (D-13); a HD 2 um non gira (oltre 500 gruppi).
- **Decisione o convenzione:** D-13
- **Fonte:** cooc_check_eval.json Q1_hd8_rsc0151_equal_intervals, Q3_ratio, Q3_ci, hd8_rsc0141_equal_intervals; SPATIAL/results_v2 JSON di concordanza (non nel pacchetto)
- **Dipende da:** D-13; R0342

#### R0689 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 326); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `### GPU speedup scales dramatically with platform resolution`
- **Valore:** GPU speedup scales dramatically with platform resolution → (da rileggere, vedi fonte)
- **Istruzione:** Riga 326, titolo di sezione "### GPU speedup scales dramatically with platform resolution": sostituire con "### End-to-end and per-step GPU speedup on three Visium platforms". Con S1 l'ordine degli speedup end-to-end (riferimento DGX) e' Visium v1 1.4x, HD 8 um 6.9x senza co-occorrenza, HD 2 um 10.4x, ma HD 8 um e HD 2 um hanno quasi lo stesso numero di bin e passi diversi (a HD 2 um co-occorrenza e arricchimento di vicinato saltati), quindi un legame causale con la risoluzione non e' sostenuto: nessun titolo deve affermarlo. La frase interpretativa spostata in Discussione si tratta nella traccia T5.
- **Decisione o convenzione:** D-01
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0]; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5
- **Dipende da:** R0360
- **Nota:** Contesto il ricalcolo del registro: 'HD 2 um 10.8x < HD 8 um 51.6x' vale per i run di marzo; con S1 HD 2 um ha lo speedup piu' alto. Resta valida la conclusione (nessun legame con la risoluzione dimostrato) per un motivo diverso.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0282 · S5 · P9 (convenzione sulle ripetizioni) · superata-da-S1
- **Bersaglio:** tabella:Table 8 didascalia (riga 330); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `: **Table 8.** Spatial transcriptomics benchmark results (RTX 4090, mean of repeats 2-5). {#tbl:spatial_summary}`
- **Valore:** RTX 4090, mean of repeats 2-5 → (da rileggere, vedi fonte)
- **Istruzione:** Riga 330, didascalia "(RTX 4090, mean of repeats 2-5)": riscrivere per il nuovo riferimento (D-01, D-11, D-12) e la convenzione A: ": **Table 8.** Spatial transcriptomics benchmark results: mean of 5 repeats, each in a fresh process. CPU reference: one DGX H100 node (poddgx02, 100 CPUs); GPU: one RTX 4090. At Visium HD 8 um, totals and speedup exclude co-occurrence (see text). {#tbl:spatial_summary}". Tutte le colonne (tempi, speedup, RAM, VRAM) con la stessa convenzione 1-5; il problema RAM r1-5 contro r2-5 sollevato dal registro scompare perche' le colonne RAM e VRAM si rileggono dai nuovi JSON (vedi R0332, R0331).
- **Decisione o convenzione:** CONV
- **Fonte:** SPATIAL/results_v2/s1_step_stats.csv col=mean_1_5,sd_1_5; SPATIAL/results_v2/s1_speedups.csv cpu=reference_dgx convention=1_5 (controllo: cpu=control_server); D-11, D-12, D-13
- **Dipende da:** CONV; D-11; D-13
- **Nota:** In S1 r1-5 e r2-5 coincidono quasi (S1.md, In breve punto 2): la scelta CONV non cambia i valori spatial ma solo la dicitura.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0290 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 343); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The CPU implementation computes pairwise cluster co-occurrence across distance intervals with O(n^2) complexity per interval, while the GPU implementation pa...`
- **Valore:** O(n^2) complexity per interval, while the GPU implementation parallelises this computation across all bins and intervals simultaneously → (da rileggere, vedi fonte)
- **Istruzione:** Riga 343: togliere il contrasto seriale contro parallelo. Sostituire con "Squidpy counts co-occurring cluster pairs with a numba-parallel loop over all pairs of bins for each distance interval (O(n^2) per interval); rapids-singlecell performs the same counting on the GPU." Se S5 non legge il kernel GPU di rapids-singlecell, non descriverne lo schema di parallelizzazione.
- **Fonte:** squidpy 1.8.1 squidpy/gr/_ppatterns.py _occur_count (@njit parallel=True, prange)
- **Dipende da:** R0362
- **Nota:** Se D-13 porta a togliere tutta la frase 342-344 dalla sezione dei tempi, questa riga va tolta insieme.

#### R0295 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** tabella:Table 9 didascalia (riga 351); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `: **Table 9.** Per-step wall time and GPU speedup for spatial-specific operations on Visium HD 8 um (393,543 bins), the platform showing the largest overall ...`
- **Valore:** spatial-specific operations | the platform showing the largest overall speedup | executed transparently → (da rileggere, vedi fonte)
- **Istruzione:** Riga 351, didascalia Table 9: sostituire con ": **Table 9.** Per-step wall time and GPU speedup on Visium HD 8 um (393,543 bins), mean of 5 repeats; CPU reference: DGX node (100 CPUs). Spatial neighbours and neighbourhood enrichment have no GPU implementation in rapids-singlecell 0.14.1: the GPU pipeline transfers the data to host memory and calls Squidpy on the CPU, so the 'GPU (s)' column for these rows is CPU time. {#tbl:spatial_steps}". Togliere "spatial-specific operations" (sei righe su undici sono passi di espressione), "executed transparently" e "the platform showing the largest overall speedup" (con S1 il massimo e' HD 2 um). Aggiungere le righe data loading e QC. Tutti i valori delle righe 355-365 (anche quelle PASS nel registro) si rileggono da s1_step_stats.csv (dgx_cpu e server_gpu, mean_1_5) e s1_speedups.csv.
- **Fonte:** benchmark_spatial_gpu.py righe 412-485; SPATIAL/results_v2/s1_step_stats.csv platform=visium_hd_square_008um; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_008um cpu=reference_dgx convention=1_5
- **Dipende da:** R0362
- **Assorbe:** R0702
- **Nota:** Valori S1 HD 8 um: data loading 1.0x, QC 0.9x, HVG 1.8x (non piu' 76x), normalisation 30.4x, PCA 37.0x, neighbours 13.5x, Leiden 12.9x.

#### R0720 · S5 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** prosa (riga 379); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `at high granularity.](../figures/fig9_spatial_concordance.png)`
- **Istruzione:** Riga 379-380: inserire una riga vuota dopo "...](../figures/fig9_spatial_concordance.png)" e prima di "Moran's I and Geary's C Spearman correlations...", cosi' che pandoc tratti l'immagine come figura con didascalia. Controllare lo stesso schema per le figure 7 e 8 e verificarlo nel rendering in S7.
- **Fonte:** full_paper_LNBI.md righe 379-380; pandoc -t html
- **Dipende da:** R0365
- **Nota:** Gia corretto nella copia di stile (tier 1), da riportare nell'originale.

#### R0694 · S5 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 399); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `between the leidenalg (CPU) and cuGraph (GPU) Leiden implementations`
- **Valore:** leidenalg (CPU) and cuGraph (GPU) Leiden implementations → (da rileggere, vedi fonte)
- **Istruzione:** Riga 399, transazione con R0329 (un solo testo per le due voci): sostituire l'intera frase "This 4.75x difference in cluster granularity arises from algorithmic differences between the leidenalg (CPU) and cuGraph (GPU) Leiden implementations, which are amplified at high resolution where the graph has many near-degenerate partitions." con "This 5.63-fold difference in cluster granularity coincides with the use of two Leiden implementations with different settings (igraph with 2 iterations on the CPU, cuGraph with its default iteration limit on the GPU); we did not test which of the two factors, or the subsampling, causes it." Il rapporto 5.63 e' 3027/538 (s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um, dgx_cpu[0] contro server_gpu[0]), lo stesso di R0329. Il backend CPU spatial e' igraph (sc.tl.leiden flavor='igraph', n_iterations=2), non leidenalg: dichiararlo anche nei Metodi spatial (S3) e alle righe 379 (didascalia di Fig. 9, R0365) e 430 (Discussione, R0615).
- **Fonte:** SPATIAL/scripts/benchmark_spatial_cpu.py righe 333-335; peer_review.md H8 (max_iter=100 di rsc)
- **Nota:** La parte Metodi va a S3 (traccia T2); la Discussione riga 430 alla traccia T5.
- **Modificata in arbitrato:** instruction, depends_on (vedi `arbitrati.csv`)

#### R0330 · S5 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 400); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Subsampling from 6.3 million to 389,492 bins also disrupts spatial contiguity, compounding the effect`
- **Valore:** Subsampling from 6.3 million to 389,492 bins also disrupts spatial contiguity, compounding the effect. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 400: togliere "Subsampling from 6.3 million to 389,492 bins also disrupts spatial contiguity, compounding the effect.": il Leiden usa il grafo kNN di espressione (50 PC), non il grafo spaziale. Se si vuole una frase sostitutiva: "The 2 um subsample retains 389,492 of 6.3 million bins; we did not test whether its sparsity contributes to the fragmented partition."
- **Fonte:** benchmark_spatial_cpu.py righe 314-337
- **Dipende da:** R0694

#### R0331 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 405); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Peak GPU VRAM was 12.9 GB on Visium v1 and plateaued at 22.6 GB for both HD platforms (Table 8), well within the RTX 4090's 24 GB capacity`
- **Valore:** 12.9 GB | 22.6 GB | well within the RTX 4090's 24 GB capacity → (da rileggere, vedi fonte)
- **Istruzione:** Righe 403 e 405: titolo "### Memory usage is modest across spatial platforms" diventa "### Memory use on spatial platforms". Riga 405 proposta: "GPU memory readings (NVML) reflect the RMM memory pool: about V0 GB was reserved before data loading in every GPU run; on both HD platforms the reading reached V1 GB (P% of the 24 GB of the RTX 4090), and HD 2 um had to be subsampled to fit." V0, V1 dai JSON GPU nuovi (memory.detailed.*_vram_before_gb e picco), P calcolato in S5. Togliere 'well within' e 'modest'.
- **Fonte:** SPATIAL/results_v2/{dgx_cpu,server_gpu,server_cpu}/spatial_*_r{1..5}_results.json campi memory (peak_ram_gb, VRAM NVML); non nel pacchetto
- **Dipende da:** R0282
- **Assorbe:** R0690
- **Nota:** Valori di marzo 12.9 e 22.6 (94.2% di 24 GB): da rileggere perche' i run S1 usano driver diverso e processi nuovi.

#### R0333 · S5 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 407); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `These modest requirements suggest that spatial benchmarks at full Visium HD resolution (6.3M bins at 2 um) would fit comfortably within DGX H100 memory`
- **Valore:** would fit comfortably within DGX H100 memory → (da rileggere, vedi fonte)
- **Istruzione:** Riga 407: togliere "These modest requirements suggest that spatial benchmarks at full Visium HD resolution (6.3M bins at 2 um) would fit comfortably within DGX H100 memory." Eventuale sostituto: "Whether the full-resolution Visium HD 2 um dataset (6.3 million bins) fits in GPU memory was not tested; the CPU pipeline densifies the HVG matrix, which at this size would need about 50 GB in float32."
- **Fonte:** benchmark_spatial_cpu.py righe 307-311; registro R0333 recomputed (50.4 GB float32)
- **Dipende da:** R0331
- **Nota:** In tensione con Metodi riga 122 ('DGX-class resources'), traccia T2.

#### R0555 · S5 · P13 (affermazioni oltre i dati) · togliere
- **Bersaglio:** prosa (riga 428); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `is, to our knowledge, the largest GPU speedup reported for any spatial transcriptomics operation`
- **Valore:** the largest GPU speedup reported for any spatial transcriptomics operation → (da rileggere, vedi fonte)
- **Istruzione:** Riga 428: togliere 'to our knowledge, the largest GPU speedup reported for any spatial transcriptomics operation' e la spiegazione O(n^2) non citata; con R0611 la frase cade comunque. Non reintrodurre superlativi sulla co-occorrenza (il valore ricalcolato in pipeline è 40.4x ed è escluso dagli speedup a HD).
- **Fonte:** righe_da_pianificare.csv id=R0555 campo recomputed; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_008um step=co_occurrence cpu=reference_dgx convention=1_5 (solo per non citarlo: escluso dagli speedup a Visium HD, D-13)
- **Dipende da:** R0611
- **Assorbe:** R0695
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0610 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 428); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Beyond scRNA-seq, the extension to spatial transcriptomics demonstrates that GPU acceleration becomes increasingly impactful for computationally intensive sp...`
- **Valore:** becomes increasingly impactful for computationally intensive spatial statistics → (da rileggere, vedi fonte)
- **Istruzione:** Riga 428: sostituire 'Beyond scRNA-seq, the extension to spatial transcriptomics demonstrates that GPU acceleration becomes increasingly impactful for computationally intensive spatial statistics.' con: "In the spatial benchmark, the GPU advantage was concentrated in a few steps rather than spread across spatial statistics as a whole."
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv cpu=reference_dgx convention=1_5, step per piattaforma
- **Dipende da:** R0572; D-13
- **Nota:** La frase dipendeva dalla co-occorrenza, ora esclusa a HD (D-13).

#### R0613 · S5 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 428); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `The remaining CPU-only operations (spatial neighbours computation via Delaunay triangulation, neighbourhood enrichment, and ligand-receptor analysis) represe...`
- **Valore:** represent clear opportunities for future GPU-native implementations → 0.8; 1.1; 0.96
- **Istruzione:** Riga 428: sostituire 'The remaining CPU-only operations (spatial neighbours computation via Delaunay triangulation, neighbourhood enrichment, and ligand-receptor analysis) represent clear opportunities for future GPU-native implementations and likely harbour substantial additional speedup potential.' con: "In rapids-singlecell 0.14.1, spatial neighbour computation, neighbourhood enrichment and ligand-receptor analysis ran on the CPU inside the GPU pipeline (0.8x and 1.1x at Visium HD 8 um; ligand-receptor, run on Visium v1 only, 0.96x); later releases list GPU implementations for some of these functions [ref]." Prima di scrivere 'later releases', S5 verifica nelle note di rilascio di rapids-singlecell in quale versione sono comparsi spatial_neighbors, nhood_enrichment e ligrec su GPU; se erano già in 0.14.x scrivere invece "were not used in our pipeline".
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv step=spatial_neighbors e nhood_enrichment platform=visium_hd_square_008um, step=ligrec platform=visium, cpu=reference_dgx, convention=1_5; note di rilascio rapids-singlecell (non nel pacchetto)
- **Dipende da:** R0366; R0295
- **Nota:** Il registro si basa sulla documentazione 'stable', non sulla 0.14.1.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0713 · S5 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 428); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `meaning that scientists can obtain identical rankings of spatially variable genes in seconds rather than minutes`
- **Valore:** identical rankings of spatially variable genes in seconds rather than minutes → 0.7-4.0; 82-86
- **Istruzione:** Riga 428: sostituire 'with near-perfect numerical concordance (rho >= 0.9995), meaning that scientists can obtain identical rankings of spatially variable genes in seconds rather than minutes' con: "with near-perfect numerical concordance (Spearman rho >= [minimum from S1 concordance]); the top-50 spatially variable genes [formed the same set | overlapped with Jaccard J] on CPU and GPU, and each statistic took 0.7-4.0 s on the GPU instead of 82-86 s on the CPU reference". Il rho minimo e le Jaccard (top-50, FDR) si rileggono nei JSON di concordanza di S1 (riferimento DGX contro GPU) prima di scrivere; un insieme uguale non è un ranking identico. La forma fra parentesi quadre si sceglie dopo la lettura della Jaccard top-50 nel JSON di concordanza DGX contro GPU.
- **Fonte:** SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu e server_gpu, step=spatial_autocorr_moran/geary, platform=visium_hd_*, mean_1_5; rho e Jaccard: SPATIAL/results_v2 concordanza DGX contro GPU (non nel pacchetto)
- **Dipende da:** R0612
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0616 · S5 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 430); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `At 389,492 spatial bins with resolution parameter 0.1, local optima abound, and the leidenalg (CPU) and cuGraph (GPU) implementations explore this landscape ...`
- **Valore:** local optima abound → (da rileggere, vedi fonte)
- **Istruzione:** Riga 430: sostituire 'At 389,492 spatial bins with resolution parameter 0.1, local optima abound, and the leidenalg (CPU) and cuGraph (GPU) implementations explore this landscape through different vertex orderings and local heuristics.' con: "At 389,492 spatial bins and resolution 0.1, the igraph (CPU) and cuGraph (GPU) implementations returned very different partitions." In S5 confermare 389,492 nei JSON di S1 (n_spots_after_qc).
- **Fonte:** righe_da_pianificare.csv id=R0616 campo recomputed; SPATIAL/results_v2/{dgx_cpu,server_gpu,server_cpu}/spatial_*_visium_hd_square_002um_r*_results.json campo n_spots_after_qc
- **Dipende da:** R0337; R0615
- **Nota:** Numeri ok, meccanismo (paesaggio di ottimi locali) non misurato.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0617 · S5 · P13 (affermazioni oltre i dati) · riformulare
- **Bersaglio:** prosa (riga 430); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `This observation suggests that users working at ultra-high spatial resolution should not rely on a single run of any Leiden implementation, but instead emplo...`
- **Valore:** employ consensus clustering approaches → (da rileggere, vedi fonte)
- **Istruzione:** Riga 430: sostituire 'This observation suggests that users working at ultra-high spatial resolution should not rely on a single run of any Leiden implementation, but instead employ consensus clustering approaches or spatial-aware alternative methods that explicitly account for tissue geometry.' con: "Users working at this resolution should therefore check how stable Leiden partitions are across implementations and settings before interpreting them."
- **Fonte:** righe_da_pianificare.csv id=R0617 campo recomputed
- **Dipende da:** R0615
- **Nota:** Il consensus clustering non è testato e Duo2020 (abstract) non lo trova migliore del miglior metodo singolo.

#### R0717 · S6 · PM (arrotondamenti e minori) · riformulare
- **Bersaglio:** prosa (riga 12); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `^3^ Neuromuscular Unit, Department of Neuroscience, University of Padua, Padua, Italy`
- **Valore:** University of Padua, Padua → University of Padova, Padova
- **Istruzione:** Uniformare il nome dell'ateneo: 'University of Padova' alle righe 8, 154 e 451, 'University of Padua' (e la citta' 'Padua') alle righe 12 e 455. Proposta: alle righe 12 e 455 sostituire 'University of Padua, Padua' / 'University of Padua' con la forma gia' prevalente "University of Padova, Padova" / "University of Padova", salvo diversa preferenza degli autori; applicare la stessa forma nel LaTeX (S7).
- **Fonte:** full_paper_LNBI.md riga 8 (forma prevalente, anche righe 154 e 451)
- **Nota:** Scelta stilistica degli autori (G44).

#### R0722 · S6 · PS (stile) · riformulare
- **Bersaglio:** prosa (riga 14); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `These results identify CPU-side preprocessing as the primary bottleneck and provide practical guidance for deploying GPU-accelerated workflows at atlas scale`
- **Valore:** provide practical guidance for deploying GPU-accelerated workflows at atlas scale → (da rileggere, vedi fonte)
- **Istruzione:** Abstract (riga 14) e Conclusioni (righe 436-441) ripetono gli stessi cinque risultati e la formula 'practical guidance'; il 120x/14.5 h/7.3 min compare alle righe 14, 183, 420, 436. Dopo il nuovo abstract (R0731) accorciare le Conclusioni a ruolo di sintesi interpretativa, senza ripetere le cifre dell'abstract, e lasciare il 120x una sola volta nei Risultati piu' l'abstract.
- **Fonte:** righe_da_pianificare.csv R0722 recomputed; full_paper_LNBI.md righe 436-441
- **Dipende da:** R0731
- **Nota:** Candidato al taglio verso ~15 pagine (D-03).

#### R0724 · S6 · PS (stile) · riformulare
- **Bersaglio:** trasversale: righe 111, 262, 283, 304, 432 (riga 111); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `the reported peak is the maximum over these post-step samples`
- **Istruzione:** Accorciamento: la spiegazione del campionamento della RAM (solo fra step, solo processo padre, limite inferiore) resta nei Metodi riga 111 e, in una frase, nella didascalia di Table 6; nei Risultati (righe 262, 304) e nelle Limitazioni (riga 432) sostituirla con un rimando ai Metodi. Applicare dopo R0461.
- **Decisione o convenzione:** D-03
- **Fonte:** full_paper_LNBI.md righe 111, 262, 283, 304, 432
- **Dipende da:** R0461

#### R0725 · S6 · PS (stile) · riformulare
- **Bersaglio:** trasversale: righe 161-163 e 432 (riga 162); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `We attempted to downgrade the spatial container to an earlier RAPIDS release known to be driver-compatible (RAPIDS 25.02)`
- **Istruzione:** Accorciamento: la vicenda driver e container del DGX è raccontata nei Metodi (righe 161-163) e di nuovo nelle Limitazioni (riga 432). Dopo R0451 e R0279 tenerla in un solo punto (Metodi) e lasciare nelle Limitazioni al massimo una frase di rimando.
- **Decisione o convenzione:** D-03
- **Fonte:** full_paper_LNBI.md righe 161-163, 432
- **Dipende da:** R0451; R0279

#### R0723 · S6 · PS (stile) · riformulare
- **Bersaglio:** prosa (riga 258); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `This variant moves scaling to CPU (exploiting the 2 TB system RAM), distributes PCA across all 8 GPUs via a covariance-matrix method`
- **Valore:** distributes PCA across all 8 GPUs via a covariance-matrix method → (da rileggere, vedi fonte)
- **Istruzione:** Accorciare il secondo periodo di riga 258 ("This variant moves scaling to CPU (exploiting the 2 TB system RAM), distributes PCA across all 8 GPUs via a covariance-matrix method, and replaces the full data matrix on GPU with an empty sparse placeholder ..."), che ripete i Metodi (riga 110): lasciare solo il rimando "(Methods, Section \"Stress test: maximum capacity\")".
- **Decisione o convenzione:** D-03
- **Fonte:** revisione_n2_log.csv id=R0723 campo recomputed
- **Dipende da:** D-03
- **Nota:** Taglio di stile per le ~15 pagine; dopo le correzioni di sostanza di S3.

#### R0727 · S6 · PS (stile) · riformulare
- **Bersaglio:** prosa (riga 260); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `A separate test at 13.7 million cells failed earlier, during the CPU-side sparse-to-dense scaling step`
- **Valore:** failed earlier, during the CPU-side sparse-to-dense scaling step → (da rileggere, vedi fonte)
- **Istruzione:** Il fallimento a 13.7M nello scaling e' ripetuto a righe 260, 262, 264 e 281: tenerlo una sola volta (riga 260, nella forma decisa da R0143) e togliere le ripetizioni a righe 262 (R0152) e 281 (R0166).
- **Decisione o convenzione:** D-03
- **Fonte:** revisione_n2_log.csv id=R0727 campo recomputed
- **Dipende da:** R0143; D-03

#### R0728 · S6 · PS (stile) · togliere
- **Bersaglio:** prosa; trasversale (riga 414); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `These results reveal several important insights about GPU-accelerated single-cell analysis that merit detailed discussion`
- **Valore:** These results reveal several important insights about GPU-accelerated single-cell analysis that merit detailed discussion → (da rileggere, vedi fonte)
- **Istruzione:** Riga 414: togliere la frase di rimando 'These results reveal several important insights about GPU-accelerated single-cell analysis that merit detailed discussion.'. In S6, dopo le correzioni di sostanza, togliere dalla Discussione le aperture enfatiche ancora presenti ('Perhaps most importantly', 'Critically', 'Related to this', 'A notable finding', 'This is a non-obvious but important takeaway') e le parole segnalate dal registro (landscape, dramatically, impressive, fundamental, actually), senza toccare numeri e citazioni; spezzare le frasi oltre circa 30 parole. La dichiarazione sull'uso di LLM nei Methods non si decide qui: è una scelta del PI (pi_choices).
- **Fonte:** revisione_n2_log.csv riga R0728; stile/full_paper_LNBI_style.md sul server (copia di stile)
- **Nota:** Proprietà del testo, non inferenza sull'origine. Molte aperture cadono già con le voci di sostanza (R0581, R0585, R0595, R0598, R0615).

#### R0716 · S6 · PS (stile) · togliere
- **Bersaglio:** prosa (riga 441); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `These results provide practical guidance for the computational bioinformatics community as single-cell and spatial datasets grow toward the billion-cell and ...`
- **Valore:** These results provide practical guidance for the computational bioinformatics community as single-cell and spatial datasets grow toward the billion-cell and billion-bin scales [@Regev2017]. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 441: frase di chiusura generica che ripete la chiusura dell'abstract. In S6 (taglio a circa 15 pagine, D-03) toglierla nella forma lasciata da R0505 in S3: "These results provide practical guidance for analysing atlas-scale single-cell and spatial datasets [@Regev2017]." Regev2017 resta citato alle righe 22 e 23: la voce del .bib non si tocca.
- **Fonte:** full_paper_LNBI.md righe 14, 441
- **Dipende da:** R0505; D-03
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0734 · S7 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** latex:lncs_latex/ (fuori dalla prosa); registro: MISMATCH, major
- **Valore:** The authors declare no conflict of interest. → (da rileggere, vedi fonte)
- **Istruzione:** In S7, dopo S3-S6, rigenerare lncs_latex/full_paper_LNBI.tex dal .md finale: il .tex attuale e' del 6 luglio e non contiene le modifiche del 2 settembre ne' quelle del piano; non correggere a mano il .tex vecchio. Con llncs 2.26 e splncs04 mettere Acknowledgements e dichiarazione sugli interessi nell'ambiente credits (\begin{credits} \subsubsection{\ackname} ... \subsubsection{\discintname} ... \end{credits}). La sezione 'Conflict of Interest' (righe 444-446) diventa la Disclosure of Interests, per esempio "The authors have no competing interests to declare that are relevant to the content of this article."; confermare formula e comandi sul template in lncs_latex/. Funding (riga 455, CUP secondo D-05) entra nei ringraziamenti o resta sezione secondo il template. Compilare in locale e registrare: pagine (R0733), riferimenti non definiti, figure con i nomi di R0735. Nulla sul server.
- **Fonte:** manuscript/lncs_latex/ (llncs.cls 2.26 e splncs04.bst, da verificare con ls in sola lettura all'apertura di S7); script di conversione md -> tex da versionare in tools/ prima di S7, con le sostituzioni di R0729 e un controllo che rilegge numeri e citazioni del .tex contro il .md; revisione_n2_log.csv R0734
- **Dipende da:** R0237;R0735;D-05
- **Nota:** La dichiarazione inserita in METEOR sostituisce quella nel testo (report, sezione 1): tenerle uguali.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0735 · S7 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** fig:figures/ (fuori dalla prosa); registro: MISMATCH, minor
- **Valore:** Figure 1 = fig1_speedup_heatmap.png; Figure 2 = fig5_timing_breakdown.png; Figure 3 = fig2_scaling_plot.png; Figure 4 = fig6_multigpu_breakdown.png; Figure 5 = fig3_concordance.png; Figure 6 = fig4_memory_profile.png; Figure 7 = fig7_spatial_speedup.png; Figure 8 = fig8_spatial_perstep.png; Figure 9 = fig9_spatial_concordance.png → (da rileggere, vedi fonte)
- **Istruzione:** Dopo S4 (figure 1-6 rigenerate, Figure 3 e 4 tolte per D-02) e S5 (figure 7-9 dai nuovi JSON), rinominare i file figura come figNN_<nome>.pdf (vettoriale, R0378; PNG solo come anteprima) con NN = numero della didascalia finale; aggiornare i percorsi nelle righe ![ del .md e gli \includegraphics del .tex; aggiornare i rimandi 'Fig. n' nel testo, compreso quello inserito da R0360, R0361, R0362, R0363, R0366 e R0658 (le figure spatial 7-9 diventano 5-7 dopo la rimozione di Fig. 3 e 4, salvo altri tagli in S6). Controllare da codice che numero nel nome, didascalia e rimandi coincidano. Questa voce assorbe R0380 (stesso problema, Figure 2).
- **Decisione o convenzione:** D-02
- **Fonte:** Guida METEOR e istruzioni LNBI/CIBB 2026 da scaricare e salvare nel repo prima di S7 (docs/ o manuscript/meteor/), con la checklist dei file da caricare (sorgente LaTeX e .bib, figure, PDF compilato, modulo di licenza) e le regole sui nomi; R0735 e R0734 le citano come fonte; full_paper_LNBI.md righe ![ (219-379)
- **Dipende da:** D-02
- **Assorbe:** R0380
- **Modificata in arbitrato:** instruction, source (vedi `arbitrati.csv`)

#### R0002 · S7 · PL (LaTeX e METEOR) · verificare-in-step
- **Bersaglio:** latex:lncs_latex/ (riga 3); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `bibliography: bibliography/cibb2026_references.bib`
- **Valore:** bibliography: bibliography/cibb2026_references.bib → (da rileggere, vedi fonte)
- **Istruzione:** Riga 3 (front matter), riga del registro UNVERIFIABLE senza quantita'. In S7 verificare che il sorgente LaTeX LNCS (lncs_latex/) usi la stessa bibliografia corretta in S3 (Palla2022, Marconato2024, eventuali nuove voci come la documentazione 10x di R0544) e che ogni chiave citata nel .md compili con splncs04; nessuna modifica alla riga 3 del .md.
- **Fonte:** full_paper_LNBI.md riga 3; lncs_latex/full_paper_LNBI.tex (da rigenerare in S7); short paper camera-ready
- **Assorbe:** R0560

#### R0003 · S7 · PL (LaTeX e METEOR) · verificare-in-step
- **Bersaglio:** latex:lncs_latex/ (riga 6); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `Luca Vedovelli^1,2^, Corrado Lanera^1,2^, Daniele Sabbatini^1,2,3^, and Dario Gregori^1,2^`
- **Valore:** Luca Vedovelli^1,2^, Corrado Lanera^1,2^, Daniele Sabbatini^1,2,3^, and Dario Gregori^1,2^ → (da rileggere, vedi fonte)
- **Istruzione:** Riga 6 (front matter), riga del registro UNVERIFIABLE senza quantita'. In S7 verificare che lista e ordine degli autori coincidano con lo short paper e con METEOR (regola CIBB: stessa lista autori; report sezione 1: rispettato) e che nel LaTeX i marcatori ^1,2^ diventino \inst{1,2}; nessuna modifica al testo.
- **Fonte:** full_paper_LNBI.md riga 6; lncs_latex/full_paper_LNBI.tex (da rigenerare in S7); short paper camera-ready
- **Assorbe:** R0561

#### R0004 · S7 · PL (LaTeX e METEOR) · verificare-in-step
- **Bersaglio:** latex:lncs_latex/ (riga 8); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `^1^ Unit of Biostatistics, Epidemiology and Public Health, Department of Cardiac, Thoracic, Vascular Sciences and Public Health, University of Padova, Padova...`
- **Valore:** ^1^ Unit of Biostatistics, Epidemiology and Public Health → (da rileggere, vedi fonte)
- **Istruzione:** Riga 8 (front matter), riga del registro UNVERIFIABLE senza quantita'. In S7 verificare nel LaTeX l'affiliazione 1 in \institute e il blocco email in \email{} (nel .md e' codice inline; '@ubep' non e' una citazione, R0470 PASS). Il nome dell'ateneo si uniforma in R0717.
- **Fonte:** full_paper_LNBI.md riga 8; lncs_latex/full_paper_LNBI.tex (da rigenerare in S7); short paper camera-ready
- **Assorbe:** R0562

#### R0005 · S7 · PL (LaTeX e METEOR) · verificare-in-step
- **Bersaglio:** latex:lncs_latex/ (riga 10); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `^2^ BIOSTAT-X, Biostatistics & AI for Biomedical Discovery, Pediatric Research Institute "Città della Speranza", Padova, Italy`
- **Valore:** ^2^ BIOSTAT-X, Biostatistics & AI for Biomedical Discovery → (da rileggere, vedi fonte)
- **Istruzione:** Riga 10 (front matter), riga del registro UNVERIFIABLE senza quantita'. In S7 verificare nel LaTeX l'affiliazione 2 (resa di '&' come \& e di 'Citta'' con accento) contro lo short paper; nessuna modifica al testo.
- **Fonte:** full_paper_LNBI.md riga 10; lncs_latex/full_paper_LNBI.tex (da rigenerare in S7); short paper camera-ready
- **Assorbe:** R0563

#### R0006 · S7 · PL (LaTeX e METEOR) · verificare-in-step
- **Bersaglio:** latex:lncs_latex/ (riga 12); registro: UNVERIFIABLE, info
- **Ancora (univoca nel .md):** `^3^ Neuromuscular Unit, Department of Neuroscience, University of Padua, Padua, Italy`
- **Valore:** ^3^ Neuromuscular Unit, Department of Neuroscience → (da rileggere, vedi fonte)
- **Istruzione:** Riga 12 (front matter), riga del registro UNVERIFIABLE senza quantita'. In S7 verificare nel LaTeX l'affiliazione 3 contro lo short paper e METEOR; la forma 'Padua' si tratta in R0717.
- **Fonte:** full_paper_LNBI.md riga 12; lncs_latex/full_paper_LNBI.tex (da rigenerare in S7); short paper camera-ready
- **Assorbe:** R0564

#### R0729 · S7 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** latex:lncs_latex/ (riga 14); registro: MISMATCH, info
- **Ancora (univoca nel .md):** `achieving up to 51.6x end-to-end speedup (Visium HD 8 um)`
- **Valore:** Visium HD 8 um → (da rileggere, vedi fonte)
- **Istruzione:** Il .md usa trascrizioni ASCII ('um', 'rho', '+/-', '>=', 'x'); nel sorgente LaTeX rigenerato (S7) convertirle in $\mu$m, $\rho$, $\pm$, $\geq$, $\times$ in tutto il capitolo, compresi abstract (es. '51.6x', 'Visium HD 8 um', 'rho >= 0.9995' o i valori che li sostituiscono) e tabelle; il .md resta ASCII. Controllare da codice che nel .tex non restino ' um' o 'rho' fuori dai comandi.
- **Fonte:** full_paper_LNBI.md; full_paper_LNBI_stale.tex (conversione gia' usata)
- **Nota:** Trasversale (G56).

#### R0721 · S7 · PL (LaTeX e METEOR) · correggere
- **Bersaglio:** trasversale: Table 1 riga 71, Table 4 righe 191-210, Table 5 righe 278-279 (riga 71); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `| 1 | Data loading | --- |`
- **Valore:** --- → (da rileggere, vedi fonte)
- **Istruzione:** Sostituire le celle '---' (12 celle) con 'none' o 'n.a.' come nella copia di stile: con la tipografia smart di pandoc '---' diventa una lineetta lunga. Farlo nel .md prima di rigenerare il LaTeX.
- **Fonte:** righe_da_pianificare.csv id=R0721 campo recomputed; stile/full_paper_LNBI_style.md


## L3 · tabella da aggregati (25 voci)

#### R0375 · S4 · P14 (figure) · correggere
- **Bersaglio:** fig:fig1_speedup_heatmap.png (riga 219); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy (100 cores) at 10k, 50k, and 100k cells`
- **Istruzione:** Rigenerare Fig. 1 (scripts/generate_figures.py fig_speedup_heatmap, righe 178-205): scala colore logaritmica centrata su 1 (LogNorm o TwoSlopeNorm su log10) con tick espliciti 0.5, 1, 10, 100 e valori annotati nelle celle; estremi distinguibili in scala di grigi. In didascalia aggiungere: "The PCA row includes scaling (`sc.pp.scale`), which is timed together with PCA; values include the first repeat." Nella stessa didascalia sostituire "relative to CPU Scanpy (100 cores)" con "relative to CPU Scanpy (100 logical CPUs)", come R0565 e R0704.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0375 campo recomputed; scripts/generate_figures.py fig_speedup_heatmap
- **Dipende da:** CONV; R0377; R0379
- **Nota:** La riga PCA include sc.pp.scale (benchmark_cpu.py riga 215, benchmark_gpu.py riga 288); Table 1 elenca Scaling come step separato: coordinare con T2.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0377 · S4 · P14 (figure) · correggere
- **Bersaglio:** trasversale (riga 219); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy (100 cores) at 10k, 50k, and 100k cells`
- **Istruzione:** Ridisegnare tutte le figure per la larghezza finale LNCS di 12,2 cm (figsize circa 4,8 in) con corpo minimo 7 pt (Springer: non sotto 6 pt). S4 lo fa per le figure 1-6 da scripts/generate_figures.py (togliendo il pannello legenda vuoto di Fig. 2); le figure 7-9 si rifanno in S5 dai nuovi JSON spatial. Fig. 3 e Fig. 4 si tolgono per D-02 (R0354, R0355) e non vanno ridisegnate.
- **Fonte:** revisione_n2_log.csv id=R0377 campo recomputed (c10_text_height.py, llncs.cls riga 55)
- **Dipende da:** D-02
- **Nota:** Voce trasversale: S5 riceve la parte fig7-9.

#### R0378 · S4 · P14 (figure) · correggere
- **Bersaglio:** trasversale (riga 219); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy (100 cores) at 10k, 50k, and 100k cells`
- **Istruzione:** Esportare le figure 1-6 in PDF vettoriale (savefig .pdf) invece che PNG a 300 dpi; se serve un raster, almeno 800 dpi a 12,2 cm (Springer Proceedings CS, line art). Aggiornare gli \includegraphics in S7. Le figure 7-9 si esportano allo stesso modo in S5.
- **Fonte:** revisione_n2_log.csv id=R0378 campo recomputed (c11_lncs_print.py)
- **Dipende da:** R0377

#### R0379 · S4 · P14 (figure) · correggere
- **Bersaglio:** trasversale (riga 219); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy (100 cores) at 10k, 50k, and 100k cells`
- **Istruzione:** Rendere leggibili in scala di grigi le figure 1, 2, 5 e 6 (numerazione attuale): marker e tratteggi diversi per serie, etichette dirette, palette con luminanza separata (non Set3 pastello in Fig. 2; in Fig. 6 2x e 8x GPU con marker diversi; in Fig. 5 PCA e kNN distinguibili). Verificare con una conversione in grigio. Le figure 8-9 in S5.
- **Fonte:** revisione_n2_log.csv id=R0379 campo recomputed (c11_lncs_print.py, montage_rest.png)
- **Dipende da:** R0377

#### R0351 · S4 · P14 (figure) · correggere
- **Bersaglio:** prosa (riga 221); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `On CPU, DE testing and neighbour graph construction dominate; on GPU, all steps complete in seconds`
- **Valore:** DE testing and neighbour graph construction dominate → UMAP
- **Istruzione:** Didascalia di Figure 2 (riga 221): sostituire "On CPU, DE testing and neighbour graph construction dominate; on GPU, all steps complete in seconds." con "On CPU, DE testing and UMAP dominate; on GPU, the longest step, DE testing at 100k cells, takes 6.4 s on average." Nella figura (fig5_timing_breakdown.png) rendere visibili le barre GPU: pannello GPU separato o asse logaritmico.
- **Decisione o convenzione:** CONV
- **Fonte:** revisione_n2_log.csv id=R0351 campo recomputed (results/cpu_{10000,50000,100000}_r*.json timings; c02_fig2_timing_breakdown.py; step GPU piu lungo 6.4 s)
- **Dipende da:** CONV; R0377
- **Assorbe:** R0113
- **Nota:** Quote CPU (100k): DE 86.9%, UMAP 7.5%, neighbours 1.4%. R0113 assorbita.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0376 · S4 · P14 (figure) · correggere
- **Bersaglio:** fig:fig3_concordance.png (riga 246); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `**Figure 5.** Concordance between CPU and GPU pipelines on 10,000 cells`
- **Valore:** All metrics indicate near-identical biological outputs → (da rileggere, vedi fonte)
- **Istruzione:** Rigenerare Figure 5 (fig3_concordance.png, scripts/generate_figures.py fig_concordance): dot plot su asse comune (per esempio 0.8-1.0) invece di barre con base 0.85, stessa scala nei due pannelli, etichetta y nel pannello destro, legenda fuori dai dati, aggiungere la sesta metrica DE logFC rho (0.946). Annotare il tetto 0.9375 della kNN Jaccard. Didascalia: togliere "All metrics indicate near-identical biological outputs" e scrivere "kNN Jaccard is bounded at 0.9375 by construction (see text)."
- **Fonte:** revisione_n2_log.csv id=R0376 campo recomputed (c03b_legend_overlap.py, c11_lncs_print.py)
- **Dipende da:** R0371; R0377; R0379

#### R0359 · S4 · P14 (figure) · correggere
- **Bersaglio:** prosa (riga 254); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Left: CPU RAM; right: GPU VRAM (per-device maximum). Dashed red line: H100 80 GB VRAM limit. CPU RAM grows super-linearly`
- **Valore:** GPU VRAM (per-device maximum) → (da rileggere, vedi fonte)
- **Istruzione:** Didascalia di Figure 6 (riga 254): sostituire "right: GPU VRAM (per-device maximum). Dashed red line: H100 80 GB VRAM limit. CPU RAM grows super-linearly;" con "right: aggregate GPU VRAM summed over the allocated devices (for 2, 4 and 8 GPUs dominated by the RMM pools pre-allocated by each Dask worker). CPU RAM grows roughly linearly;". Nella figura (fig4_memory_profile.png) togliere la linea 80 GB dal pannello destro (il dato per device non e' salvato nei JSON) e correggere il tick '1000k' dell'asse x in '1.3M'.
- **Fonte:** revisione_n2_log.csv id=R0359 campo recomputed (scripts/benchmark_multigpu.py righe 60-73, 432-433; c05_fig6_memory.py)
- **Dipende da:** R0377; R0379
- **Assorbe:** R0139
- **Nota:** Primaria per R0139.

#### R0373 · S4 · P14 (figure) · correggere
- **Bersaglio:** fig:fig4_memory_profile.png (riga 254); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `**Figure 6.** Peak memory usage across dataset sizes`
- **Istruzione:** In Figure 6 aggiungere barre (min-max o SD sulle 5 ripetizioni) ai punti di VRAM e RAM, e separare le linee 2x e 4x GPU del pannello sinistro (coincidono a 60.7 GB a 1.3M). In didascalia aggiungere: "All repeats of a configuration ran in one process; in the multi-GPU runs VRAM grew from the first to later repeats."
- **Fonte:** revisione_n2_log.csv id=R0373 campo recomputed (results/gpu{2,4,8}_{N}_r*.json memory.peak_vram_gb; slurm/gpu_8.sh)
- **Dipende da:** R0359; R0377
- **Nota:** peak_vram_gb 8 GPU a 1.3M: r1 93.71 GB, r2-r5 135.31-150.92 GB; il 134.2 del testo e' la media.
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0254 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 14); registro: UNSUPPORTED, critical
- **Ancora (univoca nel .md):** `We extended the benchmark to spatial transcriptomics on three 10x Visium platforms, achieving up to 51.6x end-to-end speedup (Visium HD 8 um) and 3,272x for ...`
- **Valore:** achieving up to 51.6x end-to-end speedup (Visium HD 8 um) and 3,272x for co-occurrence analysis, with near-perfect spatial autocorrelation concordance (Spearman rho >= 0.9995) → 1.4x (visium total); 6.9x (HD 8 um total senza co-occorrenza); 10.4x (HD 2 um total); co-occorrenza 0.14.1 errata su 41/49 distanze, 0.15.1 49/49
- **Istruzione:** Riga 14, frase spatial dell'abstract. In S3 l'abstract e' riscritto per intero da R0731, che contiene gia' le cifre spatial di S1: in S5 non sostituire testo, ma verificare sull'abstract approvato che (a) le cifre coincidano con s1_speedups.csv (platform=visium e visium_hd_square_002um, step=total, cpu=reference_dgx, convention=1_5) e con s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0], cioe' 1.4x, 6.9x senza co-occorrenza e 10.4x; (b) non compaiano 51.6x ne' 3,272x; (c) il difetto della co-occorrenza a Visium HD 8 um sia riportato come risultato (D-13: 0.14.1 diversa dalla CPU a 41 distanze su 49, 0.15.1 uguale a 49 su 49 a tempo invariato, cooc_check_eval.json). Correggere solo le cifre discordanti. Se l'abstract scelto dal PI non contiene la frase spatial, inserire "Against this DGX CPU reference, an RTX 4090 accelerated end-to-end analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occorrence) and 10.4-fold on Visium HD 2 um. At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances because of 32-bit integer overflow; version 0.15.1 matched the CPU at all 49 distances in the same time." Il valore 'Spearman rho >= 0.9995' e' di marzo: si scrive solo se S5 lo rilegge dai JSON di concordanza di S1 (riferimento DGX contro GPU).
- **Decisione o convenzione:** D-13
- **Fonte:** s1_speedups.csv platform=visium e visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0]; s1_extra_numbers.json hd8_cpu_gpu_same_groups.n_unequal; cooc_check_eval.json Q1_hd8_rsc0151_equal_intervals; rho da SPATIAL/results_v2 JSON di concordanza (server, non nel pacchetto)
- **Dipende da:** R0731; D-01; D-11; D-13; R0360; R0362; R0698
- **Assorbe:** R0570
- **Nota:** Con co-occorrenza HD 8 um lo speedup sarebbe 7.8x (s1_speedups.csv), non usabile per D-13. Rho di S1 non nel pacchetto.
- **Modificata in arbitrato:** instruction, level, depends_on (vedi `arbitrati.csv`)

#### R0701 · S5 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa; tabella:Table 10 (riga 149); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `(with N taking the values 50, 100, and 200)`
- **Valore:** (with N taking the values 50, 100, and 200) → (da rileggere, vedi fonte)
- **Istruzione:** Riga 149: i Metodi dichiarano SVG Jaccard per N = 50, 100 e 200, Table 10 riporta solo top-50 e FDR < 0.05. In S5, quando Table 10 si rifà da SPATIAL/results_v2, riportare tutti i valori di N presenti nei JSON di concordanza; se ci sono solo top-50 e FDR, riscrivere "(with N taking the values 50, 100, and 200)" come "(N = 50)".
- **Fonte:** SPATIAL/results_v2 JSON di concordanza, campo SVG Jaccard (non nel pacchetto)

#### R0345 · S5 · P9 (convenzione sulle ripetizioni) · superata-da-S1
- **Bersaglio:** tabella:Table 8, Table 9, Table 10 (riga 165); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Each benchmark configuration was repeated five times; we report mean +/- standard deviation`
- **Valore:** n.d. → dgx_cpu total 719.03 +/- 3.16 s; server_gpu total 92.21 +/- 0.68 s; server_cpu total 617.24 +/- 11.34 s
- **Istruzione:** Le SD di marzo (r2-5) del registro non valgono più. In S5, quando le tabelle spatial si rifanno da S1, aggiungere accanto a ogni media la SD campionaria delle 5 ripetizioni (colonne mean_1_5 e sd_1_5 di s1_step_stats.csv, run dgx_cpu, server_gpu e server_cpu) e dichiarare in didascalia n = 5 e ddof = 1.
- **Decisione o convenzione:** CONV
- **Fonte:** s1_step_stats.csv platform=visium_hd_square_008um step=total colonne mean_1_5, sd_1_5 (tutte le piattaforme e gli step dallo stesso file)
- **Dipende da:** CONV; R0466
- **Nota:** ddof = 1 verificato in S2 su tutte le righe di s1_step_stats.csv (per esempio dgx_cpu HD 8 um total: 3.162 con ddof = 1, 2.828 con ddof = 0).
- **Modificata in arbitrato:** note (vedi `arbitrati.csv`)

#### R0280 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** tabella:Table 8, Table 9; prosa spatial (riga 166); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `For spatial benchmarks, the first repeat served as a JIT/warmup run and was excluded; we report the mean of repeats 2-5`
- **Valore:** n.d. → visium_hd_square_008um total senza co-occorrenza: reference_dgx 6.87 [6.82; 6.92]; control_server 6.08 [5.97; 6.18]
- **Istruzione:** I ricalcoli della revisione sui dati di marzo (41.46x, 6.39x, 29.2x, 2,087.9x, RAM CPU r1-5 8.08 e 10.77, 3,272x dalla sola r2, 538 cluster modali) sono superati da S1. In S5 rifare Tables 8 e 9 e ogni speedup spatial da s1_step_stats.csv e s1_speedups.csv con cpu=reference_dgx e convention=1_5, con il controllo control_server accanto; a Visium HD 8 um lo speedup end-to-end si dà senza co-occorrenza (D-13), da s1_extra_numbers.json; i gruppi di Leiden per macchina da own_leiden_clusters. Righe di prosa con valori di marzo che nessun'altra voce ancora, da riscrivere esplicitamente in S5 con s1_speedups.csv e s1_step_stats.csv (reference_dgx, 1_5, controllo control_server accanto) e con i JSON di concordanza di S1: 348 (PCA, normalisation, Moran's I e Geary's C separati, UMAP: oggi 257x, 176x, 162-163x, 159x; in S1 37.0x, 30.4x, 20.8x e 122.4x, 197.1x), 349 (Leiden e expression neighbours: oggi 16x e 20x; in S1 12.9x e 13.5x), 370 (Visium v1 end-to-end, oggi 1.7x, in S1 1.4x, e gli step che dominano), 372 (tempo dei vicini spaziali su server_gpu), 377 (frase 'near-perfect across all platforms', da rileggere sulla concordanza S1), 381 (Jaccard top-50), 382 (sovrapposizione FDR < 0.05), 397 (ARI e NMI di Visium v1 e HD 8 um). Ogni riga si registra nel diario con il file letto.
- **Decisione o convenzione:** D-01;D-13;CONV
- **Fonte:** s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um; s1_speedups.csv cpu=reference_dgx convention=1_5; s1_step_stats.csv
- **Dipende da:** D-13; CONV; R0453
- **Nota:** Convenzione verificata in S2: speedup_total_without_co_occurrence di s1_extra_numbers.json usa mean_1_5 (6.8685 riprodotto da s1_step_stats.csv; con mean_2_5 sarebbe 6.8783).
- **Modificata in arbitrato:** note, instruction (vedi `arbitrati.csv`)

#### R0285 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** tabella:Table 8 riga HD 8 um (riga 335); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Visium HD 8 um | 393,543 | 4,068 | 79 | 51.6x | 8.1 | 22.6`
- **Valore:** 4,068 | 79 | 51.6x | 8.1 | 22.6 → 615.78666 | 89.65312 | 6.868546906119942
- **Istruzione:** Riga 335, Table 8 riga "Visium HD 8 um | 393,543 | 4,068 | 79 | 51.6x | 8.1 | 22.6": sostituire tempi e speedup con quelli di S1, riferimento DGX, convenzione 1-5, co-occorrenza esclusa (D-13). Speedup: 6.9x (value_new). CPU total e GPU total vanno scritti senza co-occorrenza: calcolarli in S5 come mean_1_5(total) meno mean_1_5(co_occurrence) per dgx_cpu e server_gpu, e controllare che il loro rapporto riproduca value_new. RAM e VRAM dai nuovi JSON (R0331, R0332). Rifare l'intera Table 8 da S1, compresa la riga Visium v1 (riga 334, registro PASS ma superata da S1) e aggiungere una colonna o nota con lo speedup del controllo server (128 thread).
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0] (IC [1],[2]); SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=total col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=co_occurrence col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=server_gpu platform=visium_hd_square_008um step=total col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=server_gpu platform=visium_hd_square_008um step=co_occurrence col=mean_1_5; controllo: SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.control_server
- **Dipende da:** CONV; D-13; R0282
- **Nota:** Verifica S2: (719.0313-103.24464)/(92.20562-2.5525) riproduce 6.868546906119942 (convenzione 1_5). Con la co-occorrenza inclusa sarebbe 7.8x: non usarlo (D-13). Riga 334 (Visium v1): 1.4x, CPU 33.9 s, GPU 24.0 s.
- **Modificata in arbitrato:** source, value_new (vedi `arbitrati.csv`)

#### R0361 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** fig:fig7_spatial_speedup.png (riga 340); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Error bars: standard deviation across repeats 2-5 (repeat 1 excluded for JIT warmup). HD 2 um was subsampled to 400k bins due to local VRAM constraints`
- **Valore:** 1.7x | 51.6x | repeats 2-5 (repeat 1 excluded for JIT warmup) | 400k bins → 1.4138500544127761 | 10.426139539453574
- **Istruzione:** Riga 340, didascalia e figura 7: rigenerare la figura da s1_step_stats.csv (totali dgx_cpu e server_gpu, mean_1_5 e sd_1_5) con lo script di R0382, con HD 8 um senza co-occorrenza come in Table 8. Didascalia proposta: "**Figure 7.** Total pipeline wall time on three Visium platforms: CPU reference (one DGX H100 node, 100 CPUs) and GPU (one RTX 4090). End-to-end speedups range from 1.4x (Visium v1, 2,695 spots) to 10.4x (Visium HD 2 um, 389,492 bins). Error bars: standard deviation across 5 repeats, each in a fresh process. At Visium HD 8 um co-occurrence is excluded (see text). Visium HD 2 um was subsampled to 389,492 bins to fit in the 24 GB of the RTX 4090." Togliere "repeat 1 excluded for JIT warmup" e "400k".
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_step_stats.csv step=total col=mean_1_5,sd_1_5
- **Dipende da:** CONV; D-13; R0382; R0285
- **Nota:** Il ricalcolo del registro (pixel della PNG di marzo) e' superato: la figura si rifa'. Il massimo e' ora HD 2 um, non HD 8 um.

#### R0381 · S5 · P14 (figure) · correggere
- **Bersaglio:** fig:fig7_spatial_speedup.png; fig:fig8_spatial_perstep.png; fig:fig9_spatial_concordance.png (riga 340); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `**Figure 7.** Total pipeline wall time (CPU vs GPU) for three Visium spatial platforms on a single RTX 4090`
- **Istruzione:** Figure 7-9: usare la stessa palette delle figure 1-6 (dizionario COLORS di scripts/generate_figures.py come fissato in S4): CPU sempre lo stesso colore, GPU sempre lo stesso; nelle figure 9 non riusare i colori CPU/GPU per le piattaforme. Nomi degli step in inglese britannico come nel testo e in Table 9 ("Normalisation", "Expression neighbours", "Co-occurrence", "Moran's I"), non snake_case; unita' "s" uniformi.
- **Fonte:** scripts/generate_figures.py COLORS (palette di S4); script delle figure spatial di R0382
- **Dipende da:** R0382; R0377; R0379
- **Nota:** La parte su Fig. 1-6 (colori ripetuti, tick '1000k' in Fig. 6) e' di S4; qui solo Fig. 7-9, coordinandosi con la palette scelta in S4.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0382 · S5 · P14 (figure) · correggere
- **Bersaglio:** script:figures/generate_spatial_figures.py (riga 340); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `**Figure 7.** Total pipeline wall time (CPU vs GPU) for three Visium spatial platforms on a single RTX 4090`
- **Istruzione:** Riscrivere figures/generate_spatial_figures.py (o un nuovo script nel ramo di lavoro) che legga SPATIAL/results_v2/s1_step_stats.csv, s1_speedups.csv e i JSON di concordanza nuovi e produca fig7-9 pubblicate, con barre di errore, senza valori scritti a mano; aggiornare GENERATION_SUMMARY.md e SPATIAL_FIGURES_README.txt. Nell'Availability (righe 459-460) aggiungere che script e risultati del nuovo riferimento spatial stanno nel repository: proposta "All code, Dockerfiles, SLURM submission scripts, benchmark result JSON files and the scripts that generate every figure are available at <https://github.com/lucavd/2026.scRNA_DGX>." La correzione del filtro cpu_/gpu*_ in scripts/generate_figures.py (fig1-6) spetta a S4.
- **Fonte:** SPATIAL/results_v2/s1_step_stats.csv; SPATIAL/results_v2/s1_speedups.csv; i 6 JSON di concordanza S1 (riferimento DGX contro GPU e controllo server contro GPU, 3 piattaforme): elencarli con ls in sola lettura all'apertura di S5, scriverne percorsi e md5 nel diario e usarli in tutte le voci che citano rho, Jaccard o ARI spatial
- **Nota:** Scrittura sul server solo in S5, non in S2. Verificare in S5 se il ramo rerun-spatial-v2 va fuso in main prima di citare il repository.
- **Modificata in arbitrato:** value_old, source (vedi `arbitrati.csv`)

#### R0344 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 344); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `At 393,543 bins with 7 Leiden clusters, co-occurrence alone consumed 88% of the CPU pipeline time`
- **Valore:** 7 Leiden clusters | 88% → 4 | 14.4%
- **Istruzione:** Riga 344: "At 393,543 bins with 7 Leiden clusters, co-occurrence alone consumed 88% of the CPU pipeline time." Con S1 CPU e GPU usano gli stessi gruppi. Sostituire con "At 393,543 bins, with the same 4 Leiden groups for CPU and GPU, co-occurrence took X% of the DGX CPU pipeline time." dove X = mean_1_5(co_occurrence)/mean_1_5(total) di dgx_cpu HD 8 um, calcolato in S5. Se R0362 resta come paragrafo sul difetto, la frase si puo' fondere li'.
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_evaluation.json gates.G5.detail[visium_hd_square_008um].n_groups; SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=co_occurrence col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_008um step=total col=mean_1_5
- **Dipende da:** R0362
- **Nota:** Verifica S2: 103.24464/719.0313 = 14.4%. La riga PASS R0291 sulla stessa frase e' superata anch'essa.
- **Modificata in arbitrato:** value_new (vedi `arbitrati.csv`)

#### R0363 · S5 · P14 (figure) · correggere
- **Bersaglio:** fig:fig8_spatial_perstep.png (riga 346); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Co-occurrence analysis achieves a 3,272x speedup (CPU: 3,573 s to GPU: 1.09 s), the single largest acceleration measured in this study`
- **Valore:** 3,272x → (da rileggere, vedi fonte)
- **Istruzione:** Fig. 8 rigenerata: etichette uguali a Table 9 (inglese britannico, non snake_case), includere data loading e QC (oggi omessi), palette leggibile da daltonici (non verde/rosso), e valori di didascalia, figura e Table 9 letti dallo stesso file (s1_speedups.csv) cosi' che non possano discordare.
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_008um cpu=reference_dgx convention=1_5
- **Dipende da:** R0366; R0381; R0382
- **Assorbe:** R0292

#### R0366 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** fig:fig8_spatial_perstep.png (riga 346); registro: UNSUPPORTED, critical
- **Ancora (univoca nel .md):** `Co-occurrence analysis achieves a 3,272x speedup (CPU: 3,573 s to GPU: 1.09 s), the single largest acceleration measured in this study`
- **Valore:** 3,272x | 162-163x | 1.0x → umap 197.0912179975394 | geary 122.35513684336057 | moran 20.769131024777607 | spatial_neighbors 0.8026325083510424 | nhood_enrichment 1.0559152368942308
- **Istruzione:** Riga 346, didascalia Fig. 8: rigenerare la figura da s1_speedups.csv (HD 8 um, reference_dgx, 1_5, con IC bootstrap) e sostituire la didascalia con "**Figure 8.** Per-step GPU speedup on Visium HD 8 um (393,543 bins) against the DGX CPU reference (mean of 5 repeats; error bars: 95% bootstrap CI). The largest speedups were for UMAP (197x) and Geary's C (122x); Moran's I reached 20.8x. Spatial neighbours and neighbourhood enrichment run on the CPU in both pipelines (0.8x and 1.1x). Co-occurrence is not shown because the GPU result with rapids-singlecell 0.14.1 was incorrect (see text)." Togliere "the single largest acceleration measured in this study".
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_008um cpu=reference_dgx convention=1_5 step=umap,spatial_autocorr_geary,spatial_autocorr_moran,spatial_neighbors,nhood_enrichment
- **Dipende da:** D-13; R0362; R0382
- **Nota:** Moran (20.8x) e Geary (122x) non sono piu' simili: S1 P5 spiega che il DGX e' lento in Moran (82.7 s). Il testo non deve piu' scrivere 'Moran's I, Geary's C 162-163x' (anche riga 348 PASS e Discussione 428, traccia T5).

#### R0309 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 368); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Without this step, UMAP dominated the GPU pipeline time (92x speedup, but consuming 92% of the 97 s total GPU time)`
- **Valore:** 92x | 92% | 97 s → T 109.9 s | A 50.4% | B 27.8% | C 72.0% | UMAP 89.4x
- **Istruzione:** Riga 368: "Without this step, UMAP dominated the GPU pipeline time (92x speedup, but consuming 92% of the 97 s total GPU time)." e' sbagliata (quota CPU scambiata per GPU). Riscrivere con S1 riferimento DGX: "Without this step, the GPU pipeline time on HD 2 um (T s) was dominated by spatial neighbours (A%) and data loading (B%); UMAP, the largest CPU cost (C% of the CPU time), ran 89.4x faster on the GPU." T in value_new; A, B, C calcolati in S5 come mean_1_5(step)/mean_1_5(total) da s1_step_stats.csv (server_gpu e dgx_cpu, HD 2 um). Riscrivere nello stesso passo le righe 367 (HD 2 um ora ha lo speedup piu' alto, non piu' basso) e 373 ("57-73%") con le quote di spatial_neighbors su server_gpu HD 8 um e HD 2 um.
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=umap cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_step_stats.csv run=server_gpu platform=visium_hd_square_002um step=total col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=server_gpu,dgx_cpu platform=visium_hd_square_002um steps=umap,spatial_neighbors,data_loading,total col=mean_1_5
- **Dipende da:** CONV; R0360
- **Assorbe:** R0374, R0675
- **Nota:** Verifica S2 (server_gpu HD 2 um, mean_1_5): UMAP 8.4%, spatial neighbours 50.4% di 109.92 s; spatial neighbours HD 8 um 61.1% di 92.21 s.
- **Modificata in arbitrato:** value_new (vedi `arbitrati.csv`)

#### R0365 · S5 · P10 (concordanza) · superata-da-S1
- **Bersaglio:** fig:fig9_spatial_concordance.png (riga 379); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Cluster concordance (ARI) degrades at HD 2 um resolution (0.080) due to algorithmic differences between cugraph and leidenalg Leiden implementations at high ...`
- **Valore:** rho >= 0.9995 | equals 1.0 | (0.080) | cugraph and leidenalg → (da rileggere, vedi fonte)
- **Istruzione:** Riga 379, didascalia e figura 9: rigenerare da i JSON di concordanza nuovi (riferimento DGX contro GPU), con le stesse metriche. Nella didascalia: sostituire "between cugraph and leidenalg Leiden implementations" con "between the igraph (CPU) and cuGraph (GPU) Leiden implementations, which also ran with different iteration settings" e togliere l'annotazione 'Algorithmic difference' nel pannello (causa non verificata). Valori di rho, Jaccard e ARI (oggi >= 0.9995, 1.0, 0.080) da rileggere: S5.md anticipa ARI 0.97 a HD 8 um e 0.07-0.08 a HD 2 um, dipendente dalla macchina CPU. Aggiungere che il numero di gruppi CPU cambia con la macchina (R0699).
- **Fonte:** SPATIAL/results_v2/ file di concordanza (6 JSON: riferimento DGX contro GPU, controllo server contro GPU; percorso da rileggere sul server, non nel pacchetto); benchmark_spatial_cpu.py righe 333-335 (flavor='igraph', n_iterations=2); peer_review.md H8
- **Dipende da:** R0382; R0694
- **Assorbe:** R0314
- **Nota:** Il registro conferma i numeri di marzo; sono superati dal nuovo riferimento CPU (cluster CPU diversi).

#### R0698 · S5 · PM (arrotondamenti e minori) · correggere
- **Bersaglio:** prosa (riga 380); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Moran's I and Geary's C Spearman correlations between CPU and GPU exceeded 0.9995 in all cases`
- **Valore:** exceeded 0.9995 → (da rileggere, vedi fonte)
- **Istruzione:** Riga 380 "exceeded 0.9995 in all cases": la disuguaglianza stretta non vale (Geary HD 8 um = 0.9995). Scrivere "were at least R in all cases" con R = minimo dei rho Moran e Geary nei JSON di concordanza nuovi (riferimento DGX contro GPU), arrotondato per difetto a 4 decimali. Stessa forma in Conclusioni riga 440 (R0340).
- **Fonte:** SPATIAL/results_v2/ file di concordanza (6 JSON: riferimento DGX contro GPU, controllo server contro GPU; percorso da rileggere sul server, non nel pacchetto)
- **Dipende da:** R0365
- **Nota:** Il minimo di marzo era 0.999526; il nuovo va riletto.
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)

#### R0699 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 398); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `the CPU pipeline identified 2,559 clusters while the GPU pipeline found 538`
- **Valore:** 2,559 | 538 | ARI = 0.080, NMI = 0.667 → 3027 | 538
- **Istruzione:** Riga 398: "However, on HD 2 um, clustering diverged substantially (ARI = 0.080, NMI = 0.667): the CPU pipeline identified 2,559 clusters while the GPU pipeline found 538." Sostituire 2,559 con 3,027 (CPU DGX) e ARI, NMI con i valori dei JSON di concordanza nuovi (riferimento DGX contro GPU). Aggiungere: "The number of CPU clusters depended on the CPU machine (2,559 on the 128-thread server)." Il rapporto 4.75x della riga 399 si tratta in R0329.
- **Decisione o convenzione:** D-11
- **Fonte:** SPATIAL/results_v2/s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um; SPATIAL/results_v2/ file di concordanza (6 JSON: riferimento DGX contro GPU, controllo server contro GPU; percorso da rileggere sul server, non nel pacchetto)
- **Dipende da:** R0326; R0365
- **Nota:** Il ricalcolo del registro (4.757 arrotondato 4.76x) e' superato: con il riferimento DGX il rapporto cambia (R0329).
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)

#### R0615 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 430); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `The dramatic divergence at Visium HD 2 um (ARI = 0.080) is not specific to GPU versus CPU comparison; rather, it reflects the fundamental sensitivity of stoc...`
- **Valore:** ARI = 0.080 → (da rileggere, vedi fonte)
- **Istruzione:** Riga 430: sostituire 'The dramatic divergence at Visium HD 2 um (ARI = 0.080) is not specific to GPU versus CPU comparison; rather, it reflects the fundamental sensitivity of stochastic graph-partitioning algorithms to implementation details when the solution landscape contains many near-degenerate partitions.' con: "At Visium HD 2 um, CPU and GPU Leiden partitions diverged (ARI [S1 value]): CPU Leiden returned 3,027 clusters on the DGX reference and 2,559 on the control server, each identical across five repeats, against 538 on the GPU. The divergence is therefore systematic between implementations and machines rather than run-to-run stochasticity; we did not test whether different seeds of the same implementation diverge to a similar extent." L'ARI va riletto nel JSON di concordanza di S1 (DGX contro GPU; S5.md indica 0.07-0.08 a seconda della CPU).
- **Fonte:** SPATIAL/results_v2/s1_extra_numbers.json own_leiden_clusters.visium_hd_square_002um (dgx_cpu, server_cpu, server_gpu); ARI: SPATIAL/results_v2 concordanza HD 2 um DGX contro GPU (non nel pacchetto); S5.md
- **Dipende da:** D-11; R0699; R0326; R0365
- **Assorbe:** R0336
- **Nota:** La revisione usava 2,559 cluster CPU (workstation di marzo) e 534-538 GPU: superati; nel rerun la GPU dà 538 in tutte e 5 le ripetizioni.
- **Modificata in arbitrato:** level, depends_on (vedi `arbitrati.csv`)

#### R0340 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 440); registro: UNSUPPORTED, critical
- **Ancora (univoca nel .md):** `For spatial transcriptomics, GPU acceleration delivers 51.6x end-to-end speedup on Visium HD, with co-occurrence analysis achieving a 3,272x speedup and spat...`
- **Valore:** 51.6x | 3,272x | exceeding 0.9995 → 1.4138500544127761 | 6.868546906119942 | 10.426139539453574
- **Istruzione:** Riga 440: sostituire con "For spatial transcriptomics on one RTX 4090, end-to-end speedups against a 100-CPU DGX node were 1.4x on Visium v1, 6.9x on Visium HD 8 um with co-occurrence excluded and 10.4x on Visium HD 2 um; Moran's I and Geary's C agreed between CPU and GPU (Spearman rho at least R). The GPU co-occurrence of rapids-singlecell 0.14.1 was incorrect at Visium HD 8 um because of 32-bit integer overflow; version 0.15.1 corrects it at unchanged runtime." R come in R0698. Togliere 51.6x e 3,272x.
- **Decisione o convenzione:** D-13
- **Fonte:** SPATIAL/results_v2/s1_speedups.csv platform=visium step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/s1_extra_numbers.json speedup_total_without_co_occurrence.visium_hd_square_008um.reference_dgx[0]; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; SPATIAL/results_v2/cooc_check/cooc_check_eval.json; SPATIAL/results_v2/ file di concordanza (6 JSON: riferimento DGX contro GPU, controllo server contro GPU; percorso da rileggere sul server, non nel pacchetto)
- **Dipende da:** R0360; R0362; R0698; D-13
- **Assorbe:** R0636
- **Nota:** Se il PI accorcia, tenere almeno il valore HD 8 um senza co-occorrenza e il difetto della co-occorrenza.
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)


## L4 · nuovo calcolo dai grezzi (9 voci)

#### R0653 · S3 · P13 (affermazioni oltre i dati) · aggiungere
- **Bersaglio:** prosa (riga 83); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `a GPU warmup step was then executed to absorb CUDA context initialisation overhead before timing.`
- **Istruzione:** Nei Metodi, dopo la frase di riga 83 sul warmup, aggiungere cosa resta fuori dal cronometro (nessuna voce di frase lo copre): "Timed steps excluded RMM pool initialisation, the GPU warmup, the copy of the matrix to adata.raw, HVG subsetting and the start-up and shutdown of the Dask cluster, so end-to-end times are sums of timed steps. The wall-clock interval between consecutive runs, an upper bound that also includes writing results, was <c> s against <d> s timed for one GPU at 10,000 cells." Valori: <c> = 8.2 s, <d> = 2.5 s, da scrivere con "(repeats 2-5)" accanto. Il timestamp si registra a fine ripetizione, prima del salvataggio, quindi l'intervallo k contiene la ripetizione k+1: i 4 intervalli (8.232, 8.028, 8.441, 8.219 s, media 8.23) si abbinano alle ripetizioni 2-5 (timings.total media 2.503 s); la ripetizione 1 (6.40 s) non ha un intervallo che la contenga, per cui la convenzione A non si applica. Registrare l'eccezione nel diario come decisione tecnica: l'esclusione della ripetizione 1 non favorisce la GPU (con la media r1-5, 3.28 s, la parte non cronometrata sembrerebbe minore). Fonte: results/gpu_10000_r{1..5}_results.json metadata.timestamp e timings.total (copia nel pacchetto S2 in scrna_json/results/).
- **Decisione o convenzione:** CONV
- **Fonte:** results/gpu_10000_r{1..5}_results.json metadata.timestamp (4 intervalli fra ripetizioni consecutive, che contengono le ripetizioni 2-5, media 8.23 s) e timings.total (media r2-5 2.503 s; copia nel pacchetto S2 in scrna_json/results/)
- **Dipende da:** CONV
- **Assorbe:** R0665
- **Nota:** I valori del registro sono medie r2-5 (peer_review.md PoW-G): con la convenzione A vanno ricalcolati; l'intervallo include il salvataggio, quindi e' solo un limite superiore.
- **Modificata in arbitrato:** source, instruction, anchor, line, quality (vedi `arbitrati.csv`)

#### R0167 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** tabella:Table 6 (riga 283); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `: **Table 6.** Indicative memory budget at the 12M-cell failure point. The baseline components are a reconstruction that sums to the 535 GB recorded at the l...`
- **Valore:** a reconstruction that sums to the 535 GB → (da rileggere, vedi fonte)
- **Istruzione:** Ricostruire Table 6 dalla traccia di 11.9M (lettura dei JSON sul server, nessun nuovo run). Struttura: (a) Baseline misurata a 11.9M: una sola copia sparsa completa (raw) di circa 426 GB, letta come RAM a inizio QC dopo la replicazione; matrice densa HVG a 11.9M (88.7 GiB = 11,899,623 x 2,000 x 4 B); residuo = 534.55 meno le due voci (534.55 - 426.10 - 88.66 = 19.79 GiB), etichettato "remainder (metadata, runtime, allocator)"; subtotale misurato 535. (b) Transitori stimati, con la formula dichiarata in nota. (c) Allocazione SLURM e memoria fisica. Didascalia: sostituire "The baseline components are a reconstruction that sums to the 535 GB recorded at the last successful run (11.9M cells)." con "Baseline components are read from the 11.9M-cell memory trace and sum to the 535 GB recorded there; all rows refer to 11.9M cells." Togliere la doppia base 12M/11.9M (R0718). Tutte le righe della tabella in GiB, come le misure della traccia (R0252: rss/1024**3): intestazione "GiB" e stime dei transitori calcolate e scritte in GiB.
- **Fonte:** revisione_n2_log.csv id=R0167 campo recomputed (a05_stress_de.py; 123.13 GiB per 3.44M x 3.46); peer_review.md 'Verifica collaterale' (95.2 GB decimali = 88.66 GiB a 11.9M); results/maxpower_11900000_8gpu_results.json memory.detailed (traccia RAM per step in GiB; copia nel pacchetto S2 in scrna_json/results/)
- **Dipende da:** R0148; R0243
- **Assorbe:** R0718
- **Nota:** Primaria per R0718. Le voci 190 + 190 + 96 + 60 sommano a 536 e non corrispondono al codice (una sola copia sparsa). Alternativa: togliere Table 6 per D-03 (pi_choices).
- **Modificata in arbitrato:** source, instruction (vedi `arbitrati.csv`)

#### R0170 · S3 · P6 (stress test replicato) · togliere
- **Bersaglio:** tabella:Table 6 riga adata.X (riga 288); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Sparse raw matrix `adata.X` (CSR, ~5% density) | ~190`
- **Valore:** ~190 → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la riga "Sparse raw matrix `adata.X` (CSR, ~5% density) | ~190": al campione di 535 GB adata.X e' gia' la matrice HVG densa (scale su CPU), che ha la sua riga (riga 290). In quella riga scrivere la base 11.9M: "Dense scaled HVG matrix `adata.X` (11.9M x 2,000, float32) | 89" (GiB, come tutta la tabella, R0252: 11,899,623 x 2,000 x 4 B = 88.66 GiB). Togliere "~5% density" (non verificabile).
- **Fonte:** revisione_n2_log.csv id=R0170 campo recomputed (scripts/benchmark_maxpower.py righe 611-627); peer_review.md verifica collaterale (95.2 GB)
- **Dipende da:** R0167
- **Modificata in arbitrato:** instruction (vedi `arbitrati.csv`)

#### R0171 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** tabella:Table 6 riga adata.raw (riga 289); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Sparse raw copy `adata.raw` (DE backup) | ~190`
- **Valore:** ~190 → (da rileggere, vedi fonte)
- **Istruzione:** Sostituire "Sparse raw copy `adata.raw` (DE backup) | ~190" con la sola copia sparsa completa misurata, circa 426 GB (RAM a inizio QC a 11.9M), etichettata "Sparse raw matrix `adata.raw` (11.9M cells, replicated) | ~426". S3 conferma il valore dalla traccia del JSON.
- **Fonte:** revisione_n2_log.csv id=R0171 campo recomputed; revisione_n2_log.csv id=R0148 campo recomputed (426.10 GiB a inizio QC); results/maxpower_11900000_8gpu_results.json memory.detailed (48 campi, GiB secondo R0252; copia nel pacchetto S2 in scrna_json/results/)
- **Dipende da:** R0167
- **Nota:** Il registro da' 'circa 420 GiB' (R0171) e 426.10 (R0148): valore finale da rileggere.
- **Modificata in arbitrato:** source (vedi `arbitrati.csv`)

#### R0173 · S3 · P6 (stress test replicato) · riformulare
- **Bersaglio:** tabella:Table 6 riga metadata (riga 291); registro: UNVERIFIABLE, minor
- **Ancora (univoca nel .md):** `Scanpy metadata + Python runtime + allocator overhead | ~60`
- **Valore:** ~60 → (da rileggere, vedi fonte)
- **Istruzione:** La voce "Scanpy metadata + Python runtime + allocator overhead | ~60" non e' misurata: nella tabella ricostruita diventa il residuo calcolato (subtotale misurato meno le voci misurate), etichettato "remainder (by difference)".
- **Fonte:** calcolo per differenza dalla traccia (R0167)
- **Dipende da:** R0167

#### R0174 · S3 · P6 (stress test replicato) · correggere
- **Bersaglio:** tabella:Table 6 riga subtotale (riga 292); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `*Measured subtotal (11.9M)* | **535**`
- **Valore:** **535** → (da rileggere, vedi fonte)
- **Istruzione:** Il subtotale misurato 535 (534.55) resta, ma deve essere la somma delle voci sopra: dopo R0167 le voci sono costruite in modo da sommare a 535 (residuo per differenza).
- **Fonte:** revisione_n2_log.csv id=R0174 campo recomputed
- **Dipende da:** R0167; R0173

#### R0176 · S3 · P6 (stress test replicato) · togliere
- **Bersaglio:** tabella:Table 6 riga +302 (riga 294); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `Unattributed rise between data loading and QC (measured at 11.9M) | +302`
- **Valore:** +302 → (da rileggere, vedi fonte)
- **Istruzione:** Togliere la riga "Unattributed rise between data loading and QC (measured at 11.9M) | +302": e' la replicazione del dataset (R0148), resta in memoria nei campioni successivi ed e' gia' dentro i 535 (doppio conteggio).
- **Fonte:** revisione_n2_log.csv id=R0176 campo recomputed
- **Dipende da:** R0148; R0167

#### R0286 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** tabella:Table 8 riga HD 2 um (riga 336); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `Visium HD 2 um | 389,492 | 1,042 | 97 | 10.8x | 10.8 | 22.6`
- **Valore:** 1,042 | 97 | 10.8x | 10.8 | 22.6 → 1146.05794 | 109.92159999999998 | 10.426139539453574
- **Istruzione:** Riga 336, Table 8 riga "Visium HD 2 um | 389,492 | 1,042 | 97 | 10.8x | 10.8 | 22.6": sostituire CPU total, GPU total e speedup con i valori di S1 (riferimento DGX, 1-5): CPU 1,146 s, GPU 110 s, speedup 10.4x. A HD 2 um la co-occorrenza non gira, quindi il totale non va corretto. RAM e VRAM dai nuovi JSON. Controllare nei JSON il numero di bin dopo QC (n_spots_after_qc) prima di confermare 389,492.
- **Fonte:** SPATIAL/results_v2/s1_step_stats.csv run=dgx_cpu platform=visium_hd_square_002um step=total col=mean_1_5; SPATIAL/results_v2/s1_step_stats.csv run=server_gpu platform=visium_hd_square_002um step=total col=mean_1_5; SPATIAL/results_v2/s1_speedups.csv platform=visium_hd_square_002um step=total cpu=reference_dgx convention=1_5; RAM/VRAM: SPATIAL/results_v2/{dgx_cpu,server_gpu,server_cpu}/spatial_*_r{1..5}_results.json campi memory (peak_ram_gb, VRAM NVML); non nel pacchetto
- **Dipende da:** CONV; R0282
- **Nota:** Controllo server: 9.4x.
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)

#### R0332 · S5 · P4 (spatial) · superata-da-S1
- **Bersaglio:** prosa (riga 406); registro: MISMATCH, minor
- **Ancora (univoca nel .md):** `CPU RAM ranged from 1.3 GB (Visium v1) to 10.8 GB (HD 2 um)`
- **Valore:** 1.3 GB | 10.8 GB → (da rileggere, vedi fonte)
- **Istruzione:** Riga 406 "CPU RAM ranged from 1.3 GB (Visium v1) to 10.8 GB (HD 2 um).": sostituire con i picchi di RAM dei run CPU di riferimento (dgx_cpu, media di 5 processi nuovi, quindi senza residui fra ripetizioni) e aggiungere la RAM massima della pipeline GPU: "Peak CPU RAM ranged from R1 GB (Visium v1) to R2 GB (HD 2 um) on the DGX CPU reference, and reached R3 GB in the GPU pipeline."
- **Decisione o convenzione:** D-11
- **Fonte:** SPATIAL/results_v2/{dgx_cpu,server_gpu,server_cpu}/spatial_*_r{1..5}_results.json campi memory (peak_ram_gb, VRAM NVML); non nel pacchetto
- **Dipende da:** CONV; R0282
- **Nota:** La contaminazione fra ripetizioni nello stesso processo segnalata dal registro non esiste nei run S1 (un processo per ripetizione).
- **Modificata in arbitrato:** level (vedi `arbitrati.csv`)


## L5 · decisione strutturale (14 voci)

#### R0730 · S3 · P1 (titolo, abstract, estensione) · riformulare
- **Bersaglio:** prosa (riga 2); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `GPU-accelerated single-cell and spatial transcriptomics on NVIDIA DGX H100: a systematic benchmark of speed, scalability, and biological concordance`
- **Valore:** GPU-accelerated single-cell and spatial transcriptomics on NVIDIA DGX H100: a systematic benchmark of speed, scalability, and biological concordance → (da rileggere, vedi fonte)
- **Istruzione:** Riga 2 (YAML title): il titolo e' identico a quello dello short paper e la regola CIBB chiede un titolo leggermente diverso; inoltre attribuisce al DGX H100 anche lo spatial (GPU su RTX 4090). Il PI sceglie il nuovo titolo; proposte, senza 'systematic' (scala su un solo dataset, R0559) e senza 'scalability' (D-02): A "GPU acceleration of single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics against a common 100-CPU reference: speed, memory limits and concordance"; B "How much do GPUs accelerate single-cell and spatial transcriptomics? Benchmarking rapids-singlecell against Scanpy and Squidpy on a common CPU reference". Dopo la scelta riportare lo stesso titolo nel sorgente LaTeX (S7) e in METEOR; verificare con difflib che differisca dal titolo dello short paper.
- **Decisione o convenzione:** PI-S3
- **Fonte:** full_paper_LNBI.md riga 2; titolo dello short paper in manuscript_short_cameraready.md riga 1 (server, non nel pacchetto)
- **Dipende da:** D-06; D-02
- **Nota:** Bloccante per l'ammissibilita'. Le righe R0001 (hardware) e R0559 (systematic) vincolano il testo scelto.

#### R0731 · S3 · P1 (titolo, abstract, estensione) · riformulare
- **Bersaglio:** prosa (riga 14); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `**Abstract.** Single-cell RNA sequencing (scRNA-seq) datasets now routinely exceed one million cells`
- **Istruzione:** Riga 14: l'abstract e' identico parola per parola allo short paper (9 frasi su 9, 246 parole) e la regola CIBB chiede un abstract diverso; limite LNCS 150-250 parole. Riscriverlo intorno all'estensione (nuovo riferimento CPU spatial di S1, D-01; difetto della co-occorrenza GPU, D-13) recependo le voci di frase R0007, R0565, R0566, R0567, R0240, R0568, R0254, R0711, R0639 e i vincoli D-02 e D-04 (44x come confronto di tempi). Bozza da sottoporre al PI, con i valori copiati dai file del pacchetto (spatial da s1_speedups.csv e s1_extra_numbers.json, reference_dgx, 1_5; la concordanza spatial va aggiunta solo se S5 la rilegge da SPATIAL/results_v2): "Single-cell and spatial transcriptomics now yield millions of cells or bins, and standard frameworks run on CPUs. We compared rapids-singlecell on NVIDIA H100 GPUs with Scanpy on 100 logical CPUs of a DGX H100 cluster, on 10,000 to 1.3 million mouse brain cells sampled from CELLxGENE Census, with five repeats per configuration. At 1.3 million cells the GPU pipeline took 435 s against 52,056 s on CPU (119.6-fold; 105.5-fold in a run that differed only in data loading). Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold. In the multi-GPU configuration tested, additional GPUs did not take part in the computation. At 10,000 cells HVG selection was identical and Leiden clustering agreed with ARI 0.908-0.963. A memory-optimised pipeline processed 11.9 million cells, built from copies of a 3,436,470-cell dataset, on one node, limited by host RAM. Pseudo-bulk differential expression finished 44 times sooner than the cell-level t-test at 3.4 million cells. For spatial data we rebuilt the CPU reference with one fresh process per repeat and the same cell groups for CPU and GPU. Against this DGX CPU reference, an RTX 4090 accelerated end-to-end analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occurrence) and 10.4-fold on Visium HD 2 um. At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances because of 32-bit integer overflow; version 0.15.1 matched the CPU at all 49 distances in the same time." Dopo la scelta del PI contare le parole da codice (150-250) e controllare con difflib che nessuna frase coincida con lo short paper.
- **Decisione o convenzione:** PI-S3
- **Fonte:** full_paper_LNBI.md riga 14; S2_P3_convenzione.csv; s1_speedups.csv; s1_extra_numbers.json; cooc_check_eval.json; righe_da_pianificare.csv R0566, R0568
- **Dipende da:** D-06; D-01; D-02; D-04; D-13; CONV; R0007; R0240; R0565; R0566; R0567; R0568; R0639; R0558; R0082
- **Nota:** Bozza di 246 parole contate da codice.
- **Modificata in arbitrato:** depends_on (vedi `arbitrati.csv`)

#### R0538 · S3 · P12 (novità e posizionamento) · riformulare
- **Bersaglio:** prosa (riga 34); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `However, most benchmarks report headline speedups without systematically examining (i) per-step performance variation, (ii) multi-GPU scaling behaviour and i...`
- **Valore:** (ii) multi-GPU scaling behaviour and its bottlenecks → (da rileggere, vedi fonte)
- **Istruzione:** Riga 34, 'However, most benchmarks report headline speedups without systematically examining (i) per-step performance variation, (ii) multi-GPU scaling behaviour ..., (iii) numerical concordance ..., and (iv) practical memory limits': la cornice e' contraddetta da lavori gia' citati (Nolet2022: tempi per step su 1-8 V100 e concordanza; Gardner2025: per step e ARI; Hu2025: 13M cellule su una A100; Dicks2026: per step e Tahoe-100M multi-GPU), e il punto (ii) non e' piu' un contributo (D-02). Il PI sceglie la nuova gap statement; proposta: "Earlier studies have reported per-step timings on one to eight GPUs with CPU-GPU concordance [@Nolet2022], accuracy-performance trade-offs on a single H100 [@Gardner2025], about 13 million replicated cells on one A100 [@Hu2025] and 100 million cells on multiple GPUs [@Dicks2026]. Less is known about how much of an end-to-end speedup comes from single steps such as differential expression testing, which resource limits a hybrid CPU-GPU pipeline on one node, and how GPU spatial analyses compare with a matched CPU reference." Coordinare con R0020 (riga 35) e con le domande delle righe 37-42.
- **Decisione o convenzione:** PI-S3
- **Fonte:** righe_da_pianificare.csv R0538 recomputed (tracks/E_work/pdf_txt); peer_review.md sezione 1 (tabella di confronto)
- **Dipende da:** D-02; D-01
- **Nota:** Cambia cio' che il capitolo dichiara come nuovo: scelta del PI (regola 6).

#### R0407 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 89); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `PCA and neighbour graph construction were distributed across N GPUs (N in {2, 4, 8}) via Dask workers, each with a 10 GB initial / 70 GB maximum RMM pool`
- **Valore:** PCA and neighbour graph construction were distributed across N GPUs (N in {2, 4, 8}) via Dask workers, each with a 10 GB initial / 70 GB maximum RMM pool. → 10GB/70GB
- **Istruzione:** Righe 85-90 (sottosezione Multi-GPU pipeline): sostituire titolo e quattro righe con "### Multi-GPU configuration" con il paragrafo: "At every dataset size we also ran a hybrid configuration with a Dask [@Rocklin2015] and Dask-CUDA [@RAPIDS2024] cluster of 2, 4 or 8 workers, one per GPU, each with a 10 GB initial / 70 GB maximum RMM pool. Data loading, QC, normalisation and HVG selection ran in Scanpy on the host CPU, and the matrix was then transferred to GPU 0 as a CuPy array. Because it was not converted to a Dask array, scaling, PCA, neighbour search, Leiden, UMAP and DE all ran on GPU 0, and the additional GPUs did not take part in the computation; rapids-singlecell 0.14.1 provides Dask-based routes for QC, normalisation, log1p, scaling and PCA that this configuration did not use. The runs with different numbers of GPUs ran on different nodes (Section Hardware). Results at 500k and 1.3M cells come only from this configuration." Prima di elencare i rami Dask della 0.14.1 rileggere il sorgente al tag v0.14.1 (_qc.py, _normalize.py, _scale.py, _pca.py): R0405 e R0045 concordano su QC, normalize_total, log1p, scale e PCA; l'HVG compare solo in R0045 e resta fuori. La frase finale su 500k e 1,3M dipende da R0044. Togliere le due figure multi-GPU e Amdahl è compito di S4 e della traccia T5 (D-02).
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0407 campo recomputed (pool 10GB/70GB confermati); id=R0405 campo recomputed (rami Dask 0.14.1); id=R0458 campo recomputed (cpu_steps)
- **Dipende da:** D-02; R0044; R0448; R0487
- **Assorbe:** R0045, R0047, R0241, R0348, R0370, R0404, R0405, R0406, R0458, R0644, R0676
- **Nota:** Primaria per tutto il blocco 85-90 (P3). Assorbe le righe che riguardano scaling su CPU, 'only PCA and neighbours', 329x e device 0.

#### R0465 · S3 · P4 (spatial) · riformulare
- **Bersaglio:** prosa (riga 122); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `The Visium HD 2 um dataset was subsampled to approximately 400,000 bins using the `--max-spots` flag so that the benchmark would fit within the RTX 4090's 24...`
- **Valore:** The Visium HD 2 um dataset was subsampled to approximately 400,000 bins using the `--max-spots` flag → 6.35%
- **Istruzione:** Scelta del PI: il sottocampione casuale tiene il 6.35% dei bin a 2 um, quindi grafo di Delaunay, Moran e Geary non descrivono la risoluzione nativa. Proposta raccomandata (nessun nuovo run): aggiungere a riga 122 "Random subsampling kept 6.35% of the bins, so the subsampled data have the bin density of a regular grid with a spacing of about 8 um; spatial statistics on this sample therefore do not describe the native 2 um resolution." e chiamare la piattaforma "Visium HD 2 um (random 400k-bin subsample)" in tabelle e figure (S5). Alternative per il PI: togliere la piattaforma 2 um, oppure un nuovo run su un ritaglio contiguo (fuori da D-01).
- **Decisione o convenzione:** PI-S3
- **Fonte:** righe_da_pianificare.csv id=R0465 campo recomputed (400,000/6,296,688)
- **Dipende da:** R0428
- **Nota:** Contestata in parte: 7,9 um non è la distanza media fra bin vicini; 2/sqrt(0,0635) = 7,9 um è il passo della griglia regolare di pari densità, mentre la distanza media al vicino più prossimo di un diradamento casuale è circa la metà (circa 4 um).

#### R0279 · S3 · P11 (ambiente e hardware) · riformulare
- **Bersaglio:** prosa (riga 162); registro: MISMATCH, major
- **Ancora (univoca nel .md):** `We attempted to downgrade the spatial container to an earlier RAPIDS release known to be driver-compatible (RAPIDS 25.02), but the spatial dependency stack (...`
- **Valore:** an earlier RAPIDS release known to be driver-compatible (RAPIDS 25.02) → RAPIDS 24.06
- **Istruzione:** Righe 162-163: il testo dice che un downgrade a RAPIDS 25.02 è fallito; la storia git documenta invece un container RAPIDS 24.06 / CUDA 12.2 'validated on DGX H100: CuPy, RMM, rapids-singlecell all PASS' (commit d65ff4d, 27/03/2026), poi riportato a 26.02 (446fc86). Scelta del PI fra: (a, raccomandata) togliere le righe 162-163 e lasciare solo la frase di R0451 "The GPU part of the spatial pipeline was run only on the workstation."; (b) scrivere "A RAPIDS 24.06 container passed basic GPU tests on the DGX in March 2026, but the spatial benchmark was not ported to it." citando i commit già letti nel registro (R0279: 524af6f, d65ff4d, 446fc86); sul server non si esegue git (regola 7 della specifica).
- **Decisione o convenzione:** PI-S3
- **Fonte:** righe_da_pianificare.csv id=R0279 campo recomputed (commit 524af6f, d65ff4d, 446fc86); id=R0452 campo recomputed (constraints.txt, SPATIAL.md righe 263-265)
- **Dipende da:** R0451
- **Assorbe:** R0073, R0452
- **Nota:** Cambia ciò che il capitolo afferma sul limite del DGX: L5. Le Limitazioni riga 432 (traccia T5) vanno allineate alla scelta.

#### R0498 · S3 · P10 (concordanza) · riformulare
- **Bersaglio:** prosa (riga 244); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `These concordance levels are consistent with the range of inter-method variation reported in mixture-control benchmarks of scRNA-seq analysis pipelines [@Tia...`
- **Valore:** interchangeable for biological interpretation → (da rileggere, vedi fonte)
- **Istruzione:** Proposta per il PI. Sostituire la frase a riga 244 ("These concordance levels are consistent with ... [@Tian2019] ... [@Duo2020], and support the conclusion that GPU and CPU pipelines are interchangeable for biological interpretation.") con: "At 10,000 cells the two pipelines therefore agreed closely. This does not establish interchangeability at atlas scale: from 50,000 cells upwards GPU Leiden labels varied across repeats with a fixed seed, and a comparison of Scanpy and RAPIDS on the 1.3-million-cell mouse brain data reported CPU-GPU ARI near 0.5 and concluded that the two are not interchangeable [@Gardner2025]." Togliere i confronti con Tian2019 e Duo2020 (confrontano metodi diversi, non due implementazioni dello stesso algoritmo).
- **Decisione o convenzione:** PI-S3
- **Fonte:** revisione_n2_log.csv id=R0498 campo recomputed; revisione_n2_log.csv id=R0540 campo recomputed (Gardner2025 pdf_txt righe 400-560); peer_review.md PoW-F (2-4 partizioni distinte da 50k in su)
- **Dipende da:** R0244
- **Assorbe:** R0130, R0540
- **Nota:** L5: cambia una conclusione presente anche in abstract (R0567, T1) e Discussione (R0594, R0693, T5). Primaria per R0130 e R0540. Se Tian2019/Duo2020 non restano citati altrove, verificarne l'uso in bib (T6).

#### R0580 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 418); registro: UNSUPPORTED, minor
- **Ancora (univoca nel .md):** `This step-level heterogeneity extends into multi-GPU scaling behaviour`
- **Valore:** This step-level heterogeneity extends into multi-GPU scaling behaviour. → (da rileggere, vedi fonte)
- **Istruzione:** Riga 418: togliere la frase 'This step-level heterogeneity extends into multi-GPU scaling behaviour.' (nessuno step è stato distribuito; D-02). Il paragrafo si apre con il testo di R0581.
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0580 campo recomputed
- **Dipende da:** R0581; D-02

#### R0581 · S3 · P3 (multi-GPU) · riformulare
- **Bersaglio:** prosa (riga 418); registro: MISMATCH, critical
- **Ancora (univoca nel .md):** `The relatively modest 12% improvement from 2 to 8 GPUs at 1.3M cells reflects a fundamental constraint imposed by pipeline structure: only PCA and neighbour ...`
- **Valore:** the remaining 95% of wall time → 17.23; 17.01; 148.99; 90.61
- **Istruzione:** Riga 418, per D-02: sostituire l'intero paragrafo (da 'This step-level heterogeneity extends into multi-GPU scaling behaviour.' a '...not as one 8xH100 supercomputer.') con un paragrafo su ciò che è stato misurato, senza Amdahl e senza la raccomandazione degli otto worker: "In our multi-GPU configuration the expression matrix stayed on one device, so PCA and neighbour search ran on a single GPU whatever the number of GPUs allocated (17.23 s with 2 GPUs and 17.01 s with 8 at 1.3M cells), and the additional GPUs did not take part in the computation. The 12% shorter runtime with 8 GPUs arose in CPU-side data loading (148.99 s versus 90.61 s), the 8-GPU jobs having run on a different node; multi-GPU scaling was therefore not measured in this study." Se il paragrafo multi-GPU dei Risultati (traccia T3) riporta già questi numeri, qui basta la prima frase senza cifre con il rimando ai Risultati. Le altre frasi del paragrafo si tolgono (R0580, R0582, R0583, R0584, R0585).
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0581 campo recomputed (tracks/F_work/f02_steps_2v8_1300000.csv, medie di 5 ripetizioni)
- **Dipende da:** D-02; CONV; R0368; R0353
- **Assorbe:** R0202, R0467, R0692, R0726
- **Nota:** Il 'remaining 95%' sparisce; se una frase lo tenesse, il valore è 96.1% (media) e non 95%. Medie di 5 ripetizioni (convenzione A).

#### R0582 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa; bib:Amdahl1967 (riga 418); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `This imbalance represents a classic manifestation of Amdahl's law [@Amdahl1967], where the non-parallelised fraction dominates overall speedup`
- **Valore:** classic manifestation of Amdahl's law [@Amdahl1967] → (da rileggere, vedi fonte)
- **Istruzione:** Riga 418: togliere la frase 'This imbalance represents a classic manifestation of Amdahl's law [@Amdahl1967], where the non-parallelised fraction dominates overall speedup.' (D-02: via la discussione su Amdahl; frazione parallela circa 0 al netto del data loading). Amdahl1967 è citato anche alla riga 232 (Risultati, T3): se anche lì cade per D-02, togliere la voce da cibb2026_references.bib.
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0582 campo recomputed (tracks/F_work/f02_amdahl.csv); peer_review.md PoW-A
- **Dipende da:** R0581; D-02; R0121
- **Assorbe:** R0203, R0659

#### R0583 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 418); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `Future frameworks could address this bottleneck by distributing preprocessing operations (e.g., chunked QC and normalisation across GPUs) and parallelising L...`
- **Valore:** would require substantial modifications to the existing Scanpy architecture → (da rileggere, vedi fonte)
- **Istruzione:** Riga 418: togliere la frase 'Future frameworks could address this bottleneck by distributing preprocessing operations (...) but such changes would require substantial modifications to the existing Scanpy architecture.'. Il fatto che rapids-singlecell 0.14.1 offrisse già rami Dask non usati va nelle Limitazioni (R0627), una sola volta.
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0583 campo recomputed
- **Dipende da:** R0581; R0627; D-02
- **Nota:** L'opzione esisteva nello stack usato e non è stata attivata.

#### R0584 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 418); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `A practical consequence for resource allocation follows from this constraint: because the marginal speedup of adding GPUs to a single run is only approximate...`
- **Valore:** near-linear throughput scaling → (da rileggere, vedi fonte)
- **Istruzione:** Riga 418: togliere la frase 'A practical consequence for resource allocation follows from this constraint: ... than as an eight-way worker for one analysis at a time.' (throughput concorrente non misurato; contesa di I/O osservata fra job concorrenti). Non sostituirla con la normalizzazione per costo della revisione: D-02 limita il paragrafo a ciò che è stato misurato.
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0584 campo recomputed
- **Dipende da:** R0581; D-02
- **Assorbe:** R0204

#### R0585 · S3 · P3 (multi-GPU) · togliere
- **Bersaglio:** prosa (riga 418); registro: UNSUPPORTED, major
- **Ancora (univoca nel .md):** `This is a non-obvious but important takeaway for groups operating shared GPU infrastructure: the capital-intensive DGX platform delivers its greatest return ...`
- **Valore:** cluster of eight H100 workstations → (da rileggere, vedi fonte)
- **Istruzione:** Riga 418: togliere la frase 'This is a non-obvious but important takeaway for groups operating shared GPU infrastructure: the capital-intensive DGX platform delivers its greatest return when treated as a cluster of eight H100 workstations, not as one 8xH100 supercomputer.' (nessuna misura di throughput, costo o ritorno; D-02).
- **Decisione o convenzione:** D-02
- **Fonte:** righe_da_pianificare.csv id=R0585 campo note
- **Dipende da:** R0581; D-02
- **Assorbe:** R0205

#### R0733 · S6 · PL (LaTeX e METEOR) · riformulare
- **Bersaglio:** trasversale (fuori dalla prosa); registro: info, major
- **Valore:** n.d. → 15 (13-17)
- **Istruzione:** Stima attuale 28-32 pagine LNCS (render typst, nessuna compilazione). Obiettivo D-03: circa 15 pagine, intervallo 13-17. In S6, dopo S3-S5: (1) verificare che siano tolte le parti decise (D-02: sezione multi-GPU, Figure 3-4, Amdahl; D-04: 'most rigorous'); (2) togliere le ridondanze del report: abstract e Conclusioni quasi identici, strumentazione della RAM spiegata cinque volte, Metodi ripetuti nei Risultati; (3) accorpare tabelle che ripetono figure. Applicare la copia di stile stile/full_paper_LNBI_style.md solo dopo le correzioni di sostanza. In S7 compilare il LaTeX e contare le pagine reali; se fuori da 13-17, tornare a S6. Abstract entro 150-250 parole.
- **Decisione o convenzione:** D-03
- **Fonte:** decisioni_D01_D13.txt D-03; revisione_n2_log.csv R0733; revisione_n2_report.md sezione 2 Minori e stile
- **Dipende da:** D-02;D-03;D-04;R0734
- **Modificata in arbitrato:** value_old (vedi `arbitrati.csv`)


# Sequenza di lavoro per dipendenza


## S3: correzioni di sostanza (190 voci)

1. Decisioni da registrare prima della prima voce che ne dipende: CONV, D-01, D-02, D-03, D-04, D-05, D-06, D-10, D-11, D-12, D-13, PI-S3.
   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: J01 (R0007, R0240, R0565, R0567, R0568, R0639, R0731); J02 (R0129, R0709); J03 (R0151, R0674); J04 (R0154, R0710); J05 (R0194, R0197); J06 (R0244, R0498); J07 (R0279, R0451); J08 (R0453, R0466); J09 (R0407, R0487); J10 (R0445, R0549).
2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): 68 righe (2, 3, 14, 22, 23, 28, 35, 37, 38, 39, 41, 44, 53, 61, 76, 78, 83, 87, 88, 94, 109, 110, 111, 115, 122, 149, 154, 155, 156, 157, 159, 160, 161, 162, 163, 165, 166, 173, 217, 223, 229, 231, 232, 240, 242, 250, 252, 260, 262, 265, 267, 304, 308, 321, 416, 418, 420, 422, 424, 426, 432, 436, 437, 438, 439, 440, 441, 455).
3. Voci isolate: 47.


## S4: figure 1-6 (11 voci)

1. Decisioni da registrare prima della prima voce che ne dipende: CONV, D-02.
   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: nessuno.
2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): 3 righe (166, 219, 254).
3. Voci isolate: 4.


## S5: integrazione dei risultati spatial (49 voci)

1. Decisioni da registrare prima della prima voce che ne dipende: CONV, D-01, D-11, D-13.
   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: nessuno.
2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): 14 righe (14, 149, 165, 166, 340, 346, 355, 379, 380, 398, 399, 428, 430, 440).
3. Voci isolate: 20.


## S6: taglio e stile (9 voci)

1. Decisioni da registrare prima della prima voce che ne dipende: D-02, D-03, D-04.
   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: nessuno.
2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): 19 righe (8, 12, 14, 22, 23, 110, 111, 161, 162, 163, 260, 262, 432, 436, 437, 438, 439, 440, 441).
3. Voci isolate: 3.


## S7: LaTeX, METEOR e verifica finale (10 voci)

1. Decisioni da registrare prima della prima voce che ne dipende: D-02, D-05.
   Gruppi di voci che dipendono l'una dall'altra, da eseguire nella stessa passata: nessuno.
2. Transazioni (righe del manoscritto toccate da più voci, da riscrivere in una sola passata): 5 righe (3, 8, 12, 14, 455).
3. Voci isolate: 6.


# Mappe

- Transazioni: `mappe/transazioni.csv` (81 righe del manoscritto).
- Altre occorrenze dei valori che cambiano: `mappe/occorrenze_valore.csv` (449 occorrenze, 0 da classificare come propagare, omografo o valore confermato).
- Conferme del registro che decadono (il registro della revisione n.2 è il log di verifica del testo): `mappe/pass_che_decadono.csv` (170 righe PASS).
- Dipendenze: `mappe/dipendenze.csv` (419 legami); voci da eseguire insieme: `mappe/gruppi_insieme.csv` (10 gruppi).
- Fonti e script: `mappe/fonti_e_script.csv` (71 percorsi, esistenza controllata sul server: sì).

# Cosa il piano non risolve

- Le scelte del PI elencate in testa: le voci relative descrivono le alternative e la raccomandazione, non il testo finale.
- I PoW della peer-review non eseguiti (H concordanza a tutte le dimensioni, I multi-GPU vero, J scaling dei thread CPU, K secondo dataset, L energia misurata, M Jaccard corretta, N e O spatial): restano proposte finché il PI non ne chiede l'esecuzione. I e N sono superati da D-02 e da S1.
- Le righe del registro non verificabili che richiedono file presenti solo sul cluster DGX (log SLURM, etichette per ripetizione, `sacct`): le voci `verificare-in-step` dicono cosa cercare; se il file non c'è, l'affermazione si indebolisce o si toglie.
- Lo short paper già distribuito (D-06): nessuna correzione.
- `manuscript/VERIFICATION_REPORT.txt` (7 aprile 2026, su `manuscript.md`) è superato dal registro della revisione n.2: in S7 si marca come superato, non si aggiorna.

# Cancelli di verifica finale (S7)

Scritti in modo raggiungibile:

1. Ogni voce primaria di `ledger.csv` ha una riga in `IMPL_diario.csv` con esito; nessuna voce `rimandato` senza step e motivo.
2. Per ogni valore superato elencato nelle trappole, la ricerca nel manoscritto restituisce solo le occorrenze marcate `omografo` o `valore-confermato` in `mappe/occorrenze_valore.csv` (il numero di quelle occorrenze, non zero).
3. Ogni numero del testo finale si rilegge da script dal file indicato nel diario (calcolo, ricevuta con md5, controllo deterministico).
4. Le righe PASS di `mappe/pass_che_decadono.csv` con esito `ridichiarare` o `rileggere-conclusione` sono ridichiarate (confermate o corrette) dopo le modifiche che le toccano; quelle `non-decade-omografo` no.
5. Il manifest dei risultati grezzi dà 0 differenze; il LaTeX compila; le pagine LNCS sono fra 13 e 17 (D-03).

# Arbitrati

`arbitrati.csv` raccoglie le correzioni alle voci decise dopo la scrittura (ancore manuali, fonti corrette, esiti cambiati), ciascuna con motivo e fonte. Il generatore le applica a ogni rigenerazione e le segnala nella voce («Modificata in arbitrato»). I ribaltamenti fra revisori sono in `arbitrati_revisione.md`.
