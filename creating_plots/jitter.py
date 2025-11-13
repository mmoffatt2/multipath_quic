import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCHEDULERS = ["minrtt","wrr","redundant","predict"]

labels = []
jitters = []

for sched in SCHEDULERS:
    f = f"runs/{sched}/client_log.json"

    if not os.path.exists(f):
        print(f"Missing {f}, skipping")
        continue

    data = json.load(open(f))
    vals = []
    for e in data:
        if e["path"]=="A":
            vals.append(e["jitA"])
        elif e["path"]=="B":
            vals.append(e["jitB"])
        else:
            # ✅ redundant case: take min jitter of both paths
            if "jitA" in e and "jitB" in e:
                vals.append(min(e["jitA"], e["jitB"]))

    if vals:
        jitters.append(np.mean(vals))
        labels.append(sched)

plt.figure(figsize=(6,4))
plt.bar(labels, jitters)
plt.ylabel("Average Jitter (sec)")
plt.title("Client-side Jitter per Scheduler")
plt.tight_layout()
plt.savefig("plot_jitter_bar.png", dpi=200)
print("✅ saved plot_jitter_bar.png")
