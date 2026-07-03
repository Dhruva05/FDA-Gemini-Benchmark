#!/usr/bin/env bash
set -euo pipefail

HARBOR_BIN="${HARBOR_BIN:-harbor}"

tasks=(
  fda-label-factual-qa
  fda-label-multihop-qa
  fda-label-refusal-qa
  fda-label-citation-retrieval
  fda-label-mixed-batch
)

for task in "${tasks[@]}"; do
  "$HARBOR_BIN" run -o logs -p "samples/$task" -a nop
done
