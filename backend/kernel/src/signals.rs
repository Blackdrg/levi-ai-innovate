// backend/kernel/src/signals.rs
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum Signal {
    SIGHUP = 1,
    SIGINT = 2,
    SIGQUIT = 3,
    SIGILL = 4,
    SIGTRAP = 5,
    SIGABRT = 6,
    SIGBUS = 7,
    SIGFPE = 8,
    SIGKILL = 9,
    SIGSEGV = 11,
    SIGTERM = 15,
}

pub struct SignalManager {
    pub pending_signals: std::collections::HashMap<String, Vec<Signal>>, // ProcessID -> Signals
}

impl SignalManager {
    pub fn new() -> Self {
        Self {
            pending_signals: std::collections::HashMap::new(),
        }
    }

    pub fn send_signal(&mut self, target_id: String, sig: Signal) {
        log::warn!("⚡ [Kernel] Signal {:?} sent to process {}", sig, target_id);
        self.pending_signals.entry(target_id).or_insert(Vec::new()).push(sig);
    }

    pub fn poll_signals(&mut self, target_id: String) -> Vec<Signal> {
        self.pending_signals.remove(&target_id).unwrap_or_default()
    }
}
