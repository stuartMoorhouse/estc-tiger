#!/bin/bash

# Remove the first line and prepare the data
tail -n +2 estc_bulk_import.json > temp_bulk.json

# Convert to the working format
DATA=$(cat temp_bulk.json | sed ':a;N;$!ba;s/\n/\\n/g')

# Load into Elasticsearch
curl -X POST "${ELASTICSEARCH_URL}/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -d $"${DATA}\n"

# Clean up
rm temp_bulk.json
