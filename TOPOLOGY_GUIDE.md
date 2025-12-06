# Network Topology Testing Guide

This project includes multiple network topologies based on the evaluation scenarios from the paper:
**"Reinforcement Learning Based Multipath QUIC Scheduler for Multimedia Streaming"**
https://www.mdpi.com/1424-8220/22/17/6333

## Available Topologies

### Topology 1 (Default): WiFi + Cellular
**Use case:** General multipath scenario, WiFi-like + LTE-like
```bash
sudo python3 mpquic_topo.py 1
```
- **Path A:** 8 Mbps bandwidth, 10ms delay, 1ms jitter (WiFi-like)
- **Path B:** 20 Mbps bandwidth, 40ms delay (LTE-like)
- **Characteristics:** Asymmetric paths with different delay/bandwidth tradeoffs

### Topology 2: Diverse RTT Paths
**Use case:** Tests scheduler behavior with very different path delays
```bash
sudo python3 mpquic_topo.py 2
```
- **Path A:** 20 Mbps bandwidth, 5ms delay (fast path)
- **Path B:** 15 Mbps bandwidth, 77ms delay (slow path)
- **Characteristics:** Large RTT difference, no packet loss
- **From paper:** Section 5.2 - Network with No Loss and Diverse RTT Paths

### Topology 3: Similar RTT with Packet Loss
**Use case:** Tests scheduler adaptability to lossy paths
```bash
sudo python3 mpquic_topo.py 3
```
- **Path A:** 50 Mbps bandwidth, 6ms delay (fast, reliable)
- **Path B:** 5 Mbps bandwidth, 8ms delay, **5% packet loss** (slow, lossy)
- **Characteristics:** Similar RTT but one path has significant packet loss
- **From paper:** Section 5.3 - Network with Packet Loss and Similar RTT Paths

### Topology 4: Adaptive Bitrate Test
**Use case:** Tests scheduler for adaptive video streaming scenarios
```bash
sudo python3 mpquic_topo.py 4
```
- **Path A:** 20 Mbps bandwidth, 5ms delay (fast)
- **Path B:** 15 Mbps bandwidth, 77ms delay (slow)
- **Characteristics:** Optimized for testing adaptive bitrate algorithms
- **From paper:** Section 5.5 - Adaptive Video Bitrate

## Running Experiments

### Single Topology
1. Start Mininet with a specific topology:
   ```bash
   sudo python3 mpquic_topo.py <topology_number>
   ```

2. In the Mininet CLI, run all scheduler experiments:
   ```bash
   mininet> source run_all_experiments.sh
   ```

3. Exit Mininet:
   ```bash
   mininet> exit
   ```

4. Sync results to local machine (if using remote VM)

5. Generate plots locally:
   ```bash
   bash generate_all_plots.sh
   ```

### Testing Multiple Topologies

To systematically test all topologies:

1. For each topology (1-4):
   ```bash
   sudo python3 mpquic_topo.py <topology_number>
   # In Mininet:
   mininet> source run_all_experiments.sh
   mininet> exit
   # Save results: mv runs runs_topo<number>
   ```

2. After collecting results from all topologies, compare them:
   ```bash
   python3 compare_topologies.py
   ```

This will generate a comparison plot showing how each scheduler performs across different network conditions.

## Expected Scheduler Behavior

Based on the paper's findings:

- **Topology 1 (WiFi+LTE):** MinRTT should favor fast path, WRR should balance load
- **Topology 2 (Diverse RTT):** Large performance differences between schedulers
- **Topology 3 (Packet Loss):** Redundant scheduler may perform better due to retransmissions
- **Topology 4 (Adaptive):** Tests dynamic adaptation to changing conditions

## Visualization

All plots are saved in the `plots/` directory:
- `plot_jitter_bar.png` - Jitter comparison
- `plot_path_usage.png` - Path selection distribution  
- `plot_rtt_cdf.png` - RTT cumulative distribution
- `throughput_timeseries.png` - Throughput over time with averages
- `plot_path_timeseries.png` - Path selection timeline (predict scheduler)
- `topology_comparison.png` - Multi-topology comparison (if available)

## Notes

- Topology 3 includes packet loss which makes results more variable
- The paper used 300 video chunks (1s each) for their tests
- Our simplified version uses 500 chunks of 500 bytes each
- Results may vary from the paper due to different test methodology
