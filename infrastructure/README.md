# LEVI-AI Infrastructure: Global Sovereign Network (v14.2)

LEVI-AI utilizes a globally diversified, serverless-first infrastructure on Google Cloud Platform. The design prioritizes 100% data sovereignty, high availability, and multi-region resonance.

## 🏗️ Deployment Architecture

Client → Global Load Balancer (HTTPS) → Cloud Run (Backend) → VPC Connector → Redis / PostgreSQL

### Infarstructure Diagram (Mermaid)
```mermaid
graph TD
    Client[Client Browser/Mobile] --> GLB[Global Load Balancer]
    GLB --> WAF[Cloud Armor WAF]
    WAF -- Latency-based Routing --> CR_US[Cloud Run - us-central1]
    WAF -- Latency-based Routing --> CR_EU[Cloud Run - europe-west1]
    
    subgraph Regional VPC (Diversified)
        CR_US --> VPC_C[VPC Connector]
        VPC_C --> SQL[Cloud SQL PostgreSQL]
        VPC_C --> REDIS[Memorystore Redis]
    end
    
    subgraph Global Pulse
        CR_US <--> PUBSUB[GCP Pub/Sub Cognitive Pulse]
        CR_EU <--> PUBSUB
    end
```

## 🛠️ GCP Managed Services
- **[Cloud Run]**: Primary backend gateway and background mission executors.
- **[Cloud SQL (PG 15)]**: Factual truth layer and user identity store.
- **[Memorystore (Redis 6.x)]**: Episodic memory and real-time mission state.
- **[Cloud Tasks]**: Wave scheduling and background task orchestration.
- **[Cloud Armor]**: WAF protection against SQLi, DDoS, and SSRF.

## 🚀 Deployment Guide

### Prerequisites
1.  `gcloud auth login`
2.  `gcloud auth application-default login`
3.  Terraform 1.5+

### Initial Provisioning
```bash
cd infrastructure/terraform
terraform init
terraform plan -var="gcp_project_id=YOUR_PROJECT"
terraform apply -var="gcp_project_id=YOUR_PROJECT"
```

### CI/CD Deployment
Pushing to the `main` branch triggers the `.github/workflows/production.yml` pipeline, which builds the backend image and performs a zero-downtime rolling update to Cloud Run across all regions.

## 🛡️ Networking & Ports
- **External Port**: 443 (HTTPS)
- **Internal Port**: 8000 (FastAPI Gateway)
- **VPC Range**: `10.0.0.0/24`
- **Connector Range**: `10.8.0.0/28`
