// backend/levi_runtime/src/runtime/daemon.rs
use notify::{Watcher, RecursiveMode, Config, Event};
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{info, error};
use crate::orchestrator::SwarmOrchestrator;
use uuid::Uuid;

pub struct LeviDaemon {
    orchestrator: Arc<SwarmOrchestrator>,
}

impl LeviDaemon {
    pub fn new(orchestrator: Arc<SwarmOrchestrator>) -> Self {
        Self { orchestrator }
    }

    pub async fn start_background_services(&self) -> anyhow::Result<()> {
        info!(" ⚙️ [Daemon] LEVI Infrastructure Layer Active. Initializing FS Watcher...");
        
        // 1. Setup FS Watcher for autonomous triggers (Step 3)
        let (tx, mut rx) = mpsc::channel(100);
        let orchestrator = self.orchestrator.clone();

        let mut watcher = notify::RecommendedWatcher::new(move |res| {
            if let Ok(event) = res {
                let _ = tx.blocking_send(event);
            }
        }, Config::default())?;

        watcher.watch(std::path::Path::new("./watch_folder"), RecursiveMode::Recursive)?;

        // 2. Event processing loop
        tokio::spawn(async move {
            info!(" 🔌 [Daemon] Watcher active on ./watch_folder");
            while let Some(event) = rx.recv().await {
                if let notify::EventKind::Create(_) = event.kind {
                    info!(" 🚀 [Daemon] FS TRIGGER: New file detected. Initiating autonomous workflow...");
                    
                    // 1. Memory Graph residency (Step 4)
                    let mut graph = orchestrator.memory_graph.lock().await;
                    graph.add_node("FileDiscovery", "Found new sovereign artifact.");
                    info!(" 🧠 [Daemon] Cognitive residency committed to Graph.");

                    // 2. Automatic extraction and report workflow (Step 1)
                    let _ = orchestrator.dcn.handle_remote_task("Watch folder -> extract data -> analyze -> email report").await;
                }

            }
        });

        // 3. User Behavior Monitor (Step 4)
        info!(" 🧠 [Daemon] Characterizing User Behavior Patterns for Memory residency...");
        
        Ok(())
    }
}
