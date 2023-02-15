#!/usr/bin/env bash

set -e

declare -A ENGINES
ENGINES+=( ["weaviate"]=10.0.1.194 ["milvus"]=10.0.0.194 ["qdrant-rps"]=10.0.3.194 )
#ENGINES+=( ["weaviate"]=10.0.1.194 )

DATASETS=${DATASETS:-"glove-100-angular glove-25-angular gist-960-euclidean deep-image-96-angular h-and-m-2048-angular-no-filters"}
#DATASETS=${DATASETS:-"glove-100-angular"}

ENGINE_SETTING=${ENGINE_SETTING:-"m-*-ef-*"}

RUN_CMD="python3 run.py"
#RUN_CMD="echo"

DATASET_ARGS=""
ENGINE_ARGS=""
SERVER_ARGS=""
for dataset in $DATASETS; do
    DATASET_ARGS="--datasets $dataset"
    for engine_name in ${!ENGINES[@]}; do
        ENGINE_ARGS="--engines $engine_name-$ENGINE_SETTING"
	SERVER_ARGS="--host ${ENGINES[${engine_name}]}"
	CMD="$RUN_CMD $ENGINE_ARGS $DATASET_ARGS $SERVER_ARGS --no-exit-on-error"
	echo $CMD
        $CMD
    done
done


#run_exp "qdrant-single-node" 'qdrant-m-32-*'
#run_exp "weaviate-single-node" 'weaviate-m-32-*'
#run_exp "milvus-single-node" 'milvus-m-32-*'

#run_exp "weaviate-single-node" 'weaviate-m-*-ef-128'
#run_exp "milvus-single-node" 'milvus-m-*-ef-128'
#run_exp "qdrant-single-node" 'qdrant-rps-m-*-ef-128'
#run_exp "elasticsearch-single-node" 'elastic-m-*-ef-128'

# run_exp "elasticsearch-single-node" 'elastic-m-*'
# run_exp "redis-single-node" 'redis-m-*'

# Extra: qdrant configured to tune RPS

