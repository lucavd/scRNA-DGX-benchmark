---
type: Report
title: "Revisione n.2 del capitolo LNBI CIBB 2026, prima della sottomissione"
description: "Verifica avversariale di numeri, metodi, figure e citazioni contro il codice e i dati del repo, peer-review sulla letteratura, stile e conformità alle regole CIBB, LNCS e METEOR."
status: draft
generated: {by: "revisione-n2/skill", at: "2026-11-03T12:00:00+01:00"}
sources:
  - id: ms
    resource: "manuscript/full_paper_LNBI.md (md5 4587032be8d2905007687e0bb50d848e)"
  - id: repo
    resource: "https://github.com/lucavd/2026.scRNA_DGX, commit a4b9b9e"
  - id: cibb
    resource: "Email CIBB 2026 General Chairs del 2 e del 23 ottobre 2026"
---

## In breve: il capitolo si può mandare così com'è?

**A cosa serviva.** Prima di sottomettere il capitolo a Springer abbiamo controllato ogni numero, tabella, figura e citazione contro il codice e i risultati salvati nel repository, abbiamo confrontato il lavoro con la letteratura e abbiamo verificato le regole degli organizzatori. Conta perché il capitolo passa una nuova revisione e resta come versione d'archivio del lavoro.

**Cosa abbiamo trovato.**

1. **Così com'è, il capitolo non è ammissibile: titolo e abstract sono identici a quelli dello short paper.**
   - Gli organizzatori chiedono un titolo e un abstract leggermente diversi e almeno un aspetto esteso rispetto allo short paper. Oggi le nove frasi dell'abstract coincidono tutte, e lo short paper riporta già tutti gli esperimenti.
   - Il titolo dice anche che lo spatial è stato fatto sul DGX, mentre è stato fatto sulla workstation con la RTX 4090.

2. **Le prove "multi-GPU" non hanno mai usato più di una GPU per il calcolo.**
   - Il codice passa la matrice alla PCA e alla ricerca dei vicini come array su una sola scheda, quindi le schede aggiuntive restano ferme. A 1,3 milioni di cellule PCA e vicini durano 17,2 secondi con 2 schede e 17,0 con 8.
   - Il 12% di differenza fra 2 e 8 schede viene tutto dal caricamento dei dati su CPU, che era più veloce sul nodo usato per il run a 8 schede (149 secondi contro 91). A 500 mila cellule i tempi sono identici. Fra 10 e 100 mila cellule, 2 schede sono più lente di una sola del 49-82%.
   - Cadono quindi la lettura "scaling sublineare per la legge di Amdahl", le figure dello scaling e della scomposizione multi-GPU, e il consiglio di usare il nodo come otto macchine indipendenti. Il 120x resta un tempo vero, ma è il tempo di una pipeline che calcola su una sola scheda.

3. **Le cifre spatial più forti dipendono da una CPU che dopo la prima ripetizione è diventata circa 50 volte più lenta.**
   - Sul Visium HD a 8 micron la co-occorrenza su CPU impiega 73 secondi nella prima ripetizione e circa 3.570 nelle quattro successive, con un risultato identico. Il paper scarta la prima come "riscaldamento" e tiene le lente.
   - Usando la prima ripetizione come riferimento CPU, lo speedup complessivo passa da 51,6 a circa 7 volte e quello della co-occorrenza da 3.272 a circa 67 volte. In più la CPU e la GPU calcolavano la co-occorrenza su 7 e su 3 gruppi di cellule: non era lo stesso lavoro.
   - L'abstract, le conclusioni e lo short paper già distribuito usano 51,6x e 3.272x.

4. **Il dataset single-cell non è quello dichiarato.**
   - Il paper dice di usare il dataset 10x di 1,3 milioni di cellule di cervello embrionale di topo. Il codice scarica invece cellule di cervello di topo da CELLxGENE Census e ne estrae 1,3 milioni a caso; il numero di geni dopo il controllo di qualità non è compatibile con il file 10x.
   - Lo stress test oltre 3,44 milioni di cellule usa copie esatte dello stesso dataset, cosa che il paper non dice. A 11,9 milioni il clustering trova quasi 140 mila gruppi, perché le copie si raggruppano fra loro.

5. **Ci sono altri errori di sostanza, ciascuno correggibile con una riscrittura.**
   - L'analisi pseudo-bulk somma valori già normalizzati e trasformati in logaritmo, non conteggi: non è "l'approccio statisticamente più rigoroso" che il testo dichiara.
   - Il 93,5% del tempo CPU a 1,3 milioni è il test di Wilcoxon per l'espressione differenziale; senza quel passo lo speedup è circa 9 volte. Il paper non lo dice.
   - Due voci di bibliografia (Squidpy e SpatialData) contengono nomi di autori che non esistono negli articoli reali.
   - La concordanza fra CPU e GPU è misurata solo a 10 mila cellule, mentre altri studi trovano un accordo dei cluster intorno a 0,5 a scale maggiori: la frase sull'intercambiabilità non regge.

**Cosa devi decidere.**

1. **Rifacciamo il riferimento CPU dello spatial? Consiglio di sì.** Ogni ripetizione in un processo nuovo e la co-occorrenza sugli stessi gruppi di cellule per CPU e GPU, sulla workstation. Servono circa tre ore di calcolo e diventa anche l'aspetto esteso richiesto dagli organizzatori.
   - Senza rifarlo resta una sola misura CPU valida per piattaforma: si possono riportare solo quelle, dichiarandolo, con cifre molto più basse.
   - Si può anche togliere lo spatial dal capitolo: il testo si accorcia molto, ma cambiano titolo e tesi.

2. **La parte multi-GPU la riduciamo a un paragrafo che dice cosa è stato misurato? Consiglio di sì.**
   - Togliamo le due figure e la discussione su Amdahl, e scriviamo che nella configurazione usata le schede aggiuntive non partecipavano al calcolo.
   - L'alternativa è rifare i run con una pipeline davvero distribuita: è un'estensione forte, ma servono modifiche al codice, tempo sul DGX e una validazione, e in sette giorni il rischio è alto.

3. **Puntiamo a circa 15 pagine Springer? Consiglio di sì.** Oggi il capitolo vale circa 30 pagine, e le correzioni tolgono comunque materiale. L'alternativa è tenerlo lungo, accettando il rischio che revisori o editor chiedano di tagliarlo.

**Comunque.** Correggiamo il dataset nei Metodi e nella bibliografia, dichiariamo la replicazione nello stress test, riformuliamo l'espressione differenziale come confronto di tempi, diciamo quanto pesa il test di Wilcoxon sul 120x, ripariamo le due voci bibliografiche, scriviamo titolo e abstract nuovi, rigeneriamo le figure con caratteri leggibili alla larghezza Springer e rigeneriamo il sorgente LaTeX dal testo corretto. Mi serve una tua conferma sul codice CUP del finanziamento: nel capitolo è diverso da quello dello short paper. La scadenza è il 10 novembre: si regge solo se le tre decisioni arrivano oggi o domani; altrimenti conviene chiedere agli organizzatori qualche giorno in più.

Appena decidi questi 3 punti, scrivo il piano di implementazione.

---

## 1. Conformità alle regole di sottomissione

Fonti: email CIBB 2026 del 2 ottobre (opportunità di pubblicazione) e del 23 ottobre (link METEOR, scadenza 10 novembre); guida METEOR per gli autori; classe llncs 2.26 nel repo.

| Requisito | Esito | Dettaglio |
|:--|:--|:--|
| Titolo leggermente diverso dallo short paper | **non rispettato** | Identico. |
| Abstract diverso dallo short paper | **non rispettato** | Identico, 246 parole (limite LNCS 150-250). |
| Stessa lista autori | rispettato | Vedovelli, Lanera, Sabbatini, Gregori in entrambi. |
| Almeno un aspetto esteso | **debole** | Lo short paper contiene già tutti gli esperimenti. Le nuove misure delle decisioni 1 e 2 possono costituire l'estensione. |
| Almeno 8 pagine LNCS | rispettato, con eccesso | Stima 28-32 pagine (9.715 parole, 10 tabelle, 9 figure). Nessun massimo dichiarato. |
| Formato LNCS, sorgente LaTeX o Word | **da rifare** | `lncs_latex/full_paper_LNBI.tex` è del 6 luglio, senza le modifiche del 2 settembre e senza l'ambiente `credits` per Acknowledgements e Disclosure of Interests. |
| Nomi dei file figura coerenti con la numerazione (METEOR) | **da correggere** | Le figure 2-6 usano `fig5`, `fig2`, `fig6`, `fig3`, `fig4`. |
| Testo alternativo delle figure (METEOR) | da fare in sottomissione | Assistente di METEOR, poi export Excel caricato con il manoscritto; controllo umano obbligatorio. |
| Figure leggibili e risoluzione | **da correggere** | 7 figure su 9 con caratteri sotto 6 punti a 12,2 cm; Fig. 1 a 291 dpi; Fig. 1, 2 e 6 illeggibili in scala di grigi. |
| Disclosure of Interests | da fare in sottomissione | La dichiarazione in METEOR sostituisce quella nel testo. |
| Contenuti di terzi | rispettato | Tutte le figure sono originali. |
| Disponibilità di codice e dati | rispettato | Il repo è pubblico e contiene codice, script SLURM e JSON; mancano gli script per le figure 7-9 e lo script delle figure 1-6 va in errore sui risultati attuali. |
| Finanziamento | **da confermare** | CUP B53C22006450001 nel capitolo, B53C22006440001 nello short paper e nel README. |

## 2. Verifica di numeri, metodi, figure e citazioni (fase 1)

Asserzioni inventariate: 339 (214 frasi con numeri, citazioni o affermazioni di discussione, 106 righe di tabella, 10 didascalie, 9 figure). Ogni asserzione ha almeno un esito; molte ne hanno più di uno perché sono state verificate da più punti di vista. Il registro completo è `revisione_n2_log.csv` (736 righe).

| Esito | Righe |
|:--|--:|
| Confermato dai dati (PASS) | 312 |
| Non corrisponde (MISMATCH) | 213 |
| Più forte di quanto i dati sostengano (UNSUPPORTED) | 147 |
| Non verificabile con i dati disponibili (UNVERIFIABLE) | 55 |
| Osservazione | 9 |

Le righe non confermate per gravità: 29 critiche, 201 maggiori, 145 minori, 49 informative. Molte sono lo stesso problema visto da più punti di vista: sotto sono raggruppate per problema. Ho ricalcolato personalmente i problemi da P1 a P9 (colonna `verificato_dal_capo` nel registro).

### Bloccanti

**P1. Titolo e abstract identici allo short paper.** Vedi sezione 1.

**P2. Dataset dichiarato sbagliato.** Metodi, riga 53: "10x Genomics 1.3-million mouse brain cell dataset (E18) [@Zheng2017], obtained as a pre-processed AnnData h5ad file from the RAPIDS single-cell examples repository". `scripts/download_data.py` scarica invece da CELLxGENE Census (versione 2025-11-08) le cellule primarie di cervello di topo con chimica 10x 3', e ne campiona 1.300.000 con `np.random.choice` e seme 42. Il commento nel codice spiega che 1,3 milioni serve "to match the original 10x Genomics benchmark dataset size". Geni dopo QC: 39.182 (`cpu_1300000_r1_results.json`), incompatibili con il file 10x. Conseguenze: Metodi, abstract, citazione Zheng2017, confronti con Nolet 2022 e Dicks 2026 "sullo stesso dataset".

**P3. Nessun calcolo multi-GPU.** `scripts/benchmark_multigpu.py` chiama `rsc.get.anndata_to_GPU(adata)` (matrice CuPy su GPU 0), avvia il cluster Dask-CUDA e poi chiama `rsc.pp.pca` e `rsc.pp.neighbors` sulla matrice CuPy: in rapids-singlecell 0.14.1 il ramo Dask della PCA si attiva solo con un Dask array. Tempi medi su 5 ripetizioni:

| Cellule | GPU | Totale (s) | Caricamento dati (s) | PCA (s) | Vicini (s) |
|--:|--:|--:|--:|--:|--:|
| 500k | 2 | 124,5 | 25,0 | 0,29 | 2,70 |
| 500k | 4 | 125,0 | 23,9 | 0,28 | 2,69 |
| 500k | 8 | 124,6 | 24,3 | 0,29 | 2,71 |
| 1,3M | 2 | 493,3 | 149,0 | 0,80 | 16,43 |
| 1,3M | 4 | 486,6 | 135,1 | 0,60 | 16,39 |
| 1,3M | 8 | 435,2 | 90,6 | 0,61 | 16,40 |

La differenza 2 contro 8 GPU a 1,3M (58,1 s) sta nel caricamento dati (58,4 s). I job a 1, 2 e 4 GPU sono girati in contemporanea su un nodo con driver 535.247.01, quello a 8 GPU su `poddgx02` con driver 535.183.01 (tracce A, D, F). Fra 10k e 100k, 2 GPU sono più lente di una (3,3 contro 4,9 s; 8,4 contro 14,7; 14,8 contro 26,9). I 134,2 GB di VRAM aggregata citati come prova della distribuzione sono i pool RMM da 10 GB degli otto worker inattivi. Frasi coinvolte: abstract, Metodi righe 85-90, Risultati righe 225-236 e 252, Discussione righe 414-418, Conclusioni riga 434, Figure 3 e 4.

**P4. Riferimento CPU spatial degradato dopo la prima ripetizione.** `SPATIAL/results`, Visium HD 8 um:

| Ripetizione | CPU totale (s) | CPU co-occorrenza (s) | GPU totale (s) | GPU co-occorrenza (s) |
|--:|--:|--:|--:|--:|
| 1 | 584,6 | 73,47 | 91,4 | 2,51 |
| 2 | 4.079,5 | 3.573,47 | 77,7 | 1,09 |
| 3 | 4.064,4 | 3.574,09 | 78,1 | 1,09 |
| 4 | 4.062,4 | 3.570,99 | 79,5 | 1,09 |
| 5 | 4.067,3 | 3.574,25 | 79,9 | 1,09 |

Le cinque matrici di co-occorrenza CPU sono identiche bit per bit. Anche Moran rallenta (35,7 contro circa 48 s). Ipotesi sul meccanismo, letta nel sorgente di Squidpy 1.8.1 ma non verificata a runtime (traccia B): `nhood_enrichment`, che gira dopo la co-occorrenza, chiama `numba.set_num_threads(1)` nel processo, e le ripetizioni successive girano nello stesso processo con un solo thread. Il rapporto 3.573/73,5 = 48,6 è coerente con questa ipotesi. Speedup secondo il riferimento CPU scelto:

| Grandezza | Paper (CPU r2-5) | CPU r1-5 | CPU r1 contro GPU r2-5 | r1 contro r1 |
|:--|--:|--:|--:|--:|
| Totale HD 8 um | 51,6x | 41,5x | 7,4x | 6,4x |
| Co-occorrenza HD 8 um | 3.272x (3.271,5x esatto) | 2.088x | 67x | 29x |

In più la co-occorrenza CPU lavora su 7 cluster e quella GPU su 3 (matrici 7x7x49 contro 3x3x49), quindi i due tempi non misurano lo stesso calcolo; per lo stesso motivo la concordanza della co-occorrenza descritta nei Metodi non è mai stata calcolata (`shape_mismatch`).

**P5. Due voci bibliografiche con autori inesistenti.** Confronto con OpenAlex:
- Palla2022 (Squidpy): "Holber" è Holmberg; "Pegno, Mohammad Nofallah" non esiste; mancano Lotfollahi e Richter.
- Marconato2024 (SpatialData): Yaber, Chierici, Puente-Lelievre, Nabavi e Rattray non sono fra i 22 autori reali.
La stessa bibliografia è nello short paper.

### Maggiori

**P6. Stress test su dati replicati, non dichiarato.** `benchmark_maxpower.py`, funzione `resize_dataset`: oltre 3.436.470 cellule il dataset viene concatenato con se stesso (`anndata.concat`). A 11,9M Leiden trova 135.710, 142.959 e 147.154 cluster. Il salto di 302 GB fra fine caricamento e inizio QC, che il testo del 2 settembre chiama "non attribuito", è questa replicazione, eseguita fuori dagli step cronometrati. Table 5 dice ancora "Leiden OOM" mentre il testo dichiara l'attribuzione irrisolta. Le componenti di Table 6 non tornano con il codice (traccia A: una sola copia sparsa di circa 420 GiB).

**P7. Espressione differenziale.** In `test_de_benchmark.py` `adata.raw` viene assegnato dopo `normalize_total` e `log1p`: lo pseudo-bulk somma valori log-normalizzati, poi li normalizza a CPM e applica di nuovo il logaritmo, e confronta i cluster con un Wilcoxon. Il commento del codice parla di "raw counts". Il Wilcoxon GPU è scritto a mano senza correzione per i pareggi e senza p-value (traccia D). Il 3-7x è contro il t-test CPU, non a parità di test. Il disegno "fattoriale" ha 6 righe, non 7 strategie.

**P8. Cosa produce il 120x.** A 1,3M il Wilcoxon di Scanpy occupa il 93,5% del tempo CPU; escludendolo lo speedup è 9,2x con 8 GPU e 7,9x con 2. Dicks et al. 2026 riportano circa 110x su una sola H200 sullo stesso tipo di dataset, senza DE e senza I/O: il confronto manca.

**P9. Ripetizione 1 trattata in modo opposto.** Nello scRNA la media include la ripetizione 1, che è un vero riscaldamento: normalizzazione a 10k 329x con r1, 115x senza (CPU r1 1,749 s contro 0,098 s); Leiden a 10k 0,36x con r1, 1,12x senza. Nello spatial la ripetizione 1 viene esclusa, ma lì la CPU r1 è la più veloce.

**P10. Concordanza.** Misurata solo a 10k, su un run dell'11 marzo diverso dai run del benchmark (CPU 40/45 cluster contro 41/46). Da 50k in su le etichette Leiden GPU cambiano fra ripetizioni con lo stesso seme. Gardner 2025 trova ARI CPU-GPU intorno a 0,45-0,55 e conclude che i due percorsi "are not interchangeable"; Nolet 2022 riporta ARI 0,54 a 1,3M. Il capitolo cita Gardner solo per il suo limite a una GPU. La Jaccard dei vicini ha un tetto di 0,9375 per costruzione: lo 0,930 non è effetto della virgola mobile. Leiden CPU usa `n_iterations=2`, quella GPU il default: i parametri non sono identici come dice Table 1.

**P11. Ambiente.** Il nodo non era dedicato (due driver, job contemporanei, 16, 32, 56, 200 o 100 CPU allocate a seconda della configurazione). La workstation spatial riporta 128 CPU e driver 580.126.09, non 100 core e 550.x. Il dataset Visium HD scaricato dallo script è il "Tiny 3'" e non l'FFPE descritto. Il downgrade del container: il paper dice che un tentativo con RAPIDS 25.02 è fallito; la storia git mostra un container RAPIDS 24.06 / CUDA 12.2 "validated on DGX H100: CuPy, RMM, rapids-singlecell all PASS" il 27 marzo (commit d65ff4d), poi annullato lo stesso giorno per lo scRNA. La concordanza spatial è calcolata sui 2.000 HVG, non su tutti i geni. Nella Discussione UMAP occupa "il 92%" del tempo GPU su HD 2 um; i dati danno 9,3%.

**P12. Novità e posizionamento.** Nolet 2022 aveva già 1-8 V100 su un dataset da 1,3M cellule con preprocessing distribuito; Dicks 2026 elabora 100 milioni di cellule con Dask su 8 B300; ScaleSC elabora 13 milioni di cellule su una A100. "11,9M su un DGX, limite CPU RAM" è una proprietà della pipeline scelta. Va detto.

**P13. Affermazioni della Discussione oltre i dati.** "well under one dollar" (con 8 GPU il costo è 1,9-3,9 USD alle tariffe citate); "a single H100 captures nearly all the benefit" (a 1,3M una GPU sola non è stata misurata: la pipeline standard non entra in 80 GB); "largest GPU speedup reported for any spatial operation"; estrapolazione 20M e 4M cellule che non deriva da nessun modello (23,8M e 4,76M, oppure 13,1M e 9,4M); "without improving the cell limit" (la variante chunked è arrivata a 12,0M); normalizzazione ad "alta intensità aritmetica" (è un'operazione element-wise, limitata dalla banda di memoria).

**P14. Figure.** Fig. 4: la fase multi-GPU ha zero pixel; la barra CPU è tutta "preprocessing". Fig. 6: VRAM aggregata confrontata con il limite di 80 GB per scheda. Fig. 3: a 500k e 1,3M mancano i punti a 1 GPU. Fig. 2: domina UMAP, non i vicini. Leggibilità e risoluzione in sezione 1. Nessuno script genera le figure 7-9.

### Minori e stile
Arrotondamenti (Table 5 10,3M: 91 invece di 92 min; Table 7: 127, 1.655, 1.649 invece di 128, 1.656, 1.650; 43,9x invece di 43,7x), 3.272x invece di 3.271x, variante chunked 131,5 min e non 156, 34 coppie e non 30 sopra 0,97, normalizzazione 173-329x e non 88-329x. Dettaglio nel registro.

Revisione di stile secondo la skill dell'autore: 23 correzioni meccaniche e 71 riscritture di frase applicate in una copia (`stile/full_paper_LNBI_style.md`, numeri e citazioni invariati, da 9.715 a 9.177 parole), 56 segnalazioni di sostanza. Le principali ridondanze: abstract e conclusioni quasi identici; la strumentazione della RAM spiegata cinque volte; Metodi ripetuti nei Risultati. La copia corregge anche tre difetti di resa dell'originale (riga di Table 2 spezzata, Fig. 9 non resa come figura, celle "---" rese come lineette). Va applicata solo dopo le correzioni di sostanza, perché molte frasi cambieranno.

## 3. Peer-review sulla letteratura (fase 2)

Il testo completo, con la tabella di confronto, i 15 punti che un revisore chiederebbe, i 15 PoW proposti e i risultati dei 7 eseguiti, è in `peer_review.md`. Sintesi dei PoW eseguiti sui dati del repo:

| Analisi | Risultato | Cosa cambia |
|:--|:--|:--|
| Frazione parallela secondo Amdahl, 2/4/8 GPU | circa 0 al netto del caricamento dati | la sezione multi-GPU va riscritta |
| Sensibilità dello spatial alla ripetizione 1 | 51,6x diventa 41,5x, 7,4x o 6,4x | le cifre di testa vanno rifatte |
| Speedup con e senza DE | 9,2x senza DE a 1,3M | il 120x va spiegato |
| Convenzione sulla ripetizione 1 nello scRNA | 10k: 12,0x con r1, 14,0x senza | convenzione da uniformare |
| Costo cloud (prezzi dichiarati come ipotesi) | 2 GPU 3-4 volte più efficienti di 8 per costo a 1,3M | frase sul costo da rifare |
| Determinismo GPU | 2-4 partizioni diverse su 5 run da 50k in su | concordanza da ridimensionare |
| Tempo non cronometrato | rilevante a N piccoli (1 GPU 10k: 8,2 s di intervallo contro 2,5 cronometrati) | da dichiarare |

## 4. Errori introdotti o rafforzati nelle modifiche del 2 settembre

Nelle modifiche fatte durante la preparazione della talk ho scritto o confermato quattro affermazioni che questa revisione smentisce:

1. Metodi, riga 88: "within that path only PCA and neighbour graph construction had distributed GPU implementations usable for the pipeline as configured here". Falso due volte: rapids-singlecell 0.14.1 aveva rami Dask anche per QC, normalizzazione, log1p e scaling, e PCA e vicini non erano distribuiti nemmeno loro.
2. Note della talk: "two GPUs already give 105-fold ... and the other six buy thirteen percent". Il 13% non viene dalle GPU ma dal caricamento dati su un nodo diverso.
3. Risultati e Table 6: il salto di 302 GB "that belongs to no timed step", con il duplicato di `adata.raw` come sospetto principale. Il numero è giusto; la causa è la replicazione del dataset.
4. Limitations: "the container could not be downgraded to a driver-compatible RAPIDS release". Ho ripreso la frase dai Metodi senza controllare la storia git, che documenta un downgrade riuscito.

Tutte e quattro vanno corrette insieme ai problemi P3, P6 e P11.

## 5. Cosa non è stato verificato

- 55 asserzioni restano non verificabili con i soli dati del repo: soprattutto valori che dipendono da file sul cluster (etichette dei cluster per ripetizione, log SLURM, `sacct`), due citazioni di cui non si è potuto leggere il testo (Hubert 1985, Soneson 2018) e la causa esatta del rallentamento della CPU spatial.
- Il numero di pagine LNCS è una stima: la compilazione LaTeX non è stata eseguita.
- Lo short paper già distribuito agli atti digitali della conferenza contiene gli stessi errori P2-P5. Se e come avvisare gli organizzatori è una scelta tua.

## Appendice: da dove vengono i numeri del riassunto

| Frase del riassunto | Fonte | Valore letto |
|:--|:--|:--|
| Titolo e abstract identici | `manuscript_short_cameraready.md` contro `full_paper_LNBI.md`, confronto per frase | 9 frasi su 9 identiche, 246 parole |
| PCA e vicini 17,2 contro 17,0 s | `results/gpu{2,8}_1300000_r1-5`, media di `timings.pca + timings.neighbors` | 17,23; 17,01 |
| Caricamento 149 contro 91 s | `timings.data_loading`, stessi file | 148,99; 90,61 |
| 500k identici | `results/gpu{2,4,8}_500000_*`, `timings.total` | 124,5; 125,0; 124,6 |
| 2 GPU più lente del 49-82% | `results/gpu_{10000,50000,100000}` contro `gpu2_*`, `timings.total` | +49%, +75%, +82% |
| Co-occorrenza 73 contro circa 3.570 s, risultato identico | `SPATIAL/results/spatial_cpu_visium_hd_square_008um_r1-5`, `timings.co_occurrence`; `.npy` confrontati con `np.array_equal` | 73,47; 3.570,99-3.574,25; identici |
| 51,6 diventa circa 7 | CPU r1 `timings.total` 584,6 / media GPU r2-5 78,8 | 7,4 |
| 3.272 diventa circa 67 | 73,47 / 1,09 | 67 |
| 7 e 3 gruppi | forma degli `.npy` CPU e GPU r2 | (7,7,49); (3,3,49) |
| CELLxGENE Census | `scripts/download_data.py`, righe 2-5 e 27-33 | versione 2025-11-08, 1.300.000 cellule |
| Geni dopo QC | `results/cpu_1300000_r1_results.json`, `results_summary.n_genes_after_qc` | 39.182 |
| Copie esatte oltre 3,44 milioni; quasi 140 mila gruppi | `scripts/benchmark_maxpower.py`, `resize_dataset`; `results/maxpower_11900000_8gpu_results.json`, `n_clusters_*` | 135.710; 142.959; 147.154 |
| Pseudo-bulk su valori log | `scripts/test_de_benchmark.py`, righe 132-138 e 653-711 | `raw` assegnato dopo `log1p` |
| 93,5% e circa 9 volte | `results/cpu_1300000_*` e `gpu8_1300000_*`, `timings.de_testing` e `timings.total` | 93,5%; 9,2x |
| Autori inesistenti | OpenAlex `works/doi:10.1038/s41592-021-01358-2` e `doi:10.1038/s41592-024-02212-x` contro il .bib | vedi P5 |
| Accordo dei cluster intorno a 0,5 | Gardner 2025 (PDF nel repo), letto dalla traccia F | ARI mediana 0,45-0,55 |
| Circa 30 pagine | stima da render typst (20 pagine letter) per rapporto di area 1,62 | 28-32 |
| CUP diverso | `full_paper_LNBI.md` riga 455; `manuscript_short_cameraready.md` riga 138 | ...450001; ...440001 |
