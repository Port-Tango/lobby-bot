#!/bin/bash

source gcp_setup_config.sh

gcloud config set project $PROJECT_ID

echo "Enable required services"
gcloud services enable \
  cloudbuild.googleapis.com \
  workflows.googleapis.com \
  iam.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  eventarc.googleapis.com \
  firestore.googleapis.com  \
  cloudtasks.googleapis.com

echo "Create service account for Lobby Bot"
gcloud iam service-accounts create $BOT_SA_PREFIX \
  --description="Service account for Lobby Bot" \
  --display-name=$BOT_SA_PREFIX

echo "Grant the IAM Service Account User roleto the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/iam.serviceAccountUser --condition=None

echo "Grant Log Writer role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/logging.logWriter --condition=None

echo "Grant Artifact Registry Writer role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/artifactregistry.writer --condition=None

echo "Grant Storage Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/storage.admin --condition=None

echo "Grant Storage Object Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/storage.objectAdmin --condition=None

echo "Grant Workflows Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/workflows.admin --condition=None

echo "Grant the IAM Service Account User role to the Cloud Build service account"
gcloud iam service-accounts add-iam-policy-binding $BOT_SA \
  --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser --condition=None

echo "Grant Cloud Functions Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/cloudfunctions.admin --condition=None

echo "Grant Cloud Scheduler Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/cloudscheduler.admin --condition=None

echo "Grant Cloud Run Invoker role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/run.invoker --condition=None

echo "Grant Secret Manager Secret Accessor role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/secretmanager.secretAccessor --condition=None

echo "Grant Eventarc Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/eventarc.admin --condition=None

echo "Grant Cloud Functions Service Agent role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/cloudfunctions.serviceAgent --condition=None

echo "Grant Pub/Sub Publisher role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/pubsub.publisher --condition=None

echo "Grant Datastore User role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/datastore.user --condition=None

echo "Grant Cloud Tasks Admin role to the Lobby Bot service account"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$BOT_SA \
  --role=roles/cloudtasks.admin --condition=None
