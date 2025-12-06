#!/bin/bash
# Script to generate all performance plots

echo "Generating all plots..."

python3 creating_plots/jitter.py
python3 creating_plots/path_usage.py
python3 creating_plots/plot_throughput.py
python3 creating_plots/rtt.py
python3 creating_plots/plot_logs.py

echo ""
echo "All plots generated successfully!"
echo "Generated files in plots/ directory:"
ls -lh plots/*.png
