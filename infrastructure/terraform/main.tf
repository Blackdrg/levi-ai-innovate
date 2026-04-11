# infrastructure/terraform/main.tf (v14.1.0 Multi-Region Diversified)
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
}

# 🌐 Phase 3: Global Networking Overlay
resource "google_compute_network" "vpc" {
  for_each                = toset(var.regions)
  name                    = "levi-vpc-${each.value}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  for_each      = toset(var.regions)
  name          = "levi-subnet-${each.value}"
  ip_cidr_range = "10.0.0.0/24"
  region        = each.value
  network       = google_compute_network.vpc[each.value].id
}

# 🛡️ Global Security Base
resource "google_service_account" "cloud_run_sa" {
  account_id   = "levi-cloud-run"
  display_name = "LEVI Global Cloud Run Service Account"
}

resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
  ])
  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# 🗄️ Diversified Regional Data Layer
resource "google_sql_database_instance" "postgres" {
  for_each         = toset(var.regions)
  name             = "levi-db-${each.value}"
  database_version = "POSTGRES_15"
  region           = each.value

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL" # Zonal for Cost Management in diversified setup
    
    ip_configuration {
      require_ssl       = true
      private_network   = google_compute_network.vpc[each.value].id
      enable_private_path_import = true
    }
  }
  deletion_protection = false # Fast teardown for graduation testing
}

resource "google_redis_instance" "cache" {
  for_each       = toset(var.regions)
  name           = "levi-redis-${each.value}"
  memory_size_gb = 1
  tier           = "BASIC"
  region         = each.value
  authorized_network  = google_compute_network.vpc[each.value].id
}

# 🚀 Regional Cloud Run Clusters
resource "google_vpc_access_connector" "connector" {
  for_each      = toset(var.regions)
  name          = "levi-conn-${each.value}"
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc[each.value].name
  region        = each.value
}

resource "google_cloud_run_service" "backend" {
  for_each = toset(var.regions)
  name     = "${var.service_name}-${each.value}"
  location = each.value

  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa.email
      containers {
        image = "gcr.io/${var.gcp_project_id}/levi-backend:latest"
        env {
          name  = "GCP_REGION"
          value = each.value
        }
        env {
          name  = "DCN_IS_DIVERSIFIED"
          value = "true"
        }
      }
      vpc_access_connector {
        name = google_vpc_access_connector.connector[each.value].id
      }
    }
  }
}

# 🌌 Global Load Balancer Overlay
resource "google_compute_global_address" "default" {
  name = "levi-global-ip"
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  for_each              = toset(var.regions)
  name                  = "levi-neg-${each.value}"
  network_endpoint_type = "SERVERLESS"
  region                = each.value
  cloud_run {
    service = google_cloud_run_service.backend[each.value].name
  }
}

resource "google_compute_backend_service" "default" {
  name                  = "levi-backend-service"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  dynamic "backend" {
    for_each = toset(var.regions)
    content {
      group = google_compute_region_network_endpoint_group.serverless_neg[backend.value].id
    }
  }
}

resource "google_compute_url_map" "default" {
  name            = "levi-url-map"
  default_service = google_compute_backend_service.default.id
}

resource "google_compute_target_http_proxy" "default" {
  name    = "levi-http-proxy"
  url_map = google_compute_url_map.default.id
}

resource "google_compute_global_forwarding_rule" "default" {
  name                  = "levi-forwarding-rule"
  target                = google_compute_target_http_proxy.default.id
  port_range            = "80"
  ip_address            = google_compute_global_address.default.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

output "global_ip" {
  value = google_compute_global_address.default.address
}
