// backend/kernel/src/main.rs
mod micro_kernel;
mod dag_executor;
mod memory_kernel;
mod intent_kernel;
mod dispatcher_kernel;

use std::sync::Arc;
use tokio::sync::mpsc;

#[tokio::main]
async fn main() {
    println!("🚀 LEVI-AI Microkernel starting up...");
    
    let (tx, rx) = mpsc::channel(100);
    
    let microkernel = micro_kernel::Microkernel {
        trusted_core: Arc::new(micro_kernel::TrustedCore {
            mission_router: micro_kernel::MissionRouter,
            resource_allocator: micro_kernel::ResourceAllocator,
            security_gate: micro_kernel::SecurityGate,
        }),
        agents: std::collections::HashMap::new(),
        message_rx: rx,
    };

    println!("✅ Microkernel online. Listening for IPC pulses...");
    
    // In a real implementation, we would start an IPC listener here that sends messages to `tx`.
    
    microkernel.run().await;
}
