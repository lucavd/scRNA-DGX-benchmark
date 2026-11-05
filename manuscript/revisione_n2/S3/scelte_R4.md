# Scelte del PI della regione R4 (Discussione, Conclusioni, parti finali, bibliografia)

Step S3, 4 novembre 2026. Manoscritto all'apertura: md5 4587032be8d2905007687e0bb50d848e. Ogni testo qui sotto è pronto da incollare; l'opzione raccomandata è già in `edits_R4.csv` con `scelta_pi` uguale al codice.

## DICKS: confronto con Dicks et al. 2026

**Domanda.** La Discussione deve confrontare i nostri risultati con Dicks et al. 2026 (articolo di rapids-singlecell, arXiv 2603.02402) nei tre punti in cui il loro lavoro limita le nostre affermazioni?

**Prove (passaggi letti in sessione nel testo estratto del PDF, `script_e_calcoli.zip: tracks/E_work/pdf_txt/2603.02402v1.txt`; metadati OpenAlex/arXiv nel pacchetto della revisione).**
- Sotto circa 50.000 cellule, scrivono, l'overhead di lancio dei kernel e dei trasferimenti può rendere la CPU comparabile o più veloce; il loro workflow di benchmark non comprende l'espressione differenziale. Da noi a 10.000 cellule la GPU è 12,0 volte più veloce, e il DE CPU vale il 54,9% del tempo CPU (`results/cpu_10000_r*`, `gpu_10000_r*`).
- Con Dask, rapids-singlecell ha analizzato i 100 milioni di cellule di Tahoe-100M su un nodo con 8 GPU B300 in meno di 20 minuti (preprocessing compreso). Nolet et al. 2022 avevano già un workflow multi-GPU su 8 V100 per 1,3 milioni di cellule.
- Harmony GPU su un embedding PCA di 11,4 milioni di cellule in meno di 25 s.

**Alternative.**
1. **A (raccomandata): tre confronti** (righe 416, 418, 424), nessuna frase su Harmony. Testo: `R4-002`, `R4-003`, `R4-006` così come sono in `edits_R4.csv`.
2. **B: nessun confronto nuovo con Dicks.** Si toglie la frase su Dicks alla riga 416, la parte su Dicks alla 418 e alla 424 (Nolet2022 e Hu2025 restano). Conseguenza: le affermazioni restano corrette ma il lettore non vede che il limite di capacità e l'assenza di overhead a 10.000 cellule dipendono dalla nostra pipeline.
   - Riga 416: `The fundamental constraint underlying our results is that GPU speedup is inherently operation-specific and highly dependent on the computational structure of each step. Normalisation (173-329x), an element-wise operation limited by memory bandwidth rather than by arithmetic, had the largest speedup at every size, and neighbour graph construction (44-88x) benefited strongly from the GPU. The CPU neighbour search, however, ran pynndescent with a single numba thread (Scanpy's default `n_jobs = 1`; Methods); on a separate server, 100 threads made it 1.16, 1.91 and 2.48 times faster at 10,000, 50,000 and 100,000 cells, so against a multi-threaded CPU search the neighbour speedup would shrink to about 76x, 32x and 18x, and at 100,000 cells (95% bootstrap interval 8.6-33.1x) it would fall below that of PCA (36.5x). In contrast, data loading was slower on the GPU at every size tested (0.76-0.85x), and Leiden at 10,000 cells was slower on the GPU only at the first resolution (0.36x, mean of five repeats), an effect of the first cuGraph call in the first repeat (1.70 s against a mean of 0.13 s in repeats 2-5); at resolutions 1.0 and 1.5 the GPU was faster (1.36x and 1.60x). For data loading, CUDA context initialisation and RMM pool allocation took place before the timer (Methods), so the timed GPU step comprised reading the h5ad file through CPU RAM and transferring the matrix to the device; its excess over the CPU (+0.10, +0.55 and +1.38 s at 10,000, 50,000 and 100,000 cells) grew with dataset size, which is consistent with reading and conversion costs rather than with a fixed overhead. In practice, the GPU advantage grew with dataset size, but even at the smallest size tested (10,000 cells) the GPU pipeline was 12.0-fold faster end to end, partly because CPU differential expression took 54.9% of the CPU time; we did not observe a size at which GPU overhead outweighed its benefit.`
   - Riga 418: `In our multi-GPU configuration the expression matrix stayed on one device, so PCA and neighbour search ran on a single GPU whatever the number of GPUs allocated, and the additional GPUs did not take part in the computation; the 12% shorter runtime with 8 GPUs at 1.3M cells came from CPU-side data loading, the 8-GPU jobs having run on a different node (Results). Multi-GPU scaling was therefore not measured in this study. Multi-GPU workflows built on Dask have been reported with RAPIDS on 8 V100 GPUs for 1.3 million cells [@Nolet2022].`
   - Riga 424: `In the memory-optimised pipeline we tested, GPU VRAM did not limit the number of cells; ScaleSC [@Hu2025] reaches larger datasets with chunked preprocessing, so the limit we observed belongs to the pipeline rather than to GPU analysis in general. At 11.9 million cells, the largest size completed with this pipeline, aggregate GPU VRAM remained flat at 48.8 GiB (7.6% of the 640 GiB total) while the recorded peak CPU RAM reached 535 GiB, 30% of the 1,800 GiB job allocation. The single run at 12.0M cells stopped with a timeout while the Dask cluster was shut down after neighbour search, so it does not show where the memory limit lies; the runs at 13.7M cells were killed by the system (signal 9) without an out-of-memory message, and our between-step sampling of the parent process cannot show whether transient allocations exceeded the SLURM cgroup limit (Table 6). Preprocessing that avoids dense or duplicated host-side intermediates, as in chunked approaches such as ScaleSC [@Hu2025], is the natural route to larger datasets. Our ScaleSC-inspired chunked variant indeed reduced aggregate VRAM by a factor of five (48.8 GiB to 9.6 GiB) and completed 12.0M cells (it was killed at 15.0M), while host RAM reached 862 GiB, which confirms that GPU memory was not the binding resource in this pipeline.`
3. **C: A più la frase su Harmony** alla fine della riga 432: `... which represent important directions for ongoing work; GPU Harmony has been reported on 11.4 million cells [@Dicks2026].` Conseguenza: un rimando in più fuori dal nostro disegno; costa spazio (D-03).

**Raccomandazione: A.** I tre punti sono quelli dove un revisore confronterebbe subito i numeri (la revisione n.2 lo ha fatto, `peer_review.md` sezione 1); Harmony non è nel nostro benchmark.

**Modifiche che ne dipendono:** R4-002, R4-003, R4-006, R4-008.

## CLOUD: paragrafo sul costo cloud (riga 420)

**Domanda.** Teniamo la frase sul costo di noleggio, con una fonte di prezzo datata, o la togliamo?

**Prove.** Il run da 7,3 minuti a 1,3M usa 8 GPU (`results/gpu8_1300000_r*`, media 435,18 s): a 2-4 USD per GPU-ora costa 1.93-3.87 USD così come allocato, non "well under one dollar"; una sola GPU a 1,3M non è stata misurata. Fonte di prezzo trovata: IntuitionLabs, "H100 Rental Prices Compared" (aggiornato a ottobre 2026). La pagina non e' coerente con se stessa: il titolo dice 1,49-6,98 USD per ora, mentre il testo elenca prezzi di listino on-demand da 1,99 USD (Runpod Community Cloud) a 12,29 USD (Azure) per H100-ora; Lambda 3,99 USD per GPU-ora su istanze da 8 GPU. Per questo l'opzione B cita solo la fascia 2-4 USD dei fornitori specializzati, non un intervallo complessivo. È una pagina web: non ha metadati verificabili su Crossref o OpenAlex (regola 5) e i prezzi cambiano di mese in mese.

**Alternative.**
1. **A (raccomandata): togliere la frase del costo**, tenere le tre frasi su ciò che è misurato (una GPU fino a 100.000 cellule; variante memory-optimised solo a 8 GPU; uso senza DGX come ipotesi). Testo: `R4-004`.
2. **B: tenerla con la fonte datata.** Testo della riga 420:
   `Because only one GPU computed in our multi-GPU configuration, we expect most of the benefit to be available on a single H100, although we did not run the hybrid pipeline with one GPU at 500k or 1.3M cells. The standard pipeline ran on a single H100 up to 100,000 cells, the largest single-GPU size we measured; the memory-optimised variant was run only with 8 GPUs. At on-demand prices of about USD 2 to 4 per H100-hour at specialist cloud providers in October 2026 [@IntuitionLabs2026], the 8-GPU run at 1.3M cells (7.3 min) would cost USD 1.93-3.87 as allocated; a single-GPU run at this size was not measured. If confirmed on a single GPU, this would make the approach usable without a DGX, for example on rented cloud GPUs.`
   Voce da aggiungere al `.bib`:
   ```
   @misc{IntuitionLabs2026,
     author    = {{IntuitionLabs}},
     title     = {{H100} Rental Prices Compared: \$1.49-\$6.98/hr Across 15+ Cloud Providers (2026)},
     year      = {2026},
     url       = {https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison},
     note      = {Last accessed 4 November 2026}
   }
   ```
   Ricevute: 1.93 e 3.87 = 8 x 435.1755 s / 3600 x 2 e x 4 USD (`results/gpu8_1300000_r1..5`, timings.total); 2 e 4 USD per H100-ora = fascia dei fornitori specializzati nella pagina (Lambda 3,99; Runpod 1,99-3,99), letta con una ricerca web il 4 novembre 2026. Conseguenza: una citazione non accademica, internamente incoerente (titolo contro testo), e un numero che invecchia.
3. **C: togliere tutto il paragrafo della riga 420.** `vecchio` = riga 420 intera, `nuovo` vuoto. Conseguenza: sparisce anche l'osservazione che il calcolo stava su una GPU, che i Risultati comunque riportano.

**Raccomandazione: A.** Il capitolo misura tempi, non costi (D-02, D-03); la fonte non è verificabile con i criteri della regola 5.

**Modifiche che ne dipendono:** R4-004.

## LLM: dichiarazione sull'uso di modelli linguistici (richiesta da Springer)

**Domanda.** Dove e con quali parole dichiariamo l'uso di assistenti basati su LLM?

**Prove.** Politica Springer Nature letta il 4 novembre 2026 (pagina "AI guidance for researchers, editors, reviewers"): gli LLM non sono autori; il loro uso va documentato nei Metodi (o equivalente) oppure, per gli autori di libri, nei ringraziamenti, nell'introduzione o nella prefazione. Il copy-editing assistito non va dichiarato. Un capitolo LNBI sta in un volume di atti. In questa revisione sono stati usati agenti basati su LLM per leggere il codice, ricalcolare i numeri e scrivere le correzioni.

**Alternative.**
1. **A (raccomandata): nei Ringraziamenti** (riga 451, `R4-015`): `The authors used a large language model-based assistant to check the analysis code against the text, to recompute reported values from the result files with scripts and to draft revisions of the text; the authors reviewed every change and take full responsibility for the content of this chapter.`
2. **B: nei Metodi** (regione R2), stessa frase come paragrafo "Use of AI tools". Conseguenza: più visibile; tocca la regione R2.
3. **C: nessuna dichiarazione.** Non conforme alla politica, dato l'uso effettivo.

**Raccomandazione: A**, con due controlli del PI: nome e versione dello strumento (Springer non li impone, ma aiutano) e se l'assistente è stato usato anche nella prima stesura.

**Modifiche che ne dipendono:** R4-015.

## POW: PoW della revisione non coperti da decisioni (H, J, K, L, M, O)

**Domanda.** Per ciascun PoW non eseguito, mettiamo una frase nelle Limitazioni (riga 432)?

| PoW | Cosa chiedeva | Già coperto da | Frase proposta se il PI la vuole | Raccomandazione |
|---|---|---|---|---|
| H | concordanza a tutte le dimensioni, ARI CPU-CPU/GPU-GPU | riga 422 (R0592, R0594) e frase esistente "Concordance analysis was performed at 10,000 cells; ..." | `Concordance was measured in a single run at 10,000 cells, separate from the timed repeats; at larger sizes we did not compare CPU and GPU labels.` (al posto della frase esistente) | nessuna frase nuova |
| J | scaling dei thread CPU | R0649 (frase sulla baseline, 32 contro 200 CPU) e D-16 (vicini a 1 thread, riga 416) | nessuna | nessuna frase nuova |
| K | secondo dataset | R0619 (un tessuto, un dataset; replica per concatenazione) | nessuna | nessuna frase nuova |
| L | energia misurata | nessuna frase del testo parla di energia; con CLOUD = A sparisce anche il costo | `We did not measure energy use, so the speedups refer to time to result only.` | nessuna frase (se CLOUD = B, aggiungerla) |
| M | Jaccard dei vicini senza la cella stessa | scelta di R3 sulla Jaccard (Risultati) | nessuna nelle Limitazioni | nessuna frase |
| O | componenti connesse a HD 2 µm | spatial, step S5 (riga 430) | nessuna in S3 | rinviato a S5 |

**Raccomandazione: nessuna frase nuova in S3**; L si aggiunge solo con CLOUD = B; O va a S5.

**Modifiche che ne dipendono:** R4-008.

## CLUSTER_ACK: formula di ringraziamento del cluster DGX

**Domanda.** Usiamo la formula ufficiale richiesta dal centro di calcolo?

**Prove.** La guida utente di CONVECS (`convecs.it/user-guide`, letta con una ricerca web il 4 novembre 2026) chiede, per gli articoli, la dicitura: "This work was supported in part by the high-performance computing infrastructure developed under the project "CONVECS", funded by the PR Veneto FESR 2021-2027 program, Priority 1 - Specific Objective 1.1 - Action 1.1.2" (lineette del sito sostituite dal trattino). La stessa pagina descrive la piattaforma UPSCALE con 5 DGX H100. Per UPSCALE da sola non ho trovato una formula distinta (pagina ASIT dell'Ateneo). Con D-11 anche il riferimento CPU dello spatial ha girato sul DGX.

**Alternative.**
1. **A (raccomandata):** frase esistente estesa (R0237, `R4-014`) più la formula CONVECS (`R4-015`).
2. **B:** solo la frase estesa di R0237, senza formula. Conseguenza: non rispetta la richiesta del centro.
3. **C:** solo la formula CONVECS. Conseguenza: si perde il nome UPSCALE e cosa ha girato sul cluster.

**Raccomandazione: A**; prima dell'invio una conferma con il referente di dipartimento (focus group HPC) che la formula valga anche per UPSCALE.

**Modifiche che ne dipendono:** R4-014, R4-015.

## REPO_DOI: tag, commit e DOI d'archivio del repo (Availability, righe 459-460)

**Domanda.** Nella sezione Availability citiamo una release con tag, commit e DOI d'archivio (per esempio Zenodo)?

**Prove.** Oggi il testo dà solo l'URL di GitHub (riga 460, uguale ai Metodi riga 170, voce della regione R2). Tag e DOI non esistono ancora: si creano al commit finale di S7. FAIR chiede un identificativo persistente.

**Alternative (testo per le righe 459-460, da completare in S7 con i valori veri; non c'è una modifica in `edits_R4.csv` perché i valori non esistono ancora).**
1. **A (raccomandata):** `All code, Dockerfiles, SLURM submission scripts, and benchmark result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX> (release <TAG>, commit <HASH>), archived at Zenodo (doi:<DOI>).`
2. **B:** solo tag e commit, senza DOI. Conseguenza: identificativo non persistente se il repo cambia.
3. **C:** come oggi, solo l'URL. Conseguenza: il lettore non sa quale versione del codice ha prodotto i numeri.

**Raccomandazione: A**, con la stessa forma nei Metodi riga 170 (regione R2). Da fare in S7 dopo il tag; il DOI Zenodo si ottiene collegando il repo GitHub a Zenodo e pubblicando la release.

**Modifiche che ne dipendono:** nessuna in questo step (testo da applicare in S7).

## Scelte di altre regioni che toccano R4

- **PADOVA (R1):** opzione raccomandata "University of Padova" ovunque; alla riga 455 cambia "University of Padua" (`R4-016`); con "Padua" cambia invece la riga 451 (`R4-015`) e la 455 tiene solo la correzione del CUP (D-05).
- **CIFRA (R1):** riga 436 (`R4-009`) con 8 GPU (7,3 min), il run a 2 GPU (8,2 min), la quota del Wilcoxon (93,5%) e lo speedup senza DE (7,9-9,2x). Va allineata all'abstract scelto.

## Variante della riga 418 con le cifre (se il paragrafo dei Risultati di R0352 non le riporta)

`In our multi-GPU configuration the expression matrix stayed on one device, so PCA and neighbour search ran on a single GPU whatever the number of GPUs allocated (17.23 s with 2 GPUs and 17.01 s with 8 at 1.3M cells), and the additional GPUs did not take part in the computation. The 12% shorter runtime with 8 GPUs arose in CPU-side data loading (148.99 s versus 90.61 s), in jobs that ran concurrently, the 8-GPU jobs on a different node; multi-GPU scaling was therefore not measured in this study. Multi-GPU workflows built on Dask have been reported with RAPIDS on 8 V100 GPUs for 1.3 million cells [@Nolet2022] and with rapids-singlecell on 8 B300 GPUs for 100 million cells [@Dicks2026].`

Ricevute: 17.23 e 17.01 = media r1-5 di pca + neighbors in `results/gpu2_1300000_r*` e `gpu8_1300000_r*` (17.229, 17.015; SD 0.73 e 0.28, differenza entro 2 SD); 148.99 e 90.61 = media r1-5 di data_loading (148.988, 90.609).
