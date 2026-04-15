# LEVI-AI Air-Gapped Registry Manifest (v16.1)

To achieve 100% sovereignty and remove external dependencies during deployment, LEVI-AI utilizes a local, air-gapped container registry.

## Architecture
- **Registry Type**: CNCF Distribution (Docker Registry v2) with mTLS.
- **Node**: Sovereign Node 0 (Coordinator).
- **Storage**: Drive D (`D:\LEVI-AI\registry`).

## Deployment Instructions

### 1. Initialize Local Registry
```bash
docker run -d \
  -p 5000:5000 \
  --restart=always \
  --name leiva-registry \
  -v D:\LEVI-AI\registry:/var/lib/registry \
  registry:2
```

### 2. Configure Local Nodes (Daemon Config)
Update `/etc/docker/daemon.json` or Windows Docker Desktop config:
```json
{
  "insecure-registries": ["localhost:5000"]
}
```

### 3. Build and Push LEVI-AI Sovereign Images
```bash
docker build -t localhost:5000/levi-backend:v16.1 ./backend
docker push localhost:5000/levi-backend:v16.1
```

### 4. K8s Manifest Integration
Update `infrastructure/k8s/deployment.yaml`:
```yaml
spec:
  containers:
  - name: backend
    image: localhost:5000/levi-backend:v16.1
    imagePullPolicy: IfNotPresent
```

> [!IMPORTANT]
> This registry must be periodically synchronized with the upstream "Graduation Harbor" only via secure data-diode or vetted USB transition in ultra-high security environments.
