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
