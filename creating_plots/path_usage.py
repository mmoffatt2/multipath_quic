import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCHEDULERS = ["minrtt","wrr","redundant","predict"]

counts = {"A":[],"B":[],"A+B":[]}
labels = []

for sched in SCHEDULERS:
    f = f"runs/{sched}/client_log.json"
    if not os.path.exists(f):
        continue

    data = json.load(open(f))
    a = sum(1 for e in data if e.get("path")=="A")
    b = sum(1 for e in data if e.get("path")=="B")
    both = sum(1 for e in data if e.get("path")=="A+B")

    counts["A"].append(a)
    counts["B"].append(b)
    counts["A+B"].append(both)
    labels.append(sched)

plt.figure(figsize=(7,4))
x = range(len(labels))
plt.bar(x, counts["A"], label="Path A")
plt.bar(x, counts["B"], bottom=counts["A"], label="Path B")
plt.bar(x, counts["A+B"], bottom=[counts["A"][i]+counts["B"][i] for i in x], label="A+B")

plt.xticks(x, labels)
plt.ylabel("Packets Sent")
plt.title("Path Usage per Scheduler")
plt.legend()
plt.tight_layout()
plt.savefig("plot_path_usage.png", dpi=200)
print("✅ saved plot_path_usage.png")
