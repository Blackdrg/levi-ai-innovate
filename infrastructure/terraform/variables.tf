# infrastructure/terraform/variables.tf
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run Service Name"
  type        = string
  default     = "levi-backend"
}
variable "regions" {
  description = "List of GCP regions for diversified global deployment"
  type        = list(string)
  default     = ["us-central1", "europe-west1", "asia-east1", "southamerica-east1", "australia-southeast1"]
}
