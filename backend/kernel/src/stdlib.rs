// backend/kernel/src/stdlib.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

/// Sovereign libc-lite: System Calls for LEVI-AI Agents.
/// Fulfills the 'Standard Library' requirement from diagnostic analysis.

#[derive(Debug, Serialize, Deserialize)]
pub enum SysCall {
    MemReserve(u64),                                   // MEM_RESERVE
    WaveSpawn { name: String, cmd: String, args: Vec<String> }, // WAVE_SPAWN
    BftSign(Vec<u8>),                                 // BFT_SIGN
    RootJail(String),                                 // ROOT_JAIL
    VramGauge,                                         // VRAM_GAUGE
    Write(String),                                    // stdout
    Exit(i32),                                        // terminate
    ReadClock,                                        // gettimeofday
}

use crate::process_manager::ProcessManager;
use crate::memory_controller::MemoryController;
use crate::gpu_controller::GpuController;
use crate::bft_signer::BftSigner;

pub struct StdLib {
    pub process_manager: Arc<ProcessManager>,
    pub memory_controller: Arc<MemoryController>,
    pub gpu_controller: Arc<GpuController>,
    pub bft_signer: Arc<BftSigner>,
}

impl StdLib {
    pub fn new(
        pm: Arc<ProcessManager>, 
        mc: Arc<MemoryController>, 
        gc: Arc<GpuController>, 
        bs: Arc<BftSigner>
    ) -> Self {
        Self {
            process_manager: pm,
            memory_controller: mc,
            gpu_controller: gc,
            bft_signer: bs,
        }
    }

    pub fn execute(&self, call: SysCall) -> Result<String, String> {
        match call {
            SysCall::MemReserve(size) => {
                let addr = self.memory_controller.reserve_memory(size)?;
                Ok(format!("0x{:X}", addr))
            },
            SysCall::WaveSpawn { name, cmd, args } => {
                let uuid = self.process_manager.spawn_task(name, cmd, args)?;
                Ok(uuid)
            },
            SysCall::BftSign(payload) => {
                let sig = self.bft_signer.sign(&payload);
                Ok(hex::encode(sig.to_bytes()))
            },
            SysCall::RootJail(path) => {
                self.process_manager.set_jail_root(path);
                Ok("JAIL_ENFORCED".to_string())
            },
            SysCall::VramGauge => {
                let metrics = self.gpu_controller.get_metrics();
                Ok(serde_json::to_string(&metrics).unwrap())
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
