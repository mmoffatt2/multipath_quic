import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

SCHEDS = ["minrtt", "wrr", "redundant", "predict"]
BASE_DIR = "runs"
CHUNK_SIZE_BYTES = 500  # matches the client code


def compute_throughput(log):
    """Returns (times, throughputs) where throughput is bytes/sec over 1 second bins"""
    if len(log) < 2:
        return [], []

    # Convert timestamps into relative time (seconds from start)
    times = [entry["time"] for entry in log]
    t0 = times[0]
    rel = [t - t0 for t in times]

    # Bin into 0.01 sec windows to make a smoother curve
    bin_size = 0.01
    max_t = rel[-1]
    bins = int(max_t // bin_size) + 2
    throughput = [0] * bins

    for t in rel:
        idx = int(t // bin_size)
        throughput[idx] += CHUNK_SIZE_BYTES

    # Convert to bytes/sec (× 1/bin_size)
    throughput = [(b / bin_size) for b in throughput]
    btimes = [i * bin_size for i in range(bins)]

    return btimes, throughput


def main():
    plt.figure(figsize=(10, 5))

    for sched in SCHEDS:
        log_path = f"{BASE_DIR}/{sched}/client_log.json"
        if not os.path.exists(log_path):
            print(f"Missing {log_path}, skipping")
            continue

        with open(log_path) as f:
            log = json.load(f)

        times, thr = compute_throughput(log)
        if times:
            plt.plot(times, thr, label=sched)

    plt.title("Client Throughput Over Time")
    plt.xlabel("Time (sec)")
    plt.ylabel("Throughput (bytes/sec)")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig("throughput_timeseries.png")
    print("✅ Saved throughput_timeseries.png")


if __name__ == "__main__":
    main()
