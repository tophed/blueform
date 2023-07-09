terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.71"
    }
  }

  backend "gcs" {
    bucket = "blufrm-state"
    prefix = "app"
  }
}

data "terraform_remote_state" "foundation" {
  backend   = "gcs"
  workspace = terraform.workspace
  config = {
    bucket = "blufrm-state"
    prefix = "foundation"
  }
}

locals {
  foundation = data.terraform_remote_state.foundation.outputs
}

provider "google" {
  project = local.foundation.project.project_id
  region  = local.foundation.region
}

resource "google_service_account" "local_agent" {
  account_id = "local-agent"
}

resource "google_storage_bucket" "state" {
  name     = "blufrm-user-state"
  location = local.foundation.region
}

resource "google_storage_bucket" "plans" {
  name     = "blufrm-user-plans"
  location = local.foundation.region
}

resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = "us-west1"
  type        = "FIRESTORE_NATIVE"
}

resource "google_artifact_registry_repository" "app" {
  location      = "us-west1"
  repository_id = "app"
  description   = "Docker images for Blueform app"
  format        = "DOCKER"
}
