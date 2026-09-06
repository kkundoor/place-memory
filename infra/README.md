# infra

Day 1 keeps infrastructure intentionally small. The current Terraform only enables the first APIs so cloud setup is version-controlled without prematurely provisioning paid database/storage resources.

Next resources after the local field test:

- Cloud Run service
- service account + least-privilege IAM
- Secret Manager secret bindings
- private Cloud Storage bucket
- Cloud SQL Postgres instance
- Cloud Build trigger from GitHub
