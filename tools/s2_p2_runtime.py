
import os
os.environ["NUMBA_NUM_THREADS"]="8"
import numpy as np, scanpy as sc, numba, anndata as ad, scipy.sparse as sp
rng=np.random.default_rng(0)
X=sp.random(6000,3000,density=0.05,format="csr",random_state=0,data_rvs=lambda n: rng.poisson(3,n)+1).astype(np.float32)
a=ad.AnnData(X)
log=[("start",numba.get_num_threads())]
for rep in (1,2):
    b=a.copy()
    sc.pp.calculate_qc_metrics(b,inplace=True); sc.pp.filter_cells(b,min_genes=10); sc.pp.filter_genes(b,min_cells=3); log.append((f"r{rep} qc",numba.get_num_threads()))
    sc.pp.normalize_total(b,target_sum=1e4); sc.pp.log1p(b); log.append((f"r{rep} norm",numba.get_num_threads()))
    sc.pp.highly_variable_genes(b,n_top_genes=2000); b=b[:,b.var.highly_variable].copy(); log.append((f"r{rep} hvg",numba.get_num_threads()))
    sc.pp.scale(b,max_value=10); sc.tl.pca(b,n_comps=50,random_state=42); log.append((f"r{rep} pca",numba.get_num_threads()))
    sc.pp.neighbors(b,n_neighbors=15,n_pcs=50,random_state=42); log.append((f"r{rep} neighbors",numba.get_num_threads()))
    sc.tl.leiden(b,resolution=1.0,random_state=42,flavor="igraph",n_iterations=2,directed=False); log.append((f"r{rep} leiden",numba.get_num_threads()))
    sc.tl.umap(b,random_state=42); log.append((f"r{rep} umap",numba.get_num_threads()))
    sc.tl.rank_genes_groups(b,"leiden",method="wilcoxon"); log.append((f"r{rep} de",numba.get_num_threads()))
print("THREADS", log)
