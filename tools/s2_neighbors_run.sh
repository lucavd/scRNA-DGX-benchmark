#!/bin/bash
# S2 neighbour measurement: prep (not timed), then 3 sizes x n_jobs {1,100} x 5 repetitions,
# one fresh process each, with free-machine checks. Usage: bash tools/s2_neighbors_run.sh PY OUT
PY=$1; OUT=$2; DATA=${3:-data}; mkdir -p $OUT
snap() {  # prints JSON: load1, tctl, foreign processes over 50% CPU
python3 - "$@" <<'PYS'
import json, os, re, subprocess, sys
l1 = float(open("/proc/loadavg").read().split()[0])
t = subprocess.run("sensors", shell=True, capture_output=True, text=True).stdout
m = re.search(r"Tctl:\s*\+?([\d.]+)", t); tc = float(m.group(1)) if m else -1
ps = subprocess.run(["ps", "-eo", "pid,pcpu,args", "--no-headers"], capture_output=True, text=True).stdout.splitlines()
fo = [p.strip()[:100] for p in ps if float(p.split(None, 2)[1]) > 50 and "s2_neighbors" not in p and " ps -eo" not in p]
print(json.dumps({"load1": l1, "tctl": tc, "n_foreign": len(fo), "foreign": fo}))
PYS
}
for n in 10000 50000 100000; do $PY -B tools/s2_neighbors_prep.py --size $n --out $OUT --data-dir $DATA; done
# wait for a free machine: 3 checks 20 s apart with load1 <= 3 and no foreign process (max 30 min)
ok=0; for i in $(seq 1 90); do s=$(snap); l=$(echo $s | python3 -c "import json,sys;d=json.load(sys.stdin);print(int(d['load1']<=3 and d['n_foreign']==0))"); if [ "$l" = 1 ]; then ok=$((ok+1)); else ok=0; fi; [ $ok -ge 3 ] && break; sleep 20; done
[ $ok -ge 3 ] || { echo "NOT FREE"; snap; exit 3; }
for r in 1 2 3 4 5; do for n in 10000 50000 100000; do for nj in 1 100; do
  s0=$(snap); f=$(echo $s0 | python3 -c "import json,sys;print(json.load(sys.stdin)['n_foreign'])")
  if [ "$f" != 0 ]; then echo "FOREIGN before $n $nj $r: $s0"; exit 4; fi
  $PY -B tools/s2_neighbors_time.py --size $n --njobs $nj --rep $r --out $OUT
  s1=$(snap)
  python3 -c "import json,sys;json.dump({'size':$n,'n_jobs':$nj,'rep':$r,'start':json.loads(sys.argv[1]),'end':json.loads(sys.argv[2])},open('$OUT/snap_${n}_nj${nj}_r${r}.json','w'))" "$s0" "$s1"
done; done; done
python3 -B tools/s2_neighbors_eval.py $OUT results
