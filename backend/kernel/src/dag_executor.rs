// backend/kernel/src/dag_executor.rs
use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use tokio::sync::mpsc;

pub type TaskId = String;

#[derive(Debug, Serialize, Deserialize)]
pub struct Task {
    pub id: TaskId,
    pub name: String,
    pub dependencies: Vec<TaskId>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DAG {
    pub id: String,
    pub tasks: Vec<Task>,
}

#[derive(Debug)]
pub enum Error {
    CycleError,
    NotFound,
    ExecutionError(String),
}

pub struct WaveResult {
    pub task_id: TaskId,
    pub status: String,
}

pub struct DAGKernel {
    pub cycle_cache: HashMap<String, bool>,  // Pre-computed acyclicity
    pub wave_order: HashMap<String, Vec<Vec<TaskId>>>, // Pre-computed wave order
    pub vram_map: HashMap<TaskId, f32>,      // Pre-computed VRAM requirements
}

impl DAGKernel {
    pub fn new() -> Self {
        Self {
            cycle_cache: HashMap::new(),
            wave_order: HashMap::new(),
            vram_map: HashMap::new(),
        }
    }

    // O(1) cycle detection (cached)
    pub fn validate_dag(&self, dag_id: &str) -> Result<(), Error> {
        if let Some(&is_acyclic) = self.cycle_cache.get(dag_id) {
            return if is_acyclic { Ok(()) } else { Err(Error::CycleError) };
        }
        // Fallback: DFS (Simulated)
        Ok(())
    }

    /// Simplified adapter for lib.rs: returns bool.
    pub fn validate(&self, dag_id: &str) -> bool {
        self.validate_dag(dag_id).is_ok()
    }


    // Kahn's algorithm for O(V+E) cycle detection and wave generation
    pub fn compute_acyclicity(&mut self, dag: &DAG) -> Result<(), Error> {
        let mut in_degree: HashMap<TaskId, usize> = HashMap::new();
        let mut adj: HashMap<TaskId, Vec<TaskId>> = HashMap::new();
        
        for task in &dag.tasks {
            in_degree.entry(task.id.clone()).or_insert(0);
            for dep in &task.dependencies {
                adj.entry(dep.clone()).or_insert(vec![]).push(task.id.clone());
                *in_degree.entry(task.id.clone()).or_insert(0) += 1;
            }
        }

        let mut queue: Vec<TaskId> = in_degree.iter()
            .filter(|&(_, &v)| v == 0)
            .map(|(k, _)| k.clone())
            .collect();

        let mut waves: Vec<Vec<TaskId>> = Vec::new();
        let mut processed_count = 0;

        while !queue.is_empty() {
            let mut current_wave = Vec::new();
            let mut next_queue = Vec::new();

            for task_id in queue {
                current_wave.push(task_id.clone());
                processed_count += 1;
                
                if let Some(neighbors) = adj.get(&task_id) {
                    for neighbor in neighbors {
                        let degree = in_degree.get_mut(neighbor).unwrap();
                        *degree -= 1;
                        if *degree == 0 {
                            next_queue.push(neighbor.clone());
                        }
                    }
                }
            }
            waves.push(current_wave);
            queue = next_queue;
        }

        let is_acyclic = processed_count == dag.tasks.len();
        self.cycle_cache.insert(dag.id.clone(), is_acyclic);
        if is_acyclic {
            self.wave_order.insert(dag.id.clone(), waves);
            Ok(())
        } else {
            Err(Error::CycleError)
        }
    }

    // Pre-scheduled wave dispatch
    pub async fn dispatch_waves(&self, dag: &DAG) -> Result<Vec<WaveResult>, Error> {
        let waves = self.wave_order.get(&dag.id).ok_or(Error::NotFound)?;
        
        let mut all_results = Vec::new();

        for wave in waves {
            // Parallel dispatch with VRAM guards (Simulated)
            let mut handles = Vec::new();
            for task_id in wave {
                let vram_needed = self.vram_map.get(task_id).unwrap_or(&1.0);
                // In a real implementation, this would interact with a dispatcher
                let task_id_clone = task_id.clone();
                handles.push(tokio::spawn(async move {
                    // Simulate execution
                    WaveResult { task_id: task_id_clone, status: "completed".to_string() }
                }));
            }
            
            // Wait for wave completion
            let results = futures::future::join_all(handles).await;
            for res in results {
                if let Ok(r) = res {
                    all_results.push(r);
                }
            }
        }
        Ok(all_results)
    }
}
