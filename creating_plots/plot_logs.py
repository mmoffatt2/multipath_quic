import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

data = json.load(open("runs/predict/client_log.json"))
_times = [e["time"] - data[0]["time"] for e in data]
_paths = [e["path"] for e in data]

os.makedirs("plots", exist_ok=True)

plt.figure(figsize=(8,4))
plt.scatter(_times, _paths, s=10)
plt.xlabel("Time (s)")
plt.ylabel("Chosen Path")
plt.title("Predict Scheduler – Path Decisions Over Time")
plt.tight_layout()
plt.savefig("plots/plot_path_timeseries.png", dpi=200)
print("✅ saved plots/plot_path_timeseries.png")
