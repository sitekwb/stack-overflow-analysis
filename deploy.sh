#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-genomic-benchmarking}"
REGION="${REGION:-europe-central2}"
SERVICE="${SERVICE:-so-survey-app}"

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --port 8080

gcloud run services describe "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --format='value(status.url)'
