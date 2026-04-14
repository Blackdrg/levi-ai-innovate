// backend/kernel/src/lib.rs
mod dag_executor;
mod memory_kernel;
mod intent_kernel;
mod dispatcher_kernel;
mod micro_kernel;

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use tokio::runtime::Runtime;
use tokio::sync::mpsc;
use std::sync::Arc;

#[pyclass]
struct LeviKernel {
    dag_kernel: dag_executor::DAGKernel,
    memory_kernel: memory_kernel::MemoryKernel,
    intent_kernel: intent_kernel::IntentKernel,
    dispatcher_kernel: dispatcher_kernel::DispatcherKernel,
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

        // Initialize components
        let mut kernel = Self {
            dag_kernel: dag_executor::DAGKernel::new(),
            memory_kernel: memory_kernel::MemoryKernel::new(),
            intent_kernel: intent_kernel::IntentKernel::new(),
            dispatcher_kernel: dispatcher_kernel::DispatcherKernel::new(8000.0),
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
            telemetry_tx: tel_tx, 
        };

        kernel.runtime.spawn(async move {
            micro_kernel_instance.run().await;
        });

        Ok(kernel)
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
}

#[pymodule]
fn levi_kernel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<LeviKernel>()?;
    Ok(())
}
