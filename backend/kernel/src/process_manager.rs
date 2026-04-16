// backend/kernel/src/process_manager.rs
use std::collections::HashMap;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use uuid::Uuid;
use serde::{Serialize, Deserialize};
use sysinfo::{Pid, ProcessExt, System, SystemExt};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum ProcessStatus {
    Starting,
    Running,
    Finished,
    Failed(String),
    Killed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessMetadata {
    pub id: String,
    pub name: String,
    pub pid: Option<u32>,
    pub status: ProcessStatus,
    pub memory_usage_kb: u64,
    pub cpu_usage_pct: f32,
    pub start_time: u64,
}

pub struct ProcessManager {
    processes: Arc<Mutex<HashMap<String, ManagedProcess>>>,
    sys: Arc<Mutex<System>>,
}

struct ManagedProcess {
    metadata: ProcessMetadata,
    child: Option<Child>,
}

impl ProcessManager {
    pub fn new() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();
        Self {
            processes: Arc::new(Mutex::new(HashMap::new())),
            sys: Arc::new(Mutex::new(sys)),
        }
    }

    pub fn spawn_task(&self, name: String, command: String, args: Vec<String>) -> Result<String, String> {
        let id = Uuid::new_v4().to_string();
        let mut child = Command::new(command)
            .args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn process: {}", e))?;

        let pid = child.id();
        let metadata = ProcessMetadata {
            id: id.clone(),
            name,
            pid: Some(pid),
            status: ProcessStatus::Running,
            memory_usage_kb: 0,
            cpu_usage_pct: 0.0,
            start_time: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        let mut processes = self.processes.lock().unwrap();
        processes.insert(id.clone(), ManagedProcess {
            metadata,
            child: Some(child),
        });

        Ok(id)
    }

    pub fn update_metrics(&self) {
        let mut sys = self.sys.lock().unwrap();
        sys.refresh_processes();
        
        let mut processes = self.processes.lock().unwrap();
        for proc in processes.values_mut() {
            if let Some(pid_val) = proc.metadata.pid {
                if let Some(p) = sys.process(Pid::from(pid_val as usize)) {
                    proc.metadata.memory_usage_kb = p.memory();
                    proc.metadata.cpu_usage_pct = p.cpu_usage();
                } else {
                    // Process might have exited
                    if let Some(mut child) = proc.child.take() {
                        match child.try_wait() {
                            Ok(Some(status)) => {
                                if status.success() {
                                    proc.metadata.status = ProcessStatus::Finished;
                                } else {
                                    proc.metadata.status = ProcessStatus::Failed(status.to_string());
                                }
                            },
                            _ => {
                                proc.metadata.status = ProcessStatus::Killed;
                            }
                        }
                    }
                }
            }
        }
    }

    pub fn get_process_list(&self) -> Vec<ProcessMetadata> {
        let processes = self.processes.lock().unwrap();
        processes.values().map(|p| p.metadata.clone()).collect()
    }

    pub fn kill_process(&self, id: String) -> Result<(), String> {
        let mut processes = self.processes.lock().unwrap();
        if let Some(proc) = processes.get_mut(&id) {
            if let Some(mut child) = proc.child.take() {
                child.kill().map_err(|e| e.to_string())?;
                proc.metadata.status = ProcessStatus::Killed;
                return Ok(());
            }
        }
        Err("Process not found or already dead".to_string())
    }
}
