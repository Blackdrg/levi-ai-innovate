// backend/kernel/src/ipc.rs
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IPCMessage {
    pub from_pid: String,
    pub payload: Vec<u8>,
}

pub struct SovereignIPC {
    channels: Arc<Mutex<HashMap<String, VecDeque<IPCMessage>>>>, // Channel Name -> Messages
    shared_memory: Arc<Mutex<HashMap<u64, Vec<u8>>>>, // Physical Addr -> Data
}

impl SovereignIPC {
    pub fn new() -> Self {
        Self {
            channels: Arc::new(Mutex::new(HashMap::new())),
            shared_memory: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn send(&self, channel: String, msg: IPCMessage) {
        let mut channels = self.channels.lock().unwrap();
        channels.entry(channel).or_insert(VecDeque::new()).push_back(msg);
    }

    pub fn receive(&self, channel: String) -> Option<IPCMessage> {
        let mut channels = self.channels.lock().unwrap();
        channels.get_mut(&channel)?.pop_front()
    }

    pub fn shm_write(&self, addr: u64, data: Vec<u8>) {
        let mut shm = self.shared_memory.lock().unwrap();
        shm.insert(addr, data);
    }

    pub fn shm_read(&self, addr: u64) -> Option<Vec<u8>> {
        let shm = self.shared_memory.lock().unwrap();
        shm.get(&addr).cloned()
    }
}
