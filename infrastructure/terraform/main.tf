# infrastructure/terraform/main.tf
terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.0" }
  }

}

variable "cloud_provider" {
  type    = string
  default = "gcp"
}

# --- GCP Provider Configuration ---
provider "google" {
  project = var.gcp_project_id
  region  = "us-central1"
}

# --- AWS Provider Configuration ---
provider "aws" {
  region = "us-east-1"
}

# --- Sovereign Kubernetes Layer ---
resource "kubernetes_namespace" "levi" {
  metadata { name = "levi-cognitive" }
}

# --- Cloud SQL (GCP Primary) ---
resource "google_sql_database_instance" "postgres" {
  count            = var.cloud_provider == "gcp" ? 1 : 0
  name             = "levi-postgres-prod"
  database_version = "POSTGRES_15"
  settings {
    tier = "db-f1-micro"
    backup_configuration { enabled = true }
  }
}

# --- RDS (AWS Secondary) ---
resource "aws_db_instance" "postgres" {
  count                = var.cloud_provider == "aws" ? 1 : 0
  identifier           = "levi-postgres-prod"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage     = 20
  username             = "levi"
  password             = "super_secret_password"
}

# --- High-Availability ConfigMap for DCN ---
resource "kubernetes_config_map" "dcn_peers" {
  metadata {
    name      = "levi-dcn-peers"
    namespace = kubernetes_namespace.levi.metadata[0].name
  }
  data = {
    "peers.yaml" = yamlencode({
      dcn = {
        peers = [
          { node_id = "node-alpha", host = "alpha.levi-cognitive.svc", port = 9000 },
          { node_id = "node-bravo", host = "bravo.levi-cognitive.svc", port = 9000 }
        ]
      }
    })
  }
}
