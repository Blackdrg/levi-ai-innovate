// backend/kernel/src/memory_kernel.rs
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fact {
    pub id: String,
    pub content: String,
    pub metadata: String,
}

#[derive(Debug)]
pub enum Error {
    StorageError(String),
}

pub enum Tier {
    Redis,
    Postgres,
    Neo4j,
    FAISS,
    Tape,
}

pub struct MemoryKernel {
    pub tier_priorities: [Tier; 5],
    pub sync_threads: u32,
    pub batch_size: usize,
    pub telemetry_tx: Option<mpsc::Sender<String>>,
}

impl MemoryKernel {
    pub fn new() -> Self {
        Self {
            tier_priorities: [Tier::Redis, Tier::Postgres, Tier::Neo4j, Tier::FAISS, Tier::Tape],
            sync_threads: 4,
            batch_size: 1000,
            telemetry_tx: None,
        }
    }

    pub fn set_telemetry(&mut self, tx: mpsc::Sender<String>) {
        self.telemetry_tx = Some(tx);
    }

    async fn send_pulse(&self, msg: String) {
        if let Some(tx) = &self.telemetry_tx {
            let _ = tx.send(msg).await;
        }
    }

    // Async tier sync with batching
    pub async fn crystallize_batch(&self, facts: Vec<Fact>) -> Result<(), Error> {
        self.send_pulse(format!("MEM_CRYSTALLIZE_START: batch_size={}", facts.len())).await;
        
        // T0: Redis (async, no-wait)
        let f0 = facts.clone();
        tokio::spawn(async move {
            let _ = Self::write_tier0(f0).await;
        });
        
        // T1: Postgres (batched)
        self.write_tier1_batch(facts.clone()).await?;
        
        // T2: Neo4j (async)
        let f2 = facts.clone();
        tokio::spawn(async move {
            let _ = Self::write_tier2(f2).await;
        });
        
        // T3: FAISS (batched embeddings)
        self.write_tier3_batch(facts.clone()).await?;
        
        self.send_pulse(format!("MEM_CRYSTALLIZE_COMPLETE: id_hash={}", facts.get(0).map(|f| &f.id).unwrap_or(&"empty".to_string()))).await;
        
        Ok(())
    }

    async fn write_tier0(_facts: Vec<Fact>) -> Result<(), Error> {
        // Redis logic
        Ok(())
    }

    async fn write_tier1_batch(&self, _facts: Vec<Fact>) -> Result<(), Error> {
        // Postgres batched write
        Ok(())
    }

    async fn write_tier2(_facts: Vec<Fact>) -> Result<(), Error> {
        // Neo4j logic
        Ok(())
    }

    async fn write_tier3_batch(&self, _facts: Vec<Fact>) -> Result<(), Error> {
        // FAISS logic
        Ok(())
    }

    /// Synchronous adapter for PyO3: parse JSON facts string and log.
    /// Full async crystallization would require block_on() — deferred to a background task.
    pub fn sync_batch(&self, facts_json: &str) -> Result<(), String> {
        let facts: Vec<serde_json::Value> = serde_json::from_str(facts_json)
            .map_err(|e| format!("sync_batch parse error: {}", e))?;
        log::info!("[MemoryKernel] sync_batch: {} facts received for crystallization.", facts.len());
        // In production: spawn a blocking Tokio task to call crystallize_batch().
        Ok(())
    }
}

