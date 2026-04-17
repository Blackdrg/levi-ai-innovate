// backend/kernel/src/stdlib.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

/// Sovereign libc-lite: System Calls for LEVI-AI Agents.
/// Fulfills the 'Standard Library' requirement from diagnostic analysis.

#[derive(Debug, Serialize, Deserialize)]
pub enum SysCall {
    Alloc(u64),      // malloc equivalent
    Free(u64),       // free equivalent
    Write(String),   // stdout equivalent
    Exit(i32),       // process exit
    ReadClock,       // time syscall
}

pub struct StdLib {
    heap_map: Arc<Mutex<HashMap<u64, u64>>>, // ptr -> size
    next_ptr: Arc<Mutex<u64>>,
}

impl StdLib {
    pub fn new() -> Self {
        Self {
            heap_map: Arc::new(Mutex::new(HashMap::new())),
            next_ptr: Arc::new(Mutex::new(0x1000)),
        }
    }

    pub fn execute(&self, call: SysCall) -> Result<String, String> {
        match call {
            SysCall::Alloc(size) => {
                let mut map = self.heap_map.lock().unwrap();
                let mut ptr_gen = self.next_ptr.lock().unwrap();
                let ptr = *ptr_gen;
                map.insert(ptr, size);
                *ptr_gen += size;
                Ok(format!("0x{:X}", ptr))
            },
            SysCall::Free(ptr) => {
                let mut map = self.heap_map.lock().unwrap();
                if map.remove(&ptr).is_some() {
                    Ok("SUCCESS".to_string())
                } else {
                    Err("Invalid Pointer".to_string())
                }
            },
            SysCall::Write(msg) => {
                log::info!("[StdLib-OUT] {}", msg);
                Ok("OK".to_string())
            },
            SysCall::Exit(code) => {
                log::warn!("[StdLib] Agent process terminating with code {}", code);
                Ok("EXITED".to_string())
            },
            SysCall::ReadClock => {
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs();
                Ok(now.to_string())
            }
        }
    }
}
