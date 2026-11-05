# Decisioni del PI (3 novembre 2026)

* [Nuovo riferimento CPU per lo spatial (D-01)](D-01.md) - Lo spatial si rifà con ogni ripetizione in un processo nuovo e con gli stessi gruppi di cellule per CPU e GPU negli step spaziali.
* [Multi-GPU ridotto a ciò che è stato misurato (D-02)](D-02.md) - La parte multi-GPU diventa un paragrafo: la matrice restava su una GPU e le schede aggiuntive non partecipavano al calcolo; nessun nuovo run sul DGX.
* [Lunghezza del capitolo: circa 15 pagine LNCS (D-03)](D-03.md) - Il capitolo punta a circa 15 pagine in formato Springer LNCS.
* [Espressione differenziale come confronto di tempi (D-04)](D-04.md) - L'espressione differenziale si presenta solo come confronto di tempi, senza dire che lo pseudo-bulk usato sia l'approccio statisticamente più rigoroso.
* [CUP corretto del progetto DARE (D-05)](D-05.md) - Il codice CUP del progetto DARE nei ringraziamenti è B53C22006440001; quello nel capitolo è un refuso.
* [Lo short paper è chiuso (D-06)](D-06.md) - Si lavora solo sul capitolo LNBI; lo short paper CIBB non si modifica più.
* [Si lavora solo sul server (D-07)](D-07.md) - Dal 3 novembre 2026 il repo di lavoro è il clone sul server lesexp-server; il clone sul Mac è fermo e non si aggiorna.
* [Il riferimento spatial gira a server libero, quando lo dice il PI (D-09)](D-09.md) - Il nuovo calcolo spatial parte solo in una finestra indicata dal PI, con i calcoli degli altri progetti sospesi.
* [Effetto del cambio di driver GPU: si misura (D-10)](D-10.md) - Il cambio di driver GPU fra marzo e oggi si quantifica confrontando i tempi GPU nuovi con quelli di marzo; se coincidono, nei Metodi basta una frase breve.
* [CPU dello spatial: DGX come riferimento, server come controllo (D-11)](D-11.md) - Il riferimento CPU dello spatial si misura sul nodo DGX del gruppo, riservato per intero, con 100 CPU come lo scRNA; la stessa misura sul server serve da controllo.
* [Co-occorrenza GPU: difetto riportato, esclusa dagli speedup a HD, verifica con rapids-singlecell 0.15.1 (D-13)](D-13.md) - La co-occorrenza GPU a Visium HD 8 µm (overflow in rapids-singlecell 0.14.1) si riporta come risultato, si toglie dagli speedup a Visium HD e si verifica la correzione della versione 0.15.1 con un calcolo di circa 20 minuti.

# Decisioni tecniche

* [Integrità dei risultati grezzi con un manifest md5 (D-08)](D-08.md) - I risultati grezzi si controllano con il manifest md5 del 3 novembre 2026, perché la maggior parte dei file non è tracciata da git.
* [Come gira il nuovo riferimento spatial (D-12)](D-12.md) - Scelte tecniche del calcolo spatial di S1: processi freddi, gruppi dal DGX, passo SLURM da 100 CPU, ramo separato, file grandi fuori da git.
* [Piano di implementazione generato da codice, con arbitrati (D-14)](D-14.md) - Il piano delle correzioni della revisione n.2 sta in manuscript/revisione_n2/piano/, si rigenera con tools/s2_mkplan.py dagli ingressi versionati e registra ogni correzione decisa dopo la scrittura in arbitrati.csv.
* [Correzioni di S3 preparate per regione e applicate da script (D-17)](D-17.md) - Le 190 voci di S3 si preparano per regione del manoscritto come file di modifiche (ancora, testo nuovo, ricevute dei numeri) e si applicano con un unico script che controlla ancore e sovrapposizioni e scrive il diario.

# Decisioni del PI (4 novembre 2026)

* [Convenzione unica sulle ripetizioni: media e SD di tutte e 5 (D-15)](D-15.md) - In tutto il capitolo, scRNA e spatial, i tempi sono media e SD campionaria delle 5 ripetizioni e lo speedup è il rapporto fra medie.
* [Vicini CPU a 1 thread: si dichiara e si misura (D-16)](D-16.md) - I Metodi dicono che la ricerca dei vicini CPU usava pynndescent con n_jobs = 1 (default di Scanpy); l'effetto si misura sul server libero confrontando n_jobs = 1 e 100.
* [Titolo e abstract nuovi del capitolo: opzione A (D-18)](D-18.md) - Il capitolo prende il titolo A e l'abstract A (247 parole) proposti nelle correzioni di sostanza (S3).
* [Scelte di contenuto di S3: approvate le 21 raccomandazioni (D-19)](D-19.md) - Il PI approva le raccomandazioni delle correzioni di sostanza (S3) per le 21 scelte diverse da titolo e abstract.
* [Scelte del PI per l'integrazione spatial (D-20)](D-20.md) - Speedup della sola co-occorrenza come informazione, totali completi a Visium HD 8 µm in Table 8 e Fig. 7, controllo con la CPU del server in una colonna di Table 8 e una frase.
* [Taglio a 15 pagine LNCS con un documento supplementare su Zenodo (D-21)](D-21.md) - Il capitolo resta a circa 15 pagine LNCS (13-17): testo principale con circa 3.000 parole di prosa, Tables 4 e 8, Figures 1, 5, 8 e 9; il resto in un documento supplementare archiviato su Zenodo con il repository.

# Decisioni tecniche (4 novembre 2026)

* [Citazioni di librerie e scheda DGX non aggiunte dopo il taglio (D-22)](D-22.md) - Le voci R0554 e R0549 rinviate da S3 si chiudono senza aggiungere citazioni.

# Decisioni tecniche (5 novembre 2026)

* [Sorgente LaTeX generato da script, figure copiate con il loro numero (D-23)](D-23.md) - Il .tex del capitolo e del supplemento si genera dal .md con tools/s7_md2lncs.py; le figure entrano come copie figN.pdf, mentre i file prodotti dagli script restano con il loro nome.
* [Correzioni del repository prima della release (D-24)](D-24.md) - Script di download spatial, script SLURM a 8 GPU, risultati principali del README, LEGENDS.md e vecchie copie delle figure del LaTeX allineati a ciò che è girato e al capitolo.

# Decisioni del PI (5 novembre 2026)

* [Repository pubblica pulita scRNA-DGX-benchmark con DOI Zenodo (D-25)](D-25.md) - Il codice, i risultati e il supplemento si pubblicano in una repository GitHub nuova e pulita, archiviata su Zenodo con DOI riservato; il repository di lavoro resta pubblico senza i PDF degli articoli citati.
* [ORCID, strumento di LLM nei ringraziamenti e supplemento anche su METEOR (D-26)](D-26.md) - ORCID del primo autore nell'intestazione, nome dello strumento di LLM nei ringraziamenti, supplemento caricato dal PI anche su METEOR oltre che nell'archivio Zenodo.
