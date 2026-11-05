> Revisione n.2 completata il 3 novembre 2026 su `full_paper_LNBI.md` (md5 4587032be8d2905007687e0bb50d848e, repo commit a4b9b9e).
> Leggi `revisione_n2/revisione_n2_report.md` e `revisione_n2/revisione_n2_log.csv` prima di modificare il manoscritto.

# Revisione n.2 del capitolo LNBI CIBB 2026

Esito: **non sottomettibile così com'è** (scadenza METEOR 10 novembre 2026).

Asserzioni verificate: 339 (736 righe di registro). Confermate 312 righe; non corrispondenti 213; più forti dei dati 147; non verificabili 55.

Bloccanti, ricalcolati a mano:
1. Titolo e abstract identici allo short paper (regola CIBB).
2. Prove multi-GPU: il calcolo gira su una sola scheda; il 12% fra 2 e 8 GPU viene dal caricamento dati.
3. Spatial: 51,6x e 3.272x dipendono da una CPU rallentata circa 50 volte dopo la prima ripetizione (con la prima: circa 7x e 67x).
4. Dataset: CELLxGENE Census, non il 10x E18; stress test oltre 3,44M su copie del dataset.
5. Bibliografia: Squidpy e SpatialData con autori inesistenti.

Decisioni del PI (3 novembre): (1) rifare il riferimento CPU dello spatial; (2) ridurre la parte multi-GPU a ciò che è stato misurato; (3) puntare a circa 15 pagine LNCS; (4) espressione differenziale come confronto di tempi; CUP corretto B53C22006440001.

Il lavoro prosegue in Claude Science: il prompt di partenza è `revisione_n2/PROMPT_claude_science.md`; per prima cosa la sessione crea la skill di progetto partendo da `revisione_n2/SKILL_bozza_lnbi_scrna_dgx.md`.

Contenuto di `revisione_n2/`:
- `revisione_n2_report.md`: riassunto «In breve», conformità, problemi raggruppati, peer-review, errori delle modifiche del 2 settembre.
- `revisione_n2_log.csv`: una riga per esito, con valore dichiarato, valore ricalcolato, fonte.
- `peer_review.md`: confronto con la letteratura, punti nascosti, PoW proposti ed eseguiti, frasi da riformulare.
- `stile/`: copia rivista per lo stile (da applicare dopo le correzioni di sostanza), tabella delle modifiche, segnalazioni.
- `tracce/`: esiti per traccia in JSON e inventario delle asserzioni.
- `script_e_calcoli.zip`: script e tabelle che riproducono ogni ricalcolo dai dati del repo.
- `PROMPT_claude_science.md`: prompt di partenza per Claude Science.
- `SKILL_bozza_lnbi_scrna_dgx.md`: bozza della skill di progetto, sul modello di mmm-session.
- `PROMPT_rerun_spatial.md`: brief dello step S1 (nuovo riferimento CPU spatial sulla workstation).
