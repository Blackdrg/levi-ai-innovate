mod micro_kernel;
mod dag_executor;
mod memory_kernel;
mod intent_kernel;
mod dispatcher_kernel;
mod process_manager;
mod memory_controller;
mod scheduler;
mod gpu_controller;
mod bootloader;
mod drivers;
mod stdlib;
mod filesystem;
mod security_monitor;
mod bft_signer;

use std::sync::Arc;
use tokio::sync::mpsc;
use crate::stdlib::SysCall;

#[tokio::main]
async fn main() {
    println!("🚀 LEVI-AI HAL-0 Kernel: Independent Boot Sequence...");
    
    let process_manager = Arc::new(process_manager::ProcessManager::new());
    let memory_controller = Arc::new(memory_controller::MemoryController::new(process_manager.clone(), 1024));
    let gpu_controller = Arc::new(gpu_controller::GpuController::new());
    let bft_signer = Arc::new(bft_signer::BftSigner::new());
    
    let stdlib = Arc::new(stdlib::StdLib::new(
        process_manager.clone(),
        memory_controller.clone(),
        gpu_controller.clone(),
        bft_signer.clone(),
    ));

    println!("✅ HAL-0 Subsystems Online.");

    // --- Syscall Self-Test ---
    println!("🧪 Test 1: MEM_RESERVE...");
    match stdlib.execute(SysCall::MemReserve(1024 * 1024)) {
        Ok(addr) => println!("   Result: OK (Address: {})", addr),
        Err(e) => println!("   Result: FAIL ({})", e),
    }

    println!("🧪 Test 2: BFT_SIGN...");
    let payload = b"HAL-0 GENESIS PULSE";
    match stdlib.execute(SysCall::BftSign(payload.to_vec())) {
        Ok(sig) => println!("   Result: OK (Signature: {})", sig),
        Err(e) => println!("   Result: FAIL ({})", e),
    }

    println!("🧪 Test 3: VRAM_GAUGE...");
    match stdlib.execute(SysCall::VramGauge) {
        Ok(json) => println!("   Result: OK (Metrics: {})", json),
        Err(e) => println!("   Result: FAIL ({})", e),
    }

    println!("🏁 HAL-0 Standalone Self-Test Complete.");
}
