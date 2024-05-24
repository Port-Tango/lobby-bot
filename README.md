# lobby-bot

This repository contains serverless backend components for a Discord bot that hosts matchmaking lobbies for various Nifty Island playground games and islands.

The bot relies on the following Google Cloud Platform services:
1. [Cloud Functions](https://cloud.google.com/functions) - used for core bot logic and running other arbitrary python code
2. [Cloud Tasks](https://cloud.google.com/tasks) - used for asynchronous task execution of follow-up tasks (e.g. deleting closed lobbies 10 minutes after close)
3. [Cloud Scheduler](https://cloud.google.com/scheduler) - used to schedule cron jobs (e.g. cleaning up non-bot messages from matchmaking channel every 1 minute)
4. [Cloud Build](https://cloud.google.com/build) - used to build, test, and deploy bot to test, and prod environments

### Deploying to the Test GCP Project
  
After you create a pull request in the repo, each commit will automatically trigger a build and deployment to the test environment, as well as the tests defined in the corresponding cloudbuild.yaml file(s)
  
### Deploying to the Prod GCP Project
  
PRs that are merged to the main branch of this repo will automatically trigger a build and deployment to the prod environment, as well as the tests defined in the corresponding cloudbuild.yaml file(s)
