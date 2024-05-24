#!/bin/bash

source gcp_setup_config.sh

gcloud config set project $PROJECT_ID

gcloud tasks queues create delayed-task-queue \
  --location=$REGION \
  --max-dispatches-per-second=500 \
  --max-concurrent-dispatches=50 \
  --max-attempts=10 \
  --max-doublings=4 \
  --min-backoff="1s" \
  --max-backoff="10s" \
