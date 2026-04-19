// backend/kernel/src/sovereign_executor.rs
//
// NATIVE SOVEREIGN EXECUTOR — DCN Heartbeat & Multi-node Verification
//
// ─────────────────────────────────────────────────────────────────────────────

use serde::{Serialize, Deserialize};
use std::time::{SystemTime, UNIX_EPOCH};
use std::sync::Arc;
use crate::bft_signer::BftSigner;

#[derive(Debug, Serialize, Deserialize)]
pub struct DcnHeartbeat {
    pub node_id: String,
    pub timestamp: u64,
    pub sequence: u64,
    pub term: u64,
    pub hash_root: String,
    pub signature: Option<Vec<u8>>,
}

pub struct SovereignExecutor {
    node_id: String,
    signer: Arc<BftSigner>,
    sequence: std::sync::atomic::AtomicU64,
}

impl SovereignExecutor {
    pub fn new(node_id: String, signer: Arc<BftSigner>) -> Self {
        Self {
            node_id,
            signer,
            sequence: std::sync::atomic::AtomicU64::new(0),
        }
    }

    /// Emit a signed Sovereign Mesh pulse (DCN Heartbeat).
    pub fn emit_heartbeat(&self, term: u64, hash_root: String) -> DcnHeartbeat {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        let seq = self.sequence.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        
        let mut pulse = DcnHeartbeat {
            node_id: self.node_id.clone(),
            timestamp,
            sequence: seq,
            term,
            hash_root,
            signature: None,
        };

        // Sign the pulse JSON
        let payload = serde_json::to_vec(&pulse).unwrap();
        let sig = self.signer.sign(&payload);
        pulse.signature = Some(sig.to_vec());

        pulse
    }

    /// Verify a signed pulse from a remote DCN node.
    pub fn verify_heartbeat(&self, pulse: &DcnHeartbeat, public_key: &[u8; 32]) -> bool {
        let mut pulse_no_sig = DcnHeartbeat {
            node_id: pulse.node_id.clone(),
            timestamp: pulse.timestamp,
            sequence: pulse.sequence,
            term: pulse.term,
            hash_root: pulse.hash_root.clone(),
            signature: None,
        };

        let payload = serde_json::to_vec(&pulse_no_sig).unwrap();
        
        if let Some(sig) = &pulse.signature {
             if sig.len() == 64 {
                 let mut sig_arr = [0u8; 64];
                 sig_arr.copy_from_slice(sig);
                 return self.signer.verify_remote(public_key, &payload, &sig_arr);
             }
        }
        false
    }
}
