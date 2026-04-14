# LEVI-AI Sovereign OS: Production Runbook (v16.0)

## 🚀 Mission Overview
LEVI-AI is a decentralized, sovereign cognitive operating system. This runbook covers deployment, scaling, and emergency operations.

## 🛠 Prerequisites
- **PostgreSQL 15+**: Persistent facts and mission logs.
- **Redis 7+**: Ephemeral context, DCN gossip, and event sourcing.
- **Neo4j 5+**: Knowledge graph relationships.
- **FAISS**: Semantic vector index.
- **Docker & Kubernetes (GKE preferred)**: Node orchestration.

## 📦 Deployment Guide
1. **Infrastructure Provisioning**:
   ```bash
   cd deployment/terraform
   terraform init
   terraform apply -var="region=us-east1"
   ```
2. **Database Migration**:
   ```bash
   cd backend
   alembic upgrade head
   python seed.py --environment production
   ```
3. **Container Deployment**:
   ```bash
   docker build -t gcr.io/levi-ai/backend:v16.0 .
   kubectl apply -f deployment/k8s/
   ```

## 📈 Monitoring & SLAs
- **Uptime**: 99.5% (Target)
- **RTO (Recovery Time Objective)**: < 2 min
- **P95 Latency**: < 10s for L2 missions.
- **VRAM Pressure**: Monitor `vram_pressure_gauge` in Prometheus. Alerts at > 90%.

## 🚨 Emergency Procedures (Chaos & Recovery)
- **Cluster Split-Brain**: 
  - Trigger force re-election: `curl -X POST /api/v1/system/re-elect -H "X-Security-Token: $SECRET"`
- **VRAM Exhaustion**:
  - Kill long-running missions: `python scripts/emergency_abort.py --all`
  - Scale up worker pods: `kubectl scale deployment levi-worker --replicas=10`

## 🛡 Security Policy
- **SSRF Shield**: All agent tool calls are routed through the `EgressProxy`.
- **HMAC Audit**: Every memory event is signed. Verify chain: `python scripts/validate_audit_chain.py`
- **PII Redaction**: Enforced by `SovereignShield` in the orchestrator.
