#!/bin/bash

source gcp_setup_config.sh

gcloud config set project $PROJECT_ID

if [ $env = "test" ]
then
  gcloud beta builds triggers delete build-test --quiet
  gcloud beta builds triggers create github \
    --name="build-test" \
    --repo-name="lobby-bot" \
    --repo-owner="Port-Tango" \
    --pull-request-pattern="^main$" \
    --comment-control="COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY" \
    --build-config="lib/cloudbuild.yaml" \
    --included-files="lib/**,scripts/gitops/**,requirements.txt" \
    --substitutions=_REGION=$REGION,_BOT_SA=$BOT_SA,_ENV=$env,_SECRETS_PROJECT_NUMBER=$SECRETS_PROJECT_NUMBER \
    --service-account=projects/$PROJECT_ID/serviceAccounts/$BOT_SA
fi

if [ $env = "prod" ]
then
  gcloud beta builds triggers delete build-prod --quiet
  gcloud beta builds triggers create github \
    --name="build-prod" \
    --repo-name="lobby-bot" \
    --repo-owner="Port-Tango" \
    --branch-pattern="^main$" \
    --build-config="lib/cloudbuild.yaml" \
    --included-files="lib/**,scripts/gitops/**,requirements.txt" \
    --substitutions=_REGION=$REGION,_BOT_SA=$BOT_SA,_ENV=$env,_SECRETS_PROJECT_NUMBER=$SECRETS_PROJECT_NUMBER \
    --service-account=projects/$PROJECT_ID/serviceAccounts/$BOT_SA
fi
