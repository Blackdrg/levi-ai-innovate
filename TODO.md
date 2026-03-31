# LEVI Project Roadmap & TODO (v5.0 Hardened) 🚀

## 🟢 PHASE 5.0: HARDENING & RELIABILITY (COMPLETE)
- [x] **True SSE Streaming**: Direct token piping from Groq API (no more simulation).
- [x] **Response Caching**: 30-min TTL Redis cache for search/chat agents.
- [x] **Circuit Breaker Consolidation**: Unified implementation with Discord webhook alerts.
- [x] **Memory Pruning Fix**: Native Timestamp comparison for Firestore auto-cleanup.
- [x] **Infrastructure Overhaul**: SSE-optimized Nginx config and Docker `beat` service.
- [x] **Security Hardening**: Corrected JTI blacklist logic in `redis_client.py`.
- [x] **Ops Runbook**: Centralized manual for production maintenance.

## 🟡 PHASE 6.0: ADVANCED COGNITION (IN PROGRESS)
- [ ] **Multi-Agent Swarms**: Dynamic task delegation among specialized sub-agents.
- [ ] **Vector Database Migration**: Move from local embeddings to Qdrant/Pinecone for million-document scale.
- [ ] **Adaptive Load Balancing**: Predictive scaling based on inference queue depth.
- [ ] **Tool Use Expansion**: Python REPL and dynamic Web Search browsing.
- [ ] **Feedback Loop**: Self-improving intent detection based on user interaction logs.

## 🔴 FUTURE GOALS (PHASE 7+)
- [ ] **Global Low-Latency Edge**: Edge-deployment for the Sanitization/Memory layers.
- [ ] **Self-Finetuning**: Automated nightly fine-tuning on high-quality interactions.
- [ ] **Voice Synthesis**: Real-time ElevenLabs/HeyGen streaming for the chat interface.
- [ ] **Cognitive Architecture**: Moving from 8-stage pipeline to a fully recursive agentic framework.

---

**LEVI — Built for emergence. Planned for depth.**
