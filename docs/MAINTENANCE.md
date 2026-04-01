# 🧹 Routine Matrix Maintenance

Sovereign OS caches vast arrays of temporal data to supply low-latency reads. Left unchecked, LEVI-AI will fill both disk and Firestore constraints. Perform these tasks bi-weekly.

### 1. The FAISS Flush Protocol
If dynamic routing is writing excessive conversational branches to the vector stores, those `_faiss.bin` and `_meta.json` files expand infinitely.
- **Action:** Execute the `.venv` and run `scripts/verify_memory_brain.py --flush`. This systematically trims the oldest dense vectors and garbage-collects numpy memory.

### 2. Studio Binary Trash Collection
MoviePy drops extensive temporary audio files (`levi_tts_*.wav`) and video (`levi_vid_*.mp4`) into the OS `/tmp/` directory if a job crashes before normal `.finally()` garbage collection executes.
- **Action (Linux):** `find /tmp -name "levi_*" -mtime +1 -exec rm -f {} \;`
- **Action (Windows):** Clear the `%TEMP%` directory targeting `levi_*` stubs.

### 3. Firestore Document Lifecycle
Firestore charges per read/write and storage space.
`decision_audit` and `jobs` collections can organically balloon.
- Set a **TTL (Time to Live) policy** natively inside Google Cloud Console targeting `decision_audit` documents older than 30 days.

### 4. Semantic Evolution Syncing
The Critic agent `AdaptivePromptManager` constantly overwrites prompt rules based on 5-star user heuristical evaluations. 
- Over months, it may become hyper-focused on one sub-set of topics (e.g. exclusively generating "cyberpunk" reflections).
- You can manually inspect its state and force a neural reset via `scripts/verify_sovereign_shield.py --reset-prompts`.
