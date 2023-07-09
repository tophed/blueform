terraform {
  required_providers {
    google = {
      source  = "hashicorp/google",
      version = "~> 4.71"
    }
  }
  backend "gcs" {
    bucket = "blufrm-state"
    prefix = "foundation"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project" "project" {
  project_id = var.project_id
  name       = var.project_name
}

resource "google_project_service" "cloudresourcemanager" {
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_project_service" "iam" {
  service = "iam.googleapis.com"
}

resource "google_project_service" "firestore" {
  service = "firestore.googleapis.com"
}

resource "google_project_service" "run" {
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
}

