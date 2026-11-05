
import os
os.environ["NUMBA_NUM_THREADS"]="8"
import numpy as np, scanpy as sc, numba, anndata as ad, inspect
import pynndescent.pynndescent_ as P
print("settings.n_jobs", sc.settings.n_jobs)
seen=[]
orig=numba.set_num_threads
def spy(n): seen.append(("set",n)); return orig(n)
numba.set_num_threads=spy
oi=P.NNDescent.__init__
def init(self,*a,**k):
    seen.append(("NNDescent n_jobs",k.get("n_jobs"))); return oi(self,*a,**k)
P.NNDescent.__init__=init
import scanpy.neighbors as N
src=inspect.getsource(N)
i=src.find("4096"); print("THRESH", src[max(0,i-300):i+200].replace("\n"," | ") if i>0 else "no 4096")
for n in (12000,):
    rng=np.random.default_rng(0)
    a=ad.AnnData(rng.normal(size=(n,50)).astype(np.float32)); a.obsm["X_pca"]=a.X.copy()
    sc.pp.neighbors(a,n_neighbors=15,n_pcs=50,random_state=42)
    print(n, "calls:", seen, "after:", numba.get_num_threads()); seen.clear()
