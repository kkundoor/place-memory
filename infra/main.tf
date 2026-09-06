terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }

provider "google" {
  project = var.project_id
  region  = var.region
}

# day 1: document the production boundary without provisioning paid resources yet
resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "aiplatform" {
  project = var.project_id
  service = "aiplatform.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "places" {
  project = var.project_id
  service = "places-backend.googleapis.com"
}

resource "google_project_service" "routes" {
  project = var.project_id
  service = "routes.googleapis.com"
}

resource "google_project_service" "static_maps" {
  project = var.project_id
  service = "static-maps-backend.googleapis.com"
}
