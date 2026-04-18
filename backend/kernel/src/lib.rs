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
mod stdlib;
mod filesystem;
mod security_monitor;
mod bft_signer;
mod memory_paging;
mod network_stack;
mod signals;
mod ipc;
mod syscalls;

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
    network_stack: Arc<network_stack::SovereignNetworkStack>,
    mmu: Arc<memory_paging::VirtualMemoryManager>,
    signals: Arc<tokio::sync::Mutex<signals::SignalManager>>,
    ipc: Arc<ipc::SovereignIPC>,
    driver_registry: Arc<drivers::DriverRegistry>,
    security_monitor: Arc<security_monitor::SecurityMonitor>,
    bft_signer: Arc<bft_signer::BftSigner>,
    stdlib: Arc<stdlib::StdLib>,
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

        let boot_report = bootloader::Bootloader::boot();

        let process_manager = Arc::new(process_manager::ProcessManager::new());
        let memory_controller = Arc::new(memory_controller::MemoryController::new(process_manager.clone(), 1024));
        let scheduler = Arc::new(scheduler::MissionScheduler::new(16)); // 16-Core SMP Support
        let gpu_controller = Arc::new(gpu_controller::GpuController::new());
        let filesystem = Arc::new(filesystem::SovereignFS::new("sovereign.img".to_string()));
        let network_stack = Arc::new(network_stack::SovereignNetworkStack::new());
        let mmu = Arc::new(memory_paging::VirtualMemoryManager::new(16384));
        let signals = Arc::new(tokio::sync::Mutex::new(signals::SignalManager::new()));
        let ipc = Arc::new(ipc::SovereignIPC::new());
        let driver_registry = Arc::new(drivers::DriverRegistry::new());
        let security_monitor = Arc::new(security_monitor::SecurityMonitor::new());
        let bft_signer = Arc::new(bft_signer::BftSigner::new());

        let stdlib = Arc::new(stdlib::StdLib::new(
            process_manager.clone(),
            memory_controller.clone(),
            gpu_controller.clone(),
            bft_signer.clone(),
            filesystem.clone(),
        ));

        let kernel = Self {
            dag_kernel: dag_executor::DAGKernel::new(),
            memory_kernel: memory_kernel::MemoryKernel::new(),
            intent_kernel: intent_kernel::IntentKernel::new(),
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
            stdlib,
            boot_report: Some(boot_report),
            micro_tx: Some(tx),
            telemetry_rx: Some(tel_rx),
            runtime,
        };

        Ok(kernel)
    }

    fn send_ipc(&self, channel: String, from_pid: String, payload: Vec<u8>) -> PyResult<()> {
        let msg = ipc::IPCMessage { 
            from_pid, 
            payload,
            signature: Some([0u8; 64]), // Simulating a signed message from userspace
        };
        self.ipc.send(channel, msg)
            .map_err(|e| PyRuntimeError::new_err(e))?;
        Ok(())
    }

    fn receive_ipc(&self, channel: String) -> PyResult<Option<String>> {
        if let Some(msg) = self.ipc.receive(channel) {
            return Ok(Some(String::from_utf8_lossy(&msg.payload).to_string()));
        }
        Ok(None)
    }

    fn send_signal(&self, target_pid: String, sig_val: u8) -> PyResult<()> {
        let sig = match sig_val {
            9 => signals::Signal::SIGKILL,
            15 => signals::Signal::SIGTERM,
            _ => signals::Signal::SIGINT,
        };
        
        let sig_mgr = self.signals.clone();
        self.runtime.spawn(async move {
            let mut mgr = sig_mgr.lock().await;
            mgr.send_signal(target_pid, sig);
        });
        Ok(())
    }

    fn sys_call(&self, ring: u8, call_type_val: u32, args: Vec<u64>) -> PyResult<u64> {
        if ring > 3 { return Err(PyRuntimeError::new_err("CPU GPF")); }
        
        let call_type = match call_type_val {
            1 => syscalls::SysCallType::Write,
            62 => syscalls::SysCallType::Kill,
            _ => syscalls::SysCallType::Read,
        };

        syscalls::SysCallDispatcher::dispatch(call_type, args)
            .map_err(|e| PyRuntimeError::new_err(e))
    }
}


#[pymodule]
fn levi_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<LeviKernel>()?;
    Ok(())
}

