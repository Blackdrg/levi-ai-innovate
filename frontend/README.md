# 🐚 LEVI-AI: The Sovereign Shell (Frontend)

The Shell is the React-based user interface for the LEVI-AI Sovereign OS. It provides a real-time terminal and dashboard for monitoring the cognitive swarm.

## 📡 Connection Architecture
The Shell connects to the Sovereign Mainframe (Soul) via two primary channels:
1. **REST API (FastAPI)**: For mission submission, history retrieval, and hardware calibration settings.
2. **WebSockets (Stream Pulse)**: For real-time telemetry, agent logs, and thermal heartbeats.

## 🛠️ Tech Stack
- **Framework**: Vite + React
- **Styling**: TailwindCSS (Hardened)
- **State Management**: Zustand (Mission context)
- **Visualization**: Recharts (VRAM/CU metrics)

## 🚀 Getting Started
1. Ensure the Mainframe is running at `http://localhost:8000`.
2. Install dependencies: `npm install`
3. Launch development shell: `npm run dev`

## 🛡️ Forensic Visualization
The dashboard includes a **BFT Pulse Monitor** that visualizes the signature chain of the audit ledger in real-time, highlighting any parity errors or adversarial interference.
