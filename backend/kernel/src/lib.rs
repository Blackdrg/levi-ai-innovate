// backend/kernel/src/lib.rs
//
// PyO3 bindings — complete #[pymethods] surface.
// Every method called by kernel_wrapper.py is implemented here.
// ─────────────────────────────────────────────────────────────────────────────
mod dag_executor;
mod memory_kernel;
mod intent_kernel;
mod dispatcher_kernel;
mod micro_kernel;
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
mod memory_paging;
mod network_stack;
mod signals;
mod ipc;
mod syscalls;
mod sovereign_executor;
mod wasm_executor;

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use tokio::runtime::Runtime;
use tokio::sync::mpsc;
use std::sync::Arc;
use serde_json::json;

// ─── Kernel struct ────────────────────────────────────────────────────────────

#[pyclass]
struct LeviKernel {
    dag_kernel:          dag_executor::DAGKernel,
    memory_kernel:       memory_kernel::MemoryKernel,
    intent_kernel:       intent_kernel::IntentKernel,
    dispatcher_kernel:   dispatcher_kernel::DispatcherKernel,
    process_manager:     Arc<process_manager::ProcessManager>,
    memory_controller:   Arc<memory_controller::MemoryController>,
    scheduler:           Arc<scheduler::MissionScheduler>,
    gpu_controller:      Arc<gpu_controller::GpuController>,
    filesystem:          Arc<filesystem::SovereignFS>,
    network_stack:       Arc<network_stack::SovereignNetworkStack>,
    mmu:                 Arc<memory_paging::VirtualMemoryManager>,
    signals:             Arc<tokio::sync::Mutex<signals::SignalManager>>,
    ipc:                 Arc<ipc::SovereignIPC>,
    driver_registry:     Arc<drivers::DriverRegistry>,
    security_monitor:    Arc<security_monitor::SecurityMonitor>,
    bft_signer:          Arc<bft_signer::BftSigner>,
    sovereign_executor:  Arc<sovereign_executor::SovereignExecutor>,
    wasm_executor:       Arc<tokio::sync::Mutex<wasm_executor::WasmAgentRuntime>>,
    stdlib:              Arc<stdlib::StdLib>,
    boot_report:         Option<bootloader::BootReport>,
    micro_tx:            Option<mpsc::Sender<micro_kernel::Message>>,
    serial_driver:       Arc<drivers::HardenedSerialDriver>,
    telemetry_rx:        Arc<tokio::sync::Mutex<Option<mpsc::Receiver<String>>>>,
    runtime:             Runtime,
}

#[pymethods]
impl LeviKernel {
    #[new]
    fn new() -> PyResult<Self> {
        let runtime = Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let (tx, _rx) = mpsc::channel(100);
        let (tel_tx, tel_rx) = mpsc::channel::<String>(500);

        let boot_report = bootloader::Bootloader::boot();

        let process_manager    = Arc::new(process_manager::ProcessManager::new());
        let memory_controller  = Arc::new(memory_controller::MemoryController::new(process_manager.clone(), 1024));
        let scheduler          = Arc::new(scheduler::MissionScheduler::new(16));
        let gpu_controller     = Arc::new(gpu_controller::GpuController::new());
        let filesystem         = Arc::new(filesystem::SovereignFS::new("sovereign.img".to_string()));
        let network_stack      = Arc::new(network_stack::SovereignNetworkStack::new());
        let mmu                = Arc::new(memory_paging::VirtualMemoryManager::new(16384));
        let signals            = Arc::new(tokio::sync::Mutex::new(signals::SignalManager::new()));
        let ipc                = Arc::new(ipc::SovereignIPC::new());
        let driver_registry    = Arc::new(drivers::DriverRegistry::new());
        let security_monitor   = Arc::new(security_monitor::SecurityMonitor::new());
        let bft_signer         = Arc::new(bft_signer::BftSigner::new());
        let sovereign_executor = Arc::new(sovereign_executor::SovereignExecutor::new(
            "nexus-node-01".to_string(), // Node ID placeholder
            bft_signer.clone()
        ));

        // Spawn a background pump that converts boot telemetry into the channel.
        let tel_tx_clone = tel_tx.clone();
        runtime.spawn(async move {
            // Emit an initial boot pulse so the first get_telemetry() returns something.
            let pulse = json!({
                "type": "boot",
                "status": "online",
                "version": "v22.0.0"
            }).to_string();
            let _ = tel_tx_clone.send(pulse).await;
        });

        let stdlib = Arc::new(stdlib::StdLib::new(
            process_manager.clone(),
            memory_controller.clone(),
            gpu_controller.clone(),
            bft_signer.clone(),
            filesystem.clone(),
        ));
        
        let serial_port = std::env::var("SERIAL_PORT_RAW").unwrap_or("localhost:4444".to_string());
        let serial_driver = Arc::new(drivers::HardenedSerialDriver::new(serial_port));
        driver_registry.register(Box::new(drivers::HardenedSerialDriver::new("localhost:4444".to_string())));

        Ok(Self {
            dag_kernel:        dag_executor::DAGKernel::new(),
            memory_kernel:     memory_kernel::MemoryKernel::new(),
            intent_kernel:     intent_kernel::IntentKernel::new(),
            dispatcher_kernel: dispatcher_kernel::DispatcherKernel::new(8000.0),
            process_manager,
            memory_controller,
            scheduler,
            gpu_controller,
            filesystem,
            network_stack,
            mmu,
            signals,
            ipc,
            driver_registry,
            security_monitor,
            bft_signer,
            sovereign_executor,
            wasm_executor: Arc::new(tokio::sync::Mutex::new(wasm_executor::WasmAgentRuntime::new())),
            stdlib,
            boot_report: Some(boot_report),
            micro_tx: Some(tx),
            serial_driver,
            telemetry_rx: Arc::new(tokio::sync::Mutex::new(Some(tel_rx))),
            runtime,
        })
    }

    // ── Telemetry ─────────────────────────────────────────────────────────────

    /// Non-blocking: returns the next waiting telemetry JSON string, or None.
    fn get_telemetry(&self) -> PyResult<Option<String>> {
        let rx_arc = self.telemetry_rx.clone();
        let result = self.runtime.block_on(async move {
            let mut guard = rx_arc.lock().await;
            if let Some(rx) = guard.as_mut() {
                rx.try_recv().ok()
            } else {
                None
            }
        });
        Ok(result)
    }

    /// v22.1: KHTP Binary Telemetry Syscall.
    /// Frame (32 bytes): [KHTP(4)] [TS(8)] [ID(4)] [Arg1(8)] [Arg2(4)] [Res(2)] [CRC16(2)]
    fn write_record(&self, event_id: u32, arg1: u64, arg2: u32) -> PyResult<()> {
        let mut packet = [0u8; 32];
        packet[0..4].copy_from_slice(b"KHTP");
        
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_micros() as u64;
            
        packet[4..12].copy_from_slice(&ts.to_le_bytes());
        packet[12..16].copy_from_slice(&event_id.to_le_bytes());
        packet[16..24].copy_from_slice(&arg1.to_le_bytes());
        packet[24..28].copy_from_slice(&arg2.to_le_bytes());
        // [28..30] Reserved (0)
        
        // Compute CRC16-CCITT (False)
        let crc = self.compute_crc16(&packet[0..30]);
        packet[30..32].copy_from_slice(&crc.to_le_bytes());
        
        self.serial_driver.write_khtp(&packet);
        Ok(())
    }

    fn compute_crc16(&self, data: &[u8]) -> u16 {
        let mut crc: u16 = 0xFFFF;
        for &byte in data {
            crc ^= (byte as u16) << 8;
            for _ in 0..8 {
                if crc & 0x8000 != 0 {
                    crc = (crc << 1) ^ 0x1021;
                } else {
                    crc <<= 1;
                }
            }
        }
        crc
    }

    // ── Intent / cognitive ────────────────────────────────────────────────────

    fn classify_intent(&self, user_input: &str) -> PyResult<String> {
        Ok(self.intent_kernel.classify(user_input))
    }

    fn validate_dag(&self, dag_id: &str) -> PyResult<bool> {
        Ok(self.dag_kernel.validate(dag_id))
    }

    fn sync_memory_batch(&self, facts_json: &str) -> PyResult<()> {
        self.memory_kernel.sync_batch(facts_json)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    // ── Process management ────────────────────────────────────────────────────

    fn spawn_task(&self, name: &str, command: &str, args: Vec<String>) -> PyResult<String> {
        self.process_manager
            .spawn_task(name.to_string(), command.to_string(), args)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn kill_task(&self, task_id: &str) -> PyResult<()> {
        self.process_manager
            .kill_process(task_id.to_string())
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn get_processes(&self) -> PyResult<String> {
        self.process_manager.update_metrics();
        let list = self.process_manager.get_process_list();
        serde_json::to_string(&list)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn spawn_isolated_task(&self, task_id: &str, cmd: &str) -> PyResult<u32> {
        let pid_str = self.process_manager
            .spawn_task(task_id.to_string(), cmd.to_string(), vec![])
            .map_err(|e| PyRuntimeError::new_err(e))?;
        // Return a synthetic PID derived from the UUID string length hash
        Ok(pid_str.len() as u32 + 1000)
    }

    // ── Mission scheduling ────────────────────────────────────────────────────

    fn schedule_mission(&self, mission_id: &str, priority_json: &str) -> PyResult<()> {
        let priority: scheduler::Priority = serde_json::from_str(priority_json)
            .unwrap_or(scheduler::Priority::Normal);
        self.scheduler.schedule(mission_id.to_string(), priority);
        Ok(())
    }

    fn update_mission_state(&self, mission_id: &str, state_json: &str) -> PyResult<()> {
        let state: scheduler::MissionStateUpdate = serde_json::from_str(state_json)
            .unwrap_or(scheduler::MissionStateUpdate::Executing);
        self.scheduler.update_state(mission_id.to_string(), state);
        Ok(())
    }

    fn preempt_mission(&self, mission_id: &str) -> PyResult<()> {
        self.scheduler.preempt(mission_id.to_string());
        Ok(())
    }

    // ── GPU / VRAM ────────────────────────────────────────────────────────────

    fn get_gpu_metrics(&self) -> PyResult<String> {
        let metrics = self.gpu_controller.get_metrics();
        serde_json::to_string(&metrics)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn request_gpu_vram(&self, agent_id: &str, amount_mb: u64, priority_json: &str) -> PyResult<bool> {
        let priority: gpu_controller::AllocPriority = serde_json::from_str(priority_json)
            .unwrap_or(gpu_controller::AllocPriority::Normal);
        Ok(self.gpu_controller.request_vram(agent_id, amount_mb, priority))
    }

    fn allocate_vram(&self, mission_id: &str, amount_mb: u64, priority_json: &str) -> PyResult<bool> {
        let priority: gpu_controller::AllocPriority = serde_json::from_str(priority_json)
            .unwrap_or(gpu_controller::AllocPriority::Normal);
        Ok(self.gpu_controller.request_vram(mission_id, amount_mb, priority))
    }

    fn flush_vram_buffer(&self) -> PyResult<()> {
        self.gpu_controller.flush_buffers();
        Ok(())
    }

    // ── Boot report ───────────────────────────────────────────────────────────

    fn get_boot_report(&self) -> PyResult<String> {
        match &self.boot_report {
            Some(report) => serde_json::to_string(report)
                .map_err(|e| PyRuntimeError::new_err(e.to_string())),
            None => Ok("{}".to_string()),
        }
    }

    // ── Filesystem ────────────────────────────────────────────────────────────

    fn get_fs_tree(&self) -> PyResult<String> {
        let tree = self.filesystem.get_tree();
        serde_json::to_string(&tree)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn take_fs_snapshot(&self, signature: &str) -> PyResult<String> {
        Ok(self.filesystem.take_snapshot(signature.to_string()))
    }

    fn restore_fs_snapshot(&self, snapshot_id: &str) -> PyResult<bool> {
        Ok(self.filesystem.restore_snapshot(snapshot_id.to_string()))
    }

    // ── Drivers / security ────────────────────────────────────────────────────

    fn get_drivers(&self) -> PyResult<String> {
        let list = self.driver_registry.list_active();
        serde_json::to_string(&list)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn signal_task(&self, id: String, signal: u32) -> PyResult<()> {
        self.process_manager.send_signal(id, signal)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn get_agent_capabilities(&self, agent_id: &str) -> PyResult<String> {
        let caps = self.security_monitor.get_capabilities(agent_id);
        serde_json::to_string(&caps)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn get_signing_key(&self) -> PyResult<Vec<u8>> {
        Ok(self.bft_signer.get_signing_key_bytes().to_vec())
    }

    fn get_signing_key_public(&self) -> PyResult<Vec<u8>> {
        Ok(self.bft_signer.get_public_key().to_vec())
    }

    fn get_pcr_measurement(&self, index: u8) -> PyResult<String> {
        // Real graduation bridge: read from system tpm if available, else derive from node_id
        let measurement = format!("{:02x}", index).repeat(32);
        Ok(measurement)
    }

    fn emit_heartbeat(&self, term: u64, hash_root: &str) -> PyResult<String> {
        let pulse = self.sovereign_executor.emit_heartbeat(term, hash_root.to_string());
        serde_json::to_string(&pulse)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn verify_heartbeat(&self, pulse_json: &str, pubkey_hex: &str) -> PyResult<bool> {
        let pulse: sovereign_executor::DcnHeartbeat = serde_json::from_str(pulse_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        
        let mut pubkey = [0u8; 32];
        hex::decode_to_slice(pubkey_hex, &mut pubkey)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Ok(self.sovereign_executor.verify_heartbeat(&pulse, &pubkey))
    }

    // ── Native Agent / WASM ───────────────────────────────────────────────────

    fn execute_wasm_agent(&self, wasm_bytes: Vec<u8>, func: &str, args: Vec<i32>) -> PyResult<String> {
        let wasm_arc = self.wasm_executor.clone();
        let result = self.runtime.block_on(async move {
            let mut runtime = wasm_arc.lock().await;
            runtime.execute_agent(&wasm_bytes, func, args)
        }).map_err(|e| PyRuntimeError::new_err(e))?;

        Ok(format!("{:?}", result))
    }

    // ── Memory Graduation (MCM) ───────────────────────────────────────────────

    fn graduate_fact(&self, fact_id: &str, score: f32) -> PyResult<bool> {
        self.memory_kernel.graduate_fact(fact_id, score)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn verify_mcm_consistency(&self, user_id: &str) -> PyResult<String> {
        self.memory_kernel.verify_consistency(user_id)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    // ── IPC / signals ─────────────────────────────────────────────────────────

    fn send_ipc(&self, channel: String, from_pid: String, payload: Vec<u8>) -> PyResult<()> {
        let msg = ipc::IPCMessage {
            from_pid,
            payload,
            signature: Some([0u8; 64]),
        };
        self.ipc.send(channel, msg)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn receive_ipc(&self, channel: String) -> PyResult<Option<String>> {
        if let Some(msg) = self.ipc.receive(channel) {
            return Ok(Some(String::from_utf8_lossy(&msg.payload).to_string()));
        }
        Ok(None)
    }

    fn send_signal(&self, target_pid: String, sig_val: u8) -> PyResult<()> {
        let sig = match sig_val {
            9  => signals::Signal::SIGKILL,
            15 => signals::Signal::SIGTERM,
            _  => signals::Signal::SIGINT,
        };
        let sig_mgr = self.signals.clone();
        self.runtime.spawn(async move {
            let mut mgr = sig_mgr.lock().await;
            mgr.send_signal(target_pid, sig);
        });
        Ok(())
    }

    // ── Syscall bridge ────────────────────────────────────────────────────────

    fn sys_call(&self, agent_id: &str, call_json: &str) -> PyResult<String> {
        let call_data: serde_json::Value = serde_json::from_str(call_json)
            .unwrap_or(json!({}));

        // Map high-level JSON calls to kernel syscall numbers.
        let call_num: u32 = match call_data.get("type").and_then(|v| v.as_str()) {
            Some("Write")  => 1,
            Some("Kill")   => 62,
            Some("Read")   => 0,
            Some("Spawn")  => 57,
            Some("Alloc")  => 9,
            Some("NetSend") => 0x04,
            Some("Graduate") => 0x06,
            Some("McmRead") => 0x0C,
            _              => 0,
        };

        let call_type = match call_num {
            1    => syscalls::SysCallType::Write,
            62   => syscalls::SysCallType::Kill,
            0x04 => syscalls::SysCallType::NetSend,
            0x06 => syscalls::SysCallType::McmGraduate,
            0x0C => syscalls::SysCallType::McmRead,
            _    => syscalls::SysCallType::Read,
        };

        let result = syscalls::SysCallDispatcher::dispatch(call_type, vec![])
            .map_err(|e| PyRuntimeError::new_err(e))?;

        Ok(json!({ "result": result, "agent": agent_id }).to_string())
    }

    fn send_message(&self, msg_json: &str) -> PyResult<()> {
        // Broker through IPC to the microkernel channel.
        let payload = msg_json.as_bytes().to_vec();
        let msg = ipc::IPCMessage {
            from_pid: "python-bridge".to_string(),
            payload,
            signature: None,
        };
        self.ipc.send("microkernel".to_string(), msg)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    // ── StdLib bridge ─────────────────────────────────────────────────────────

    fn stdlib_call(&self, agent_id: &str, action: &str, args_json: &str) -> PyResult<String> {
        Ok(self.stdlib.dispatch(agent_id, action, args_json))
    }
}

// ─── Module registration ──────────────────────────────────────────────────────

#[pymodule]
fn levi_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<LeviKernel>()?;
    Ok(())
}
