#!/bin/bash

. ../constants.env

CONFIG_PATH="../../lib/"
DEV_BOT_SA=$BOT_SA_PREFIX@$DEV_PROJECT_ID.iam.gserviceaccount.com

gcloud config set project $DEV_PROJECT_ID
SECRETS_PROJECT_NUMBER=$(gcloud projects describe $PROD_PROJECT_ID --format='value(projectNumber)')
echo $SECRETS_PROJECT_NUMBER

gcloud builds submit ../.. --config=$CONFIG_PATH/cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_BOT_SA=$DEV_BOT_SA,_ENV='dev',_SECRETS_PROJECT_NUMBER=$SECRETS_PROJECT_NUMBER \
  --impersonate-service-account=$BOT_SA
