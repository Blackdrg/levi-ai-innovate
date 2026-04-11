# LEVI-AI Test Suite & Verification (v14.2)

LEVI-AI utilizes a multi-tier testing strategy to ensure 100% system integrity and production stability.

## 🧪 Test Categories

- **Unit Tests**: Standard logic verification for core engines and utilities.
- **Integration Tests**: End-to-end mission flows from API Gateway to Agent Swarm.
- **Chaos Tests**: Verifies DCN resilience during node failure and network partitions.
- **Load Tests**: Validates system performance and backpressure under extreme mission volume ($CU_{sim} > 100$).
- **graduation_audit**: High-fidelity graduation suite for production-readiness sign-off.

## 🚀 Execution Commands

### Full Test Suite
```bash
pytest tests/
```

### Core Logic Only
```bash
pytest tests/core/
```

### Production Readiness Audit
```bash
python tests/v14_production_audit.py
```

### Chaos & Resilience
```bash
pytest tests/chaos/
```

## 📊 Coverage & Reporting
Unit test coverage is tracked via `pytest-cov`. In a production release, the `Graduation Score` is calculated strictly from the audit suite results:
$$GS = 1.0 \iff \forall Test_{i} \in AuditSuite, Result_{i} = Pass$$

## 📂 Test Organization
```text
├── core/             # Core Engine Tests (Planner, Orchestrator)
├── integration/      # S2S and Multi-Agent flows
├── chaos/            # Resilience & Failover scenarios
├── load/             # K6/Locust performance benches
└── v14/              # Version-specific graduation scripts
```
