import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

SCHEDS = ["minrtt", "wrr", "redundant", "predict"]
BASE_DIR = "runs"
CHUNK_SIZE_BYTES = 500  # matches the client code
COLORS = {
    "minrtt": "#2E86AB",      # Blue
    "wrr": "#A23B72",         # Purple
    "redundant": "#F18F01",   # Orange
    "predict": "#06A77D"      # Green
}


def moving_average(data, window_size):
    """Apply moving average smoothing"""
    if len(data) < window_size:
        return data
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')


def compute_throughput(log):
    """Returns (times, throughputs) where throughput is Kbps over time bins"""
    if len(log) < 2:
        return [], [], 0

    # Convert timestamps into relative time (seconds from start)
    times = [entry["time"] for entry in log]
    t0 = times[0]
    rel = [t - t0 for t in times]

    # Bin into 0.05 sec windows for better visualization
    bin_size = 0.05
    max_t = rel[-1]
    bins = int(max_t // bin_size) + 2
    throughput = [0] * bins

    for t in rel:
        idx = int(t // bin_size)
        if idx < len(throughput):
            throughput[idx] += CHUNK_SIZE_BYTES

    # Convert to Kbps: bytes/sec * 8 bits/byte / 1,000
    throughput_kbps = [(b / bin_size * 8 / 1_000) for b in throughput]
    btimes = [i * bin_size for i in range(bins)]
    
    # Calculate average throughput
    total_bytes = len(log) * CHUNK_SIZE_BYTES
    total_time = max_t
    avg_kbps = (total_bytes / total_time * 8 / 1_000) if total_time > 0 else 0

    return btimes, throughput_kbps, avg_kbps


def main():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    stats = {}
    
    # Plot 1: Throughput over time
    for sched in SCHEDS:
        log_path = f"{BASE_DIR}/{sched}/client_log.json"
        if not os.path.exists(log_path):
            print(f"Missing {log_path}, skipping")
            continue

        with open(log_path) as f:
            log = json.load(f)

        times, thr, avg_kbps = compute_throughput(log)
        if times:
            # Apply smoothing
            window = 10
            if len(thr) > window:
                smooth_times = times[window-1:]
                smooth_thr = moving_average(thr, window)
                ax1.plot(smooth_times, smooth_thr, 
                        label=f"{sched} (avg: {avg_kbps:.2f} Kbps)",
                        color=COLORS[sched], linewidth=2, alpha=0.8)
            else:
                ax1.plot(times, thr, 
                        label=f"{sched} (avg: {avg_kbps:.2f} Kbps)",
                        color=COLORS[sched], linewidth=2, alpha=0.8)
            
            stats[sched] = avg_kbps

    ax1.set_title("Throughput Over Time (Smoothed)", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Time (seconds)", fontsize=12)
    ax1.set_ylabel("Throughput (Kbps)", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.3)
    ax1.legend(loc='best', fontsize=10)
    
    # Plot 2: Average throughput comparison bar chart
    if stats:
        schedulers = list(stats.keys())
        avg_throughputs = [stats[s] for s in schedulers]
        colors = [COLORS[s] for s in schedulers]
        
        bars = ax2.bar(schedulers, avg_throughputs, color=colors, alpha=0.8, edgecolor='black')
        
        # Add value labels on bars
        for bar, val in zip(bars, avg_throughputs):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f} Kbps',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax2.set_title("Average Throughput Comparison", fontsize=14, fontweight='bold')
        ax2.set_ylabel("Average Throughput (Kbps)", fontsize=12)
        ax2.set_xlabel("Scheduler", fontsize=12)
        ax2.grid(True, axis='y', linestyle="--", alpha=0.3)

    os.makedirs("plots", exist_ok=True)
    plt.tight_layout()
    plt.savefig("plots/throughput_timeseries.png", dpi=150)
    print("✅ Saved plots/throughput_timeseries.png")


if __name__ == "__main__":
    main()
