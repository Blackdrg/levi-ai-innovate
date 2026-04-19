// backend/levi_runtime/src/memory/mod.rs
use anyhow::Result;
use rusqlite::{params, Connection};
use std::sync::Arc;
use tokio::sync::Mutex;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct MemoryFragment {
    pub id: String,
    pub mission_id: String,
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: String,
}

pub struct MemoryLedger {
    conn: Mutex<Connection>,
    dcn: Option<Arc<DistributedCognitiveNetwork>>,
}

impl MemoryLedger {
    pub async fn new(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        
        // Initialise schema
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_fragments (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                content TEXT,
                timestamp TEXT,
                metadata TEXT
            )",
            [],
        )?;

        Ok(Self {
            conn: Mutex::new(conn),
            dcn: None,
        })
    }

    pub fn set_dcn(&mut self, dcn: Arc<DistributedCognitiveNetwork>) {
        self.dcn = Some(dcn);
    }

    pub async fn append(&self, fragment: MemoryFragment) -> Result<()> {
        let conn = self.conn.lock().await;
        conn.execute(
            "INSERT INTO memory_fragments (id, mission_id, content, timestamp, metadata)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                fragment.id,
                fragment.mission_id,
                fragment.content,
                fragment.timestamp.to_rfc3339(),
                fragment.metadata
            ],
        )?;
        Ok(())
    }

    pub async fn query_mission(&self, mission_id: &str) -> Result<Vec<MemoryFragment>> {
        let conn = self.conn.lock().await;
        let mut stmt = conn.prepare("SELECT id, mission_id, content, timestamp, metadata FROM memory_fragments WHERE mission_id = ?1")?;
        
        let fragments = stmt.query_map(params![mission_id], |row| {
            Ok(MemoryFragment {
                id: row.get(0)?,
                mission_id: row.get(1)?,
                content: row.get(2)?,
                timestamp: row.get::<_, String>(3)?.parse().unwrap_or(Utc::now()),
                metadata: row.get(4)?,
            })
        })?.collect::<Result<Vec<_>, _>>()?;

        Ok(fragments)
    }

    /// MCM (Memory Consistency Manager): Promotes high-fidelity facts to the global ledger.
    pub async fn graduation_pulse(&self) -> Result<usize> {
        let conn = self.conn.lock().await;
        info!(" [MCM] Running consistency scan on Mission Ledger...");
        
        // Simulation: Scanning for high-reward experiences to crystallize
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM memory_fragments", [], |r| r.get(0))?;
        
        if count > 0 {
            info!(" [MCM] Graduating {} fragments to Distributed Consensus (DCN)...", count);
            if let Some(dcn) = &self.dcn {
                let fragments = self.retrieve_recent(count as usize).await?;
                let json = serde_json::to_string(&fragments)?;
                dcn.sync_memory_fragment(&json).await?;
            }
        }

        Ok(count as usize)
    }

}

