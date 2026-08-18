#!/bin/bash

# Get info on SHACL shapes in YAGO4.6
python src/get_shapes_info.py \
  --output data/shapes_info.csv

# Prepare folder for datasets related to shape Event
mkdir data/Event

# Get target nodes degree distribution for shape Event
python src/get_target_nodes_degree_distribution.py \
  --shape-uri http://schema.org/Event \
  --output-hist data/Event/event_hist.pdf \
  --output-ecdf data/Event/event_ecdf.pdf

# Start building Event datasets

# -- Event 2 seeds 10 min degree
mkdir data/Event/Event_2seeds_10mindegree

python src/get_seed_nodes.py \
  --shape-uri http://schema.org/Event \
  --seed-nodes 2 \
  --min-degree 10 \
  --output data/Event/Event_2seeds_10mindegree/seed_nodes.pkl

# -- Event 2 seeds 100 min degree
mkdir data/Event/Event_2seeds_100mindegree

python src/get_seed_nodes.py \
  --shape-uri http://schema.org/Event \
  --seed-nodes 2 \
  --min-degree 100 \
  --output data/Event/Event_2seeds_100mindegree/seed_nodes.pkl

# -- Event 5 seeds 10 min degree
mkdir data/Event/Event_5seeds_10mindegree

python src/get_seed_nodes.py \
  --shape-uri http://schema.org/Event \
  --seed-nodes 5 \
  --min-degree 10 \
  --output data/Event/Event_5seeds_10mindegree/seed_nodes.pkl

# -- Event 5 seeds 100 min degree
mkdir data/Event/Event_5seeds_100mindegree

python src/get_seed_nodes.py \
  --shape-uri http://schema.org/Event \
  --seed-nodes 5 \
  --min-degree 100 \
  --output data/Event/Event_5seeds_100mindegree/seed_nodes.pkl
