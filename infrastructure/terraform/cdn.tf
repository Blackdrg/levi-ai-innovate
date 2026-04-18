# infrastructure/terraform/cdn.tf

# 🌐 Cloudflare Provider (Recommended for Edge Caching)
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

resource "cloudflare_zone" "levi_zone" {
  zone = "levi-ai.sovereign"
}

# --- Cloudflare Cache Rules ---
resource "cloudflare_filter" "static_assets" {
  zone_id = cloudflare_zone.levi_zone.id
  expression = "(http.request.uri.path contains \"/shared/\" or http.request.uri.path contains \"/ui/\")"
}

resource "cloudflare_page_rule" "edge_cache" {
  zone_id = cloudflare_zone.levi_zone.id
  target  = "*.levi-ai.sovereign/shared/*"
  actions {
    cache_level = "cache_everything"
    edge_cache_ttl = 14400 # 4 hours
    browser_cache_ttl = 14400
  }
}

# --- GCP Cloud CDN (Backend Integration) ---
resource "google_compute_backend_service" "cdn_backend" {
  name        = "levi-cdn-backend"
  enable_cdn  = true
  
  cdn_policy {
    cache_mode = "CACHE_ALL_STATIC"
    default_ttl = 3600
    client_ttl  = 3600
    max_ttl     = 86400
    negative_caching = true
  }

  backend {
    group = google_container_cluster.primary.node_pool[0].instance_group_urls[0]
  }

  health_checks = [google_compute_health_check.default.id]
}
