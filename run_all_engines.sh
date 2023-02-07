#!/usr/bin/env bash

set -e

DATASETS=${DATASETS:-"glove-100-angular glove-25-angular gist-960-euclidean deep-image-96-angular"}
DATASET_ARGS=""
for dataset in $DATASETS; do
    DATASET_ARGS="$DATASET_ARGS --datasets $dataset"
done

SERVER_HOST=${SERVER_HOST:-"localhost"}
SERVER_USERNAME=${SERVER_USERNAME:-"user"}

SSH_OPT="-i ~/.ssh/ann-cloud-engine-benchmark_key.pem"

function run_exp() {
    SERVER_PATH=$1
    ENGINE_NAME=$2
    MONITOR_PATH=$(echo $ENGINE_NAME | sed -e 's/[^A-Za-z0-9._-]/_/g')
    ssh $SSH_OPT ${SERVER_USERNAME}@${SERVER_HOST} "nohup bash -c 'cd ./projects/vector-db-benchmark/monitoring && rm -f docker.stats.jsonl && bash monitor_docker.sh' > /dev/null 2>&1 &"
    ssh $SSH_OPT -t ${SERVER_USERNAME}@${SERVER_HOST} "cd ./projects/vector-db-benchmark/engine/servers/$SERVER_PATH ; docker compose down ; docker compose up -d"
    sleep 30
    python3 run.py --engines $ENGINE_NAME $DATASET_ARGS --host $SERVER_HOST
    ssh $SSH_OPT -t ${SERVER_USERNAME}@${SERVER_HOST} "cd ./projects/vector-db-benchmark/engine/servers/$SERVER_PATH ; docker compose down"
    ssh $SSH_OPT -t ${SERVER_USERNAME}@${SERVER_HOST} "cd ./projects/vector-db-benchmark/monitoring && mkdir -p results && mv docker.stats.jsonl ./results/${MONITOR_PATH}-docker.stats.jsonl"
}


#run_exp "qdrant-single-node" 'qdrant-m-32-*'
#run_exp "weaviate-single-node" 'weaviate-m-32-*'
#run_exp "milvus-single-node" 'milvus-m-32-*'

run_exp "weaviate-single-node" 'weaviate-m-*-ef-128'
run_exp "milvus-single-node" 'milvus-m-*-ef-128'
run_exp "qdrant-single-node" 'qdrant-rps-m-*-ef-128'
#run_exp "elasticsearch-single-node" 'elastic-m-*-ef-128'

# run_exp "elasticsearch-single-node" 'elastic-m-*'
# run_exp "redis-single-node" 'redis-m-*'

# Extra: qdrant configured to tune RPS

