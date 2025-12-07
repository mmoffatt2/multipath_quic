import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

SCHEDS = ["minrtt", "wrr", "redundant", "predict"]
BASE_DIR = "runs"


def extract_cwnd_data(log):
    """Extract congestion window data for both paths over time"""
    if len(log) < 2:
        return [], [], []

    # Convert timestamps into relative time (seconds from start)
    times = [entry["time"] for entry in log]
    t0 = times[0]
    rel = [t - t0 for t in times]

    # Extract cwnd values, filtering out None values
    cwndA = [entry.get("cwndA") for entry in log]
    cwndB = [entry.get("cwndB") for entry in log]

    return rel, cwndA, cwndB


def main():
    # Create figure with subplots for each scheduler
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, sched in enumerate(SCHEDS):
        log_path = f"{BASE_DIR}/{sched}/client_log.json"
        if not os.path.exists(log_path):
            print(f"Missing {log_path}, skipping")
            continue

        with open(log_path) as f:
            log = json.load(f)

        times, cwndA, cwndB = extract_cwnd_data(log)
        
        ax = axes[idx]
        if times:
            # Filter out None values for cleaner plotting
            valid_indices_A = [i for i, v in enumerate(cwndA) if v is not None]
            valid_indices_B = [i for i, v in enumerate(cwndB) if v is not None]
            
            if valid_indices_A:
                times_A = [times[i] for i in valid_indices_A]
                cwndA_valid = [cwndA[i] for i in valid_indices_A]
                ax.plot(times_A, cwndA_valid, label="Path A", alpha=0.7, marker='o', markersize=3)
            
            if valid_indices_B:
                times_B = [times[i] for i in valid_indices_B]
                cwndB_valid = [cwndB[i] for i in valid_indices_B]
                ax.plot(times_B, cwndB_valid, label="Path B", alpha=0.7, marker='s', markersize=3)

        ax.set_title(f"Congestion Window - {sched.upper()}")
        ax.set_xlabel("Time (sec)")
        ax.set_ylabel("Congestion Window (bytes)")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend()

    plt.tight_layout()
    plt.savefig("cwnd_comparison.png", dpi=150)
    print("✅ Saved cwnd_comparison.png")

    # Also create a single plot comparing all schedulers on same graph
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    for sched in SCHEDS:
        log_path = f"{BASE_DIR}/{sched}/client_log.json"
        if not os.path.exists(log_path):
            continue

        with open(log_path) as f:
            log = json.load(f)

        times, cwndA, cwndB = extract_cwnd_data(log)
        
        if times:
            # Filter out None values
            valid_indices_A = [i for i, v in enumerate(cwndA) if v is not None]
            valid_indices_B = [i for i, v in enumerate(cwndB) if v is not None]
            
            if valid_indices_A:
                times_A = [times[i] for i in valid_indices_A]
                cwndA_valid = [cwndA[i] for i in valid_indices_A]
                ax1.plot(times_A, cwndA_valid, label=sched, alpha=0.7)
            
            if valid_indices_B:
                times_B = [times[i] for i in valid_indices_B]
                cwndB_valid = [cwndB[i] for i in valid_indices_B]
                ax2.plot(times_B, cwndB_valid, label=sched, alpha=0.7)

    ax1.set_title("Congestion Window - Path A (All Schedulers)")
    ax1.set_xlabel("Time (sec)")
    ax1.set_ylabel("Congestion Window (bytes)")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend()

    ax2.set_title("Congestion Window - Path B (All Schedulers)")
    ax2.set_xlabel("Time (sec)")
    ax2.set_ylabel("Congestion Window (bytes)")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend()

    plt.tight_layout()
    plt.savefig("cwnd_all_schedulers.png", dpi=150)
    print("✅ Saved cwnd_all_schedulers.png")


if __name__ == "__main__":
    main()
