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
use axum::{
    routing::{get, post},
    Json, Router, extract::State,
};
use serde::{Deserialize, Serialize};
use crate::stdlib::{StdLib, SysCall};

struct AppState {
    stdlib: Arc<StdLib>,
}

#[tokio::main]
async fn main() {
    println!("🚀 LEVI-AI HAL-0 Kernel: Awakening Native Runtime...");

    let process_manager = Arc::new(process_manager::ProcessManager::new());
    let memory_controller = Arc::new(memory_controller::MemoryController::new(process_manager.clone(), 1024));
    let gpu_controller = Arc::new(gpu_controller::GpuController::new());
    let bft_signer = Arc::new(bft_signer::BftSigner::new());
    let filesystem = Arc::new(filesystem::SovereignFS::new());
    
    let stdlib = Arc::new(stdlib::StdLib::new(
        process_manager.clone(),
        memory_controller.clone(),
        gpu_controller.clone(),
        bft_signer.clone(),
        filesystem.clone(),
    ));

    let state = Arc::new(AppState {
        stdlib: stdlib.clone(),
    });

    // --- Build API Router ---
    let app = Router::new()
        .route("/status", get(get_status))
        .route("/mission/admit", post(admit_mission))
        .route("/syscall", post(execute_syscall))
        .with_state(state);

    println!("✅ HAL-0 Subsystems Online.");
    println!("📡 Listening on http://127.0.0.1:8001");

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8001").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

#[derive(Serialize)]
struct StatusResponse {
    status: String,
    kernel_version: String,
    ring: u32,
}

async fn get_status() -> Json<StatusResponse> {
    Json(StatusResponse {
        status: "SOVEREIGN".to_string(),
        kernel_version: "17.0.0".to_string(),
        ring: 0,
    })
}

#[derive(Deserialize)]
struct MissionRequest {
    task: String,
}

#[derive(Serialize)]
struct MissionResponse {
    status: String,
    mission_id: String,
}

async fn admit_mission(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<MissionRequest>,
) -> Json<MissionResponse> {
    println!("🛡️ [Kernel] BFT GATE: Admitting mission: {}", payload.task);
    
    // Simulate mission admission logic
    Json(MissionResponse {
        status: "admitted".to_string(),
        mission_id: uuid::Uuid::new_v4().to_string(),
    })
}

#[derive(Deserialize)]
struct SyscallRequest {
    call: SysCall,
}

#[derive(Serialize)]
struct SyscallResponse {
    result: String,
}

async fn execute_syscall(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<SyscallRequest>,
) -> Json<SyscallResponse> {
    match state.stdlib.execute(payload.call) {
        Ok(res) => Json(SyscallResponse { result: res }),
        Err(e) => Json(SyscallResponse { result: format!("ERROR: {}", e) }),
    }
}
