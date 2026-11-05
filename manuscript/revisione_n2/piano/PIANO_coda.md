
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
