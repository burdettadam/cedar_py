#!/bin/bash
# Automated cleanup script for cedar-integration-tests corpus-tests
# Deletes all .cedar, .cedarschema, .entities.json, and .json files in the corpus-tests directory

CORPUS_DIR="$(dirname "$0")/cedar-integration-tests/corpus-tests"

find "$CORPUS_DIR" -type f \( -name '*.cedar' -o -name '*.cedarschema' -o -name '*.entities.json' -o -name '*.json' \) -delete

echo "Cleanup complete: Removed all .cedar, .cedarschema, .entities.json, and .json files from $CORPUS_DIR."
