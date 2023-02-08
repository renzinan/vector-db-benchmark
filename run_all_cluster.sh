#!/usr/bin/env bash

set -e

DATASETS=${DATASETS:-"glove-100-angular glove-25-angular gist-960-euclidean deep-image-96-angular"}
DATASET_ARGS=""
for dataset in $DATASETS; do
    DATASET_ARGS="$DATASET_ARGS --datasets $dataset"
done

MILVUS_SERVER_HOST=${SERVER_HOST:-"10.0.0.194"}
QDRANT_SERVER_HOST=${SERVER_HOST:-"10.0.3.194"}
WEAVIATE_SERVER_HOST=${SERVER_HOST:-"10.0.1.194"}
ENGINE_SETTING=${ENGINE_SETTING:-"-m-*-ef-128"}

python3 run.py --engines milvus$ENGINE_SETTING $DATASET_ARGS --host $MILVUS_SERVER_HOST
python3 run.py --engines qdrant-rps$ENGINE_SETTING $DATASET_ARGS --host $QDRANT_SERVER_HOST
#python3 run.py --engines weaviate$ENGINE_SETTING $DATASET_ARGS --host $WEAVIATE_SERVER_HOST



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

