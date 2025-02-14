#!/usr/bin/env bash


rsync -avP \
   --exclude="results" \
   --exclude="results-*" \
   --exclude='*.hdf5' \
   --exclude='venv' \
   --exclude='__pycache__' \
   --exclude='frontend' \
   --exclude='.idea' \
   --exclude='.git' \
   --exclude='datasets/*/' \
   . $1:./projects/vector-db-benchmark/
