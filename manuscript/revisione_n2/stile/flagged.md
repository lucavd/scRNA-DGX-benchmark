# Track G: flagged, not changed (tier 3)

Line numbers refer to the original `full_paper_LNBI.md`. Each item is also in `tracks/G_findings.json` under the same identifier. Items G46-G48 were mechanical defects fixed in the copy and are listed so that they reach the original.

## Contradictions, arithmetic and claims beyond the design

**G01** (major, line 262). Stress-test failure at 12M: four incompatible attributions. Table 5 and the Results label the 12.0M failure 'Leiden OOM' ('failed at 12.0 million cells (Leiden out-of-memory, SLURM signal 9)'); the Results then state 'What the data do exclude is clustering as the CPU-side culprit'; Table 6 assigns '~50' GB to 'Leiden internal structures (executes on GPU; host delta at 11.9M < 1 GB)', contradicting its own row label; the Discussion states the cause as fact ('it occurred because transient memory spikes during individual preprocessing operations briefly multiplied the working set') although the kill happened during the Leiden step, after preprocessing had completed, and although the Results call the attribution unresolved. The abstract ('with CPU RAM as the binding constraint') and the Conclusions ('The principal scalability bottleneck is CPU-side preprocessing') rest on this attribution. The project script `scripts/benchmark_maxpower.py` (line 714) comments 'Leiden via cugraph (GPU), OOMs above ~12M cells'.

**G02** (major, line 368). Spatial time shares that cannot both hold. 'UMAP dominated the GPU pipeline time (92x speedup, but consuming 92% of the 97 s total GPU time)' and 'Spatial neighbours alone represented 57-73% of total GPU pipeline time on HD platforms' (with '~55 s on all HD platforms'). On HD 2 um, 0.92 x 97 = 89.2 s plus about 55 s exceeds the 97 s total; a 92x speedup on 89.2 s of GPU time implies about 8210 s of CPU UMAP, more than the 1042 s CPU total in Table 8.

**G03** (major, line 90). Where scaling ran in the multi-GPU pipeline. Line 88 lists scaling among the host-CPU steps ('data loading, QC, normalisation, HVG selection and scaling executed on the host CPU'); line 90 states 'Scaling, Leiden clustering, UMAP, and DE testing executed on a single GPU (device 0), as they operate on the reduced PCA embedding', and the Results breakdown lists 'transfer + scale + Leiden + UMAP + DE' as single-GPU operations. Scaling (step 5) precedes PCA (step 6), so it cannot operate on the PCA embedding.

**G04** (major, line 83). Data-loading mechanism contradicts the stated procedure. Methods: 'the RMM pool allocator was initialised to pre-reserve GPU VRAM ... a GPU warmup step was then executed to absorb CUDA context initialisation overhead before timing.' Results (line 223) and Discussion (line 416) attribute the slower GPU data loading to 'the fixed overhead of CUDA context initialisation and RMM pool allocation'.

**G05** (major, line 185). Non-monotonic sequence described as monotonic: 'The speedup increased monotonically with dataset size: 33.6x at 50k, 43.7x at 100k, 34.9x at 500k (2 GPU), and 119.6x at 1.3M (8 GPU)'. The value falls from 100k to 500k, and the sequence mixes 1-, 2- and 8-GPU configurations.

**G06** (major, line 416). Normalisation range and mechanism. Discussion: 'achieving speedups of 88-329x and 44-88x respectively, because they involve high arithmetic intensity'. Results report normalisation at 329x, 206x and 173x (10k-100k), and describe it as 'only element-wise division and logarithm', an operation of low arithmetic intensity; the same paragraph then explains the Leiden result through low arithmetic intensity and the roofline model.

**G07** (major, line 250). Text and caption disagree on CPU RAM growth: 'CPU RAM usage scaled approximately linearly with cell count' against the Fig. 6 caption 'CPU RAM grows super-linearly'. Table 4 gives a 89.5-fold RAM increase for a 130-fold cell increase overall, and a 3.6-fold increase for 2.6-fold more cells between 500k and 1.3M.

**G08** (major, line 252). Evidence for distributed execution. 'the aggregate peak VRAM at 1.3M cells with 8 GPUs (134.2 GB) exceeds the 80 GB capacity of any single H100 device; this working set could not have fit on one GPU alone'. Table 4 shows 106.5 GB aggregate at 10k cells with 8 GPUs, where the data are a few GB, so the aggregate tracks per-worker RMM pool reservation (Methods: 10 GB initial per worker) rather than the working set. 'as reported for some Dask-CUDA configurations' carries no citation. UMAP is described as 'implemented as single-GPU operations in cuGraph 26.2'. The paragraph also reports procedure (scheduler queries, a bug fix) inside Results.

**G09** (major, line 281). Two 'failure points' and a broken cross-reference. 'the failure point was identical (13.7M)' (line 264) and 'the failure point at scale is identical (13.7M, CPU-side scale step), so the KMeans rows are included here as valid ascending points on the runtime/memory curves' (line 281), while Table 5 places the Leiden failure at 12.0M. The cited Methods section ('see Section "Stress test: maximum capacity"') does not mention KMeans or its footprint. This justification paragraph sits in Results; it was left in place because of these issues.

**G10** (major, line 424). Chunked variant and the cell limit. Discussion: 'Our ScaleSC-inspired chunked variant ... reduced aggregate VRAM by a factor of five (49 GB to 10 GB) without improving the cell limit'. Results: 'This variant succeeded at 12.0 million cells (862 GB peak RAM, 10 GB aggregate VRAM, 156 min)', a size at which the memory-optimised pipeline failed. Abstract, Table 5 and Conclusions give 11.9M as the maximum.

**G11** (major, line 424). HVG extrapolation. 'with 2,000 HVGs this suggests 20M cells at 1,000 HVGs and 4M cells at 5,000 HVGs as linear-extrapolation operating points'. Linear scaling from 11.9M cells at 2,000 HVGs gives 23.8M and 4.76M; 20M and 4M correspond to a 10M baseline. Table 6 puts the dense scaled matrix at 96 GB of a 535 GB baseline, so the premise that the limit scales with cells x HVGs is not what the budget shows.

**G12** (major, line 115). DE design total does not close. 'We evaluated seven DE strategies in a factorial design crossing test type (Wilcoxon, t-test, pseudo-bulk) with GPU strategy (none, scatter-by-genes across 8 GPUs, chunk-and-stream on 1 GPU).' Three by three levels give 9 cells; Table 7 has 6 rows.

**G13** (major, line 308). Infeasibility of the CPU Wilcoxon baseline. 'a CPU Wilcoxon baseline at this scale was infeasible to measure (extrapolation from smaller subsamples places it above four hours)'. The same study ran the 1.3M CPU pipeline five times at about 14.5 h each; the extrapolation method is not described.

**G14** (major, line 115). Data provenance above 1.3M cells and the 'donor' unit. Methods describe only the 1.3M E18 dataset and its subsamples; the construction of the 3.4M-15M datasets is not stated, nor what a 'donor' is in 'summed raw counts by donor x cluster'. Gene counts differ ('1.3M x 39,182 genes' against '3.4 million cells and 41,000 genes'). Results state that aggregation 'reduced the analysis from 3.4 million individual cells to a few hundred pseudo-samples per cluster'.

**G15** (major, line 306). Correctness claims without a correctness measurement. Heading 'pseudo-bulk is fastest and most correct'; Discussion 'represents the optimal balance between computational efficiency and statistical rigour'; Conclusions 'simultaneously the fastest (44x vs t-test) and most statistically rigorous approach'. Only run time was measured, and the benchmarked pseudo-bulk applies a Wilcoxon test to log-CPM (Methods), whereas the Discussion names count-based models (DESeq2, edgeR) as the 'gold standard'.

**G16** (major, line 326). Speedup and resolution. Heading 'GPU speedup scales dramatically with platform resolution' and 'demonstrating that GPU acceleration becomes increasingly valuable as spatial resolution increases'. Table 8: HD 2 um, the highest resolution, has 10.8x against 51.6x at HD 8 um.

**G17** (major, line 405). Spatial memory described as modest. 'plateaued at 22.6 GB for both HD platforms (Table 8), well within the RTX 4090's 24 GB capacity' (94% of capacity) under the heading 'Memory usage is modest across spatial platforms', while Methods and the Fig. 7 caption state that HD 2 um was subsampled 'so that the benchmark would fit within the RTX 4090's 24 GB VRAM'. The extrapolation 'would fit comfortably within DGX H100 memory' at 6.3M bins and the Methods statement 'requires DGX-class resources' were not tested.

**G18** (major, line 420). Single-GPU and cost claims. 'the memory-optimised variant described here extends single-GPU feasibility to 1.3M cells and beyond' (the variant distributes PCA across all 8 GPUs; Table 4 reports no single-GPU run at 500k or 1.3M) and 'translates to well under one dollar of compute rental' (the 7.3 min were measured on 8 H100s, about 0.97 GPU-hours, USD 1.9-3.9 at the stated USD 2 to 4 per hour). The price range has no source.

**G19** (major, line 418). Multi-GPU paragraph. 'the remaining 95% of wall time is spent on inherently sequential CPU preprocessing' (Results: 75% + 21%, i.e. 96.2%, with the multi-GPU phase at 3.8%), described as 'a fundamental constraint imposed by pipeline structure', while the Limitations call the same fraction 'a property of the software stack ... rather than an intrinsic limit' and the CPU steps ran on 100 threads. 'yielding near-linear throughput scaling in the number of concurrent studies' was not measured, and 500k and 1.3M do not fit on one GPU with the standard pipeline.

**G20** (major, line 422). Attribution of CPU-GPU clustering differences. Results: 'reflects the inherent stochasticity of the Leiden algorithm ... rather than indicating any systematic bias'; Discussion: 'entirely consistent with the algorithm's inherent stochasticity' and 'Floating-point non-associativity ... contributes negligibly ..., as the dominant source of variation is the Leiden algorithm's non-deterministic vertex ordering', concluding that the pipelines are 'interchangeable'. Concordance comes from one repeat at 10k cells (`results/concordance_10000_r1.json`), with no within-implementation seed baseline, and the kNN graphs fed to Leiden overlap at a mean Jaccard of 0.930.

**G21** (major, line 399). Spatial Leiden backend and the 2 um divergence. Fig. 9 caption, Results and Discussion name 'leidenalg (CPU)', whereas `SPATIAL/scripts/benchmark_spatial_cpu.py` (lines 333-335) calls `sc.tl.leiden(..., flavor="igraph", n_iterations=2)`, as in the scRNA-seq pipeline; Methods do not state the spatial backend. 'is not specific to GPU versus CPU comparison; rather, it reflects the fundamental sensitivity of stochastic graph-partitioning algorithms' is not tested by any within-implementation comparison.

**G22** (major, line 428). Priority claim without support: 'is, to our knowledge, the largest GPU speedup reported for any spatial transcriptomics operation'. No comparison or citation is given.

**G23** (minor, line 428). Spatial autocorrelation range: Discussion 'speedups of 162-170x' against 162-163x in Results, Fig. 8 and Table 9.

**G24** (minor, line 262). Percentage and its base: '49 GB out of 640 GB (7.6%)'. 49/640 is 7.7%; 7.6% follows from 48.8 GB, the value given later in the same paragraph.

**G25** (minor, line 380). Strict inequality: 'exceeded 0.9995 in all cases' (Results) and 'exceeding 0.9995' (Conclusions), while Table 10 reports 0.9995 for Geary's C on HD 8 um; the abstract writes '>= 0.9995'.

**G26** (minor, line 398). Ratio rounding: 2,559/538 = 4.76, reported as '4.75x'.

**G27** (minor, line 215). Heading and text disagree: 'varies over two orders of magnitude' against 'ranging across nearly two orders of magnitude'; the reported per-step values run from 0.36x to 329x.

**G28** (minor, line 149). Declared metrics not reported: SVG Jaccard for 'N taking the values 50, 100, and 200', while Table 10 shows only top 50 and FDR < 0.05.

**G29** (minor, line 351). Table 9 caption says 'spatial-specific operations' but the table lists expression steps (PCA, normalisation, UMAP, HVG selection, neighbours, Leiden).

**G30** (minor, line 165). Repeats and dispersion conventions. 'Each benchmark configuration was repeated five times; we report mean +/- standard deviation.' The stress test, DE benchmark and concordance analysis have one result file per configuration in `results/`, and Tables 5 and 7 carry no SD. The SD type (sample or population) and whether the Table 4 peak-memory columns are means or maxima over repeats are not stated.

**G31** (minor, line 82). Thread-pool paragraph in Methods argues and contradicts itself: 'Only the pool corresponding to the BLAS library ... is actually active at runtime; the other variables are harmlessly ignored', after naming OpenMP (scikit-learn loops) and Numba (umap-learn) as backends that do not depend on the BLAS choice.

**G32** (minor, line 94). 'six concordance metrics, one for each major stage of the analysis pipeline': Table 2 assigns ARI and NMI to the same stage (Clustering), giving five stages.

**G33** (minor, line 111). Binary search and Table 5. 'We conducted a binary search from 3.4M to 13.7M cells', while Table 5 lists seven sizes, `results/` holds further sizes (1.7M, 8.5M, 9.4M, 9.8M, 10.0M to 11.8M), and 13.7M is called 'a separate test'. The selection rule for the table is not stated.

**G34** (minor, line 171). Reproducibility claim and a mutable tag: 'Docker image `lucavd/sc-benchmark:latest` ..., which pins the full package environment', and 'provide all code and containers for full reproducibility'. A `latest` tag does not identify an image.

**G35** (minor, line 231). 'a representative 8-GPU run at 1.3M cells (total 463.4 s)': Table 4 gives 435.2 +/- 16.2 s; the selection criterion is not stated.

**G36** (minor, line 242). Threshold introduced in Results only: 'exceeding the stringent threshold of rho > 0.97'. Table 2 and the Methods define no threshold.

**G37** (minor, line 267). Method described in Results: the sparse-scatter optimisation (line 265), the ScaleSC-inspired chunked variant ('we also implemented a third variant that performs HVG selection on per-gene running statistics') and the 'variant pipeline at 14M cells' have no Methods description.

**G38** (minor, line 14). 'three 10x Visium platforms' (abstract, Results) against 'two 10x Genomics public datasets' with Visium HD at two bin sizes (Methods); Conclusions 'delivers 51.6x end-to-end speedup on Visium HD' holds for 8 um only (2 um: 10.8x).

**G39** (minor, line 416). 'on small datasets the overhead of GPU operations may outweigh their benefits': at the smallest size tested, 10k cells, the end-to-end speedup was 12-fold.

**G40** (minor, line 428). 'identical rankings of spatially variable genes': the data show identical top-50 sets (Jaccard = 1.0) and 98.2-100% overlap at FDR < 0.05, not identical rankings.

**G41** (minor, line 426). Mechanisms without measurement: GPU DE 'is ultimately limited by the I/O cost of converting sparse matrices to dense gene chunks' and the Wilcoxon advantage 'reflects the fact that CuPy's `argsort` maps efficiently onto sparse data'. No profiling is reported.

**G42** (minor, line 54). Uncited generalisations: 'This dataset is the canonical large-scale single-cell benchmark' (Methods), 'most benchmarks report headline speedups without systematically examining' (Introduction), 'This challenges the common intuition that GPU memory availability limits GPU-accelerated analysis' (Discussion).

**G43** (minor, line 441). Stock closing sentence with a citation: 'These results provide practical guidance for the computational bioinformatics community as single-cell and spatial datasets grow toward the billion-cell and billion-bin scales [@Regev2017].' It repeats the abstract's closer; whether a 2017 source supports 'billion-bin' spatial scales needs checking.

**G44** (minor, line 12). Institution name in two forms: 'University of Padova' (affiliation 1, hardware, acknowledgements) and 'University of Padua, Padua' (affiliation 3, funding).

**G45** (minor, line 283). Table 6 baseline: 'a reconstruction that sums to the 535 GB recorded at the last successful run (11.9M cells)'; the rows sum to 536 GB and the dense matrix row is computed for 12M cells (96 GB) rather than 11.9M (95.2 GB).

## Rendering defects (fixed in the copy)

**G46** (major, line 101). Table 2 row breaks in rendering: '| PCA loading |rho| |' splits the cell, so the compiled table shows 'rho' as the definition and drops 'Mean absolute Spearman rho across first 10 PC loadings, accounting for sign flips' and its scope. Fixed in the copy (tier 1).

**G47** (major, line 379). Figure 9 is not rendered as a figure: the image line is followed directly by text (line 380), so pandoc treats it as an inline image and the caption is lost. Fixed in the copy (tier 1).

**G48** (minor, line 71). Twelve table cells contain '---', which pandoc renders as an em dash. Replaced in the copy (tier 1).

## Redundancy a reviewer would ask to shorten (LNBI chapter)

**G49** (info, line 14). Abstract and Conclusions repeat the same five results almost word for word (14.5 h to 7.3 min; 11.9M cells at 7.6% VRAM; 44x pseudo-bulk; 51.6x and 3,272x; 0.9995) and both close on 'practical guidance'. The 120x / 14.5-hour / 7.3-minute figure appears four times (abstract, Results, Discussion, Conclusions).

**G50** (info, line 258). The first Results paragraph on the stress test restates the Methods description of the memory-optimised pipeline ('This variant moves scaling to CPU (exploiting the 2 TB system RAM), distributes PCA across all 8 GPUs ...').

**G51** (info, line 111). The memory instrumentation (between-step, parent process only, lower bound) is explained in Methods, twice in Results, in the Table 6 caption and in the Limitations. After relocation the copy still explains it in the caption, the Discussion and the Limitations.

**G52** (info, line 162). The DGX driver story (driver 535.183.01, CUDA 12.2 cap, failed downgrade) is told in Methods and again in the Limitations.

**G53** (info, line 418). The 12% gain from 2 to 8 GPUs appears in Results, twice in one Discussion paragraph, and in the Conclusions; the last two sentences of that paragraph make the same point twice. The 75% CPU fraction and its remedy appear in both the multi-GPU Discussion paragraph and the Limitations.

**G54** (info, line 260). The 13.7M failure during scaling is stated four times in the same subsection (lines 260, 262, 264, 281).

## Language signals and typesetting

**G55** (info, line 414). Language signals, reported as properties of the text. Before editing: five marker words (comprehensive, leveraging, landscape three times); emphatic or scaffolding openers concentrated in the Discussion ('Perhaps most importantly', 'Critically', 'Related to this', 'A notable finding', 'This is a non-obvious but important takeaway', and a sentence announcing that results 'merit detailed discussion'); intensifiers (dramatically three times, impressive, fundamental four times, stringent); 'actually' four times; 'We note that' twice; formulaic closers in the abstract, the Introduction and the Conclusions. The cluster co-occurs with verification failures (G02, G05, G06, G10, G11, G23). Median sentence length is 26 words (Discussion 30) against the author's 16-21. Springer Nature asks authors to document any use of LLMs in the Methods; the authors may wish to consider that disclosure.

**G56** (info, line 14). ASCII stand-ins ('um', 'rho', '+/-', '>=', 'x') are used consistently in the Markdown and converted to symbols in the stale LaTeX; left unchanged in the copy, to be converted at typesetting.

