#!/bin/bash

set -e

# Loop over all folders with the pattern extpar_*
i=1
for dir in ${WORKSPACE}/extpar_*; do
    echo "Processing directory: $dir"
    cd "$dir"
    grid_file=$(cat ../icontools/grid_$i.txt)  # Assuming grid.txt contains the grid file name
    podman run \
        -v /c2sm-data/extpar-input-data:/data \
        -v ${WORKSPACE}/icontools:/grid \
        -v "$dir":/work \
        extpar-image \
        python3 -m extpar.WrapExtpar \
        --run-dir /work \
        --raw-data-path /data/linked_data \
        --account none \
        --no-batch-job \
        --host docker \
        --input-grid /grid/${grid_file} \
        --extpar-config /work/config.json
    cd ..
    ((i++))
done
