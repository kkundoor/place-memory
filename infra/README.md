# infrastructure

The shareable project is deliberately runnable without paid cloud infrastructure. The root Dockerfile builds the React frontend and FastAPI backend into one image, and `render.yaml` provides a zero-cost demo deployment path once a Render account is connected.

`infra/main.tf` is a **future GCP production boundary**, not a claim that the current demo is deployed there. It only enables services that would be needed for a Cloud Run deployment with server-side secrets and optional Google Places/Routes.

Potential production additions, only when justified:

- Cloud Run service
- least-privilege service account / IAM
- Secret Manager bindings
- private artifact storage
- managed Postgres/PostGIS if measured retrieval/indexing needs it
- Cloud Build trigger from GitHub

The project intentionally does not provision Cloud SQL, Kubernetes, Redis, or other paid/operational infrastructure before the workload requires it.
