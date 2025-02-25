#!/bin/bash

# Define the target directory and URL
TARGET_DIR="backend/data_pipelines/external_data/imdb_data"
URL="https://datasets.imdbws.com/title.basics.tsv.gz"

# Create the target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Download the file into the target directory
curl -o "$TARGET_DIR/title.basics.tsv.gz" "$URL"

# Verify the download
if [ $? -eq 0 ]; then
    echo "Download completed successfully: $TARGET_DIR/title.basics.tsv.gz"
else
    echo "Download failed."
    exit 1
fi