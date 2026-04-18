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

provider "google" {
  alias  = "europe"
  project = var.gcp_project_id
  region  = "europe-west1"
}

# --- AWS Provider Configuration ---
provider "aws" {
  region = "us-east-1"
}

# --- Sovereign Kubernetes Layer ---
resource "kubernetes_namespace" "levi" {
  metadata { name = "levi-cognitive" }
}

# --- Cloud SQL (GCP Primary - High Availability) ---
resource "google_sql_database_instance" "postgres" {
  name             = "levi-postgres-prod"
  database_version = "POSTGRES_15"
  region           = "us-central1"
  settings {
    tier = "db-custom-2-7680" # 2 vCPU, 7.5GB RAM (P0 Hardened)
    availability_type = "REGIONAL" # High Availability (Multi-zone failover)
    backup_configuration {
      enabled = true
      point_in_time_recovery_enabled = true
    }
    ip_configuration {
      ipv4_enabled = false
      private_network = var.vpc_id
    }
  }
}

# --- GKE Autopilot Cluster (Sovereign Engine v15.0) ---
resource "google_container_cluster" "primary" {
  name     = "levi-sovereign-cluster-us"
  location = "us-central1"
  enable_autopilot = true
  
  network    = var.vpc_id
  subnetwork = var.subnet_id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
}

# --- Secondary Regional Cluster (Europe) ---
resource "google_container_cluster" "secondary" {
  provider = google.europe
  name     = "levi-sovereign-cluster-eu"
  location = "europe-west1"
  enable_autopilot = true
  
  network    = var.vpc_id
  subnetwork = var.subnet_eu_id
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

# --- Sovereign Secret Manager (GCP) ---
resource "google_secret_manager_secret" "dcn_secret" {
  count     = var.cloud_provider == "gcp" ? 1 : 0
  secret_id = "levi-dcn-secret"
  replication {
    user_managed {
      replicas { location = "us-central1" }
    }
  }
}

resource "google_secret_manager_secret" "arweave_wallet" {
  count     = var.cloud_provider == "gcp" ? 1 : 0
  secret_id = "levi-arweave-wallet"
  replication {
    user_managed {
      replicas { location = "us-central1" }
    }
  }
}

# --- Cloud Memorystore (Redis Standard-HA) ---
resource "google_redis_instance" "cache" {
  name           = "levi-redis-prod"
  tier           = "STANDARD_HA" # Multi-zone replication
  memory_size_gb = 5
  region         = "us-central1"
  connect_mode   = "PRIVATE_SERVICE_ACCESS"
  authorized_network = var.vpc_id
}

# --- Global Cloud Load Balancer (Multi-Region Ingress) ---
resource "google_compute_global_forwarding_rule" "default" {
  name       = "levi-global-lb"
  target     = google_compute_target_http_proxy.default.id
  port_range = "80"
}

resource "google_compute_target_http_proxy" "default" {
  name    = "levi-http-proxy"
  url_map = google_compute_url_map.default.id
}

resource "google_compute_url_map" "default" {
  name            = "levi-url-map"
  default_service = google_compute_backend_service.primary.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.primary.id
  }
}

resource "google_compute_backend_service" "primary" {
  name        = "levi-backend-service"
  port_name   = "http"
  protocol    = "HTTP"
  timeout_sec = 30
  
  backend {
    group = google_container_cluster.primary.node_pool[0].instance_group_urls[0]
  }

  backend {
    group = google_container_cluster.secondary.node_pool[0].instance_group_urls[0]
  }

  health_checks = [google_compute_health_check.default.id]
}

resource "google_compute_health_check" "default" {
  name               = "levi-health-check"
  check_interval_sec = 5
  timeout_sec        = 5
  http_health_check {
    port = 8000
    request_path = "/healthz"
  }
}

# --- Workload Identity (Zero-Trust Security) ---
resource "google_service_account" "levi_identity" {
  account_id   = "levi-sovereign-identity"
  display_name = "Sovereign Workload Identity"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.levi_identity.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.gcp_project_id}.svc.id.goog[levi-cognitive/levi-sa]"
}


output "postgres_endpoint" {
  value = var.cloud_provider == "gcp" ? google_sql_database_instance.postgres.public_ip_address : (length(aws_db_instance.postgres) > 0 ? aws_db_instance.postgres[0].endpoint : "")
}
