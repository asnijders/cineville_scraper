#!/bin/bash

# Ensure the data directory exists
mkdir -p "$(dirname "$0")/../data"

# Download the file into the data directory
curl -L -o "$(dirname "$0")/../data/the-movies-dataset.zip" \
  https://www.kaggle.com/api/v1/datasets/download/rounakbanik/the-movies-dataset
