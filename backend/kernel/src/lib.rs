// backend/kernel/src/lib.rs
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
mod filesystem;
mod security_monitor;

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use tokio::runtime::Runtime;
use tokio::sync::mpsc;
use std::sync::Arc;
use std::time::Duration;

#[pyclass]
struct LeviKernel {
    dag_kernel: dag_executor::DAGKernel,
    memory_kernel: memory_kernel::MemoryKernel,
    intent_kernel: intent_kernel::IntentKernel,
    dispatcher_kernel: dispatcher_kernel::DispatcherKernel,
    process_manager: Arc<process_manager::ProcessManager>,
    memory_controller: Arc<memory_controller::MemoryController>,
    scheduler: Arc<scheduler::MissionScheduler>,
    gpu_controller: Arc<gpu_controller::GpuController>,
    filesystem: Arc<filesystem::SovereignFS>,
    driver_registry: Arc<drivers::DriverRegistry>,
    boot_report: Option<bootloader::BootReport>,
    micro_tx: Option<mpsc::Sender<micro_kernel::Message>>,
    telemetry_rx: Option<mpsc::Receiver<String>>,
    runtime: Runtime,
}

#[pymethods]
impl LeviKernel {
    #[new]
    fn new() -> PyResult<Self> {
        let runtime = Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let (tx, rx) = mpsc::channel(100);
        let (tel_tx, tel_rx) = mpsc::channel(500);

        // 🚀 Level 3: Sovereign Boot Sequence
        let boot_report = bootloader::Bootloader::boot();

        let process_manager = Arc::new(process_manager::ProcessManager::new());
        let memory_controller = Arc::new(memory_controller::MemoryController::new(process_manager.clone(), 1024));
        let scheduler = Arc::new(scheduler::MissionScheduler::new());
        let gpu_controller = Arc::new(gpu_controller::GpuController::new());
        let filesystem = Arc::new(filesystem::SovereignFS::new());
        let driver_registry = Arc::new(drivers::DriverRegistry::new());

        // Register default HAL drivers
        driver_registry.register(Box::new(drivers::VirtualMemoryDriver { total_vmem: 16384 }));

        // Initialize components
        let mut kernel = Self {
            dag_kernel: dag_executor::DAGKernel::new(),
            memory_kernel: memory_kernel::MemoryKernel::new(),
            intent_kernel: intent_kernel::IntentKernel::new(),
            dispatcher_kernel: dispatcher_kernel::DispatcherKernel::new(8000.0),
            process_manager,
            memory_controller,
            scheduler,
            gpu_controller,
            filesystem,
            driver_registry,
            boot_report: Some(boot_report),
            micro_tx: Some(tx),
            telemetry_rx: Some(tel_rx),
            runtime,
        };

        // Wire telemetry to memory kernel
        kernel.memory_kernel.set_telemetry(tel_tx.clone());

        // Spawn Microkernel in background
        let micro_core = Arc::new(micro_kernel::TrustedCore {
            mission_router: micro_kernel::MissionRouter,
            resource_allocator: micro_kernel::ResourceAllocator,
            security_gate: micro_kernel::SecurityGate,
        });

        let mut micro_kernel_instance = micro_kernel::Microkernel {
            trusted_core: micro_core,
            agents: std::collections::HashMap::new(),
            message_rx: rx,
            telemetry_tx: tel_tx.clone(), 
        };

        kernel.runtime.spawn(async move {
            micro_kernel_instance.run().await;
        });

        // Spawn resource monitor loop
        let pm_clone = kernel.process_manager.clone();
        let mc_clone = kernel.memory_controller.clone();
        let sch_clone = kernel.scheduler.clone();
        let gpu_clone = kernel.gpu_controller.clone();
        let dr_clone = kernel.driver_registry.clone();
        let tel_tx_clone = tel_tx.clone();
        kernel.runtime.spawn(async move {
            loop {
                pm_clone.update_metrics();
                mc_clone.enforce_limits();
                
                // Emit system health pulse
                let processes = pm_clone.get_process_list();
                let tasks = sch_clone.get_all_tasks();
                let gpu = gpu_clone.get_metrics();
                let drivers = dr_clone.list_drivers();
                
                let pulse = serde_json::json!({
                    "type": "SovereignOS_HealthPulse",
                    "kernel_state": "GRADUATED",
                    "processes": processes,
                    "missions": tasks,
                    "gpu": gpu,
                    "hal_drivers": drivers
                });

                if let Ok(json) = serde_json::to_string(&pulse) {
                    let _ = tel_tx_clone.send(json).await;
                }
                
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
        });

        Ok(kernel)
    }

    fn get_boot_report(&self) -> PyResult<String> {
        if let Some(report) = &self.boot_report {
            return Ok(serde_json::to_string(report).unwrap());
        }
        Err(PyRuntimeError::new_err("No boot report found"))
    }

    fn get_fs_tree(&self) -> PyResult<String> {
        let tree = self.filesystem.get_tree();
        Ok(serde_json::to_string(&tree).unwrap())
    }

    fn get_drivers(&self) -> PyResult<String> {
        let drivers = self.driver_registry.list_drivers();
        Ok(serde_json::to_string(&drivers).unwrap())
    }

    fn get_agent_capabilities(&self, _agent_id: String) -> PyResult<String> {
        // Return default caps for now
        let caps = security_monitor::SecurityMonitor::default_agent_caps();
        Ok(serde_json::to_string(&caps).unwrap())
    }

    fn schedule_mission(&self, id: String, priority_json: String) -> PyResult<()> {
        let priority: scheduler::MissionPriority = serde_json::from_str(&priority_json)
            .map_err(|e| PyRuntimeError::new_err(format!("Invalid priority: {}", e)))?;
        self.scheduler.schedule(id, priority);
        Ok(())
    }

    fn update_mission_state(&self, id: String, state_json: String) -> PyResult<()> {
        let state: scheduler::MissionState = serde_json::from_str(&state_json)
            .map_err(|e| PyRuntimeError::new_err(format!("Invalid state: {}", e)))?;
        self.scheduler.update_state(id, state);
        Ok(())
    }

    fn get_mission_status(&self, id: String) -> PyResult<Option<String>> {
        if let Some(state) = self.scheduler.get_status(id) {
            return Ok(Some(serde_json::to_string(&state).unwrap()));
        }
        Ok(None)
    }

    fn get_gpu_metrics(&self) -> PyResult<String> {
        let metrics = self.gpu_controller.get_metrics();
        Ok(serde_json::to_string(&metrics).unwrap())
    }

    fn request_gpu_vram(&self, agent_id: String, amount_mb: u64) -> PyResult<bool> {
        match self.gpu_controller.request_vram(agent_id, amount_mb) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    fn spawn_task(&self, name: String, command: String, args: Vec<String>) -> PyResult<String> {
        self.process_manager.spawn_task(name, command, args)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn kill_task(&self, id: String) -> PyResult<()> {
        self.process_manager.kill_process(id)
            .map_err(|e| PyRuntimeError::new_err(e))
    }

    fn get_processes(&self) -> PyResult<String> {
        let processes = self.process_manager.get_process_list();
        serde_json::to_string(&processes)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn get_telemetry(&mut self) -> PyResult<Option<String>> {
        if let Some(rx) = &mut self.telemetry_rx {
             match rx.try_recv() {
                 Ok(msg) => Ok(Some(msg)),
                 Err(mpsc::error::TryRecvError::Empty) => Ok(None),
                 Err(e) => Err(PyRuntimeError::new_err(format!("Telemetry channel error: {}", e))),
             }
        } else {
             Ok(None)
        }
    }

    fn send_message(&self, msg_json: String) -> PyResult<()> {
        let msg: micro_kernel::Message = serde_json::from_str(&msg_json)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to parse message: {}", e)))?;
        
        if let Some(tx) = &self.micro_tx {
            let tx_clone = tx.clone();
            self.runtime.block_on(async move {
                let _ = tx_clone.send(msg).await;
            });
        }
        Ok(())
    }

    fn classify_intent(&mut self, input: String) -> PyResult<String> {
        match self.intent_kernel.classify_intent(&input) {
            Ok(intent) => Ok(intent.name),
            Err(e) => Err(PyRuntimeError::new_err(format!("{:?}", e))),
        }
    }

    fn validate_dag(&self, dag_id: String) -> PyResult<bool> {
        match self.dag_kernel.validate_dag(&dag_id) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    fn sync_memory_batch(&self, facts_json: String) -> PyResult<()> {
        let facts: Vec<memory_kernel::Fact> = serde_json::from_str(&facts_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            
        self.runtime.block_on(async {
            self.memory_kernel.crystallize_batch(facts).await
                .map_err(|e| PyRuntimeError::new_err(format!("{:?}", e)))
        })
    }

    // --- Phase 4: Hardening & Optimization ---

    fn allocate_vram(&self, mission_id: String, amount_mb: u32) -> PyResult<bool> {
        match self.gpu_controller.request_vram(mission_id, amount_mb as u64) {
            Ok(_) => Ok(true),
            Err(e) => {
                log::warn!("[Kernel] VRAM allocation failed for {}: {}", mission_id, e);
                Ok(false)
            }
        }
    }

    fn spawn_isolated_task(&self, task_id: String, cmd: String) -> PyResult<u32> {
        let parts: Vec<&str> = cmd.split_whitespace().collect();
        if parts.is_empty() {
            return Err(PyRuntimeError::new_err("Empty command"));
        }
        let command = parts[0].to_string();
        let args: Vec<String> = parts[1..].iter().map(|s| s.to_string()).collect();

        // 🛡️ Phase 4 isolation: The process is spawned by our TaskManager/ProcessManager
        // which enforces resource limits via the MemoryController loop.
        let uuid = self.process_manager.spawn_task(task_id.clone(), command, args)
            .map_err(|e| PyRuntimeError::new_err(e))?;
            
        let list = self.process_manager.get_process_list();
        if let Some(proc) = list.iter().find(|p| p.id == uuid) {
            if let Some(pid) = proc.pid {
                log::info!("🚀 [Kernel] Isolated task spawned: {} (PID: {})", task_id, pid);
                return Ok(pid);
            }
        }
        
        Err(PyRuntimeError::new_err("Process spawned but PID missing"))
    }
}

#[pymodule]
fn levi_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<LeviKernel>()?;
    Ok(())
}
