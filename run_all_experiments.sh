# Mininet CLI commands to run all QUIC scheduler experiments
# Usage in Mininet CLI: source run_all_experiments.sh

h2 python3 server.py &
h1 sleep 3
h1 python3 scheduler_client.py minrtt
h1 sleep 2
h1 python3 scheduler_client.py wrr
h1 sleep 2
h1 python3 scheduler_client.py redundant
h1 sleep 2
h1 python3 scheduler_client.py predict

