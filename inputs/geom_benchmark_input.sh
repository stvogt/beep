#!/bin/bash

# Function to display usage message
show_usage() {
    echo "Usage: bash sampling.sh"
}

# Check if the "--help" flag is provided
if [ "$1" == "--help" ]; then
    # Display help message and exit
    python ../workflows/launch_geom_benchmark.py --help
    exit 0
fi

# Python program invocation
python ../workflows/launch_geom_benchmark.py \
    --client_address localhost:7777 \
    --username '' \
    --password ''  \
    --benchmark-structures  co_w2_0007 co_w3_0004   \
    --small-molecule-collection small_molecules \
    --molecule CO \
    --surface-model-collection small_water \
    --reference-geometry-level-of-theory 'DF-CCSD(T)-F12' 'cc-pVDZ-F12' 'molpro' \
    --dft-optimization-program psi4 \
