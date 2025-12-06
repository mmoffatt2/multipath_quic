Setup virtual env:

    python3 -m venv venv <n> # where n is a number from 1-4

    source venv/bin/activate
    
    pip install -r requirements.txt

Use Mininet VM for future steps:

Run schedulers:

    sudo python3 mpquic_topo.py
    
    source run_all_experiments.sh

    bash generate_all_plots.sh

