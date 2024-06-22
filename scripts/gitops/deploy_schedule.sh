#!/bin/bash

# A script to create or update an existing Cloud Scheduler job for a Google Cloud Function

FUNCTION_NAME="$1"
SCHEDULE_NAME="$2"
SCHEDULE="$3"
OATH_SA="$4"
REGION="$5"
PROJECT_ID="$6"
MESSAGE="${7:-'{}'}"  # default to "{}" if no message is provided
ENDPOINT="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}"
TIMEOUT="600s"

gcloud scheduler jobs create http ${SCHEDULE_NAME}_scheduler \
  --location=$REGION \
  --oidc-service-account-email=$OATH_SA \
  --uri="${ENDPOINT}" \
  --schedule="${SCHEDULE}" \
  --http-method=POST \
  --message-body="${MESSAGE}" \
  --headers='Content-Type=application/json' \
  --attempt-deadline=${TIMEOUT} \
|| \
gcloud scheduler jobs update http ${SCHEDULE_NAME}_scheduler \
  --location=$REGION \
  --oidc-service-account-email=$OATH_SA \
  --uri="${ENDPOINT}" \
  --schedule="${SCHEDULE}" \
  --http-method=POST \
  --message-body="${MESSAGE}" \
  --attempt-deadline=${TIMEOUT}
