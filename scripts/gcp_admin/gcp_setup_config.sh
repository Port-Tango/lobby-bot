#!/bin/bash

. ../constants.env

PS3="Which environment are you setting up?: "

select env in prod test dev; do

  case $env in
    prod)
      PROJECT_ID=$PROD_PROJECT_ID
      break
      ;;
    test)
      PROJECT_ID=$TEST_PROJECT_ID
      break
      ;;
    dev)
      PROJECT_ID=$DEV_PROJECT_ID
      break
      ;;
    *) 
      echo "Invalid option $REPLY"
      ;;
  esac
done
echo "Get the GCP project region, id and number"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
BOT_SA=$BOT_SA_PREFIX@$PROJECT_ID.iam.gserviceaccount.com
echo "bot service account: $BOT_SA"
echo "project: $PROJECT_ID"
echo "project number: $PROJECT_NUMBER"
echo "project region: $REGION"
