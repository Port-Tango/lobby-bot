source gcp_setup_config.sh

gcloud config set project $PROJECT_ID

gcloud firestore databases create --location=$REGION
