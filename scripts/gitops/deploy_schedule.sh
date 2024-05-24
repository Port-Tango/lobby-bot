#!/bin/bash

# A script to create or update an existing Cloud Scheduler job for a Google Cloud Function

FUNCTION_NAME="$1"
SCHEDULE="$2"
OATH_SA="$3"
REGION="$4"
PROJECT_ID="$5"
ENDPOINT="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}"

gcloud scheduler jobs create http ${FUNCTION_NAME}_scheduler \
  --location=$REGION \
  --oidc-service-account-email=$OATH_SA \
  --uri="${ENDPOINT}" \
  --schedule="${SCHEDULE}" \
  --http-method=POST \
  --message-body='{}' \
  --headers='Content-Type=application/json' \
|| \
gcloud scheduler jobs update http ${FUNCTION_NAME}_scheduler \
  --location=$REGION \
  --oidc-service-account-email=$OATH_SA \
  --uri="${ENDPOINT}" \
  --schedule="${SCHEDULE}" \
  --http-method=POST \
  --message-body='{}' \
