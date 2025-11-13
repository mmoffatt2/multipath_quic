import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCHEDULERS = ["minrtt","wrr","redundant","predict"]

plt.figure(figsize=(7,4))

for sched in SCHEDULERS:
    f = f"runs/{sched}/client_log.json"
    if not os.path.exists(f):
        continue

    data = json.load(open(f))
    rtts = []
    for e in data:
        if e["path"]=="A":
            rtts.append(e["rttA"])
        elif e["path"]=="B":
            rtts.append(e["rttB"])
        else: # redundant
            rtts.append(min(e["rttA"], e["rttB"]))

    rtts = sorted(rtts)
    y = np.arange(len(rtts))/len(rtts)
    plt.plot(rtts, y, label=sched)

plt.xlabel("RTT (s)")
plt.ylabel("CDF")
plt.title("RTT CDF per Scheduler (client-estimated)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("plot_rtt_cdf.png", dpi=200)
print("✅ saved plot_rtt_cdf.png")
