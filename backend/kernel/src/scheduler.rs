// backend/kernel/src/scheduler.rs
use std::collections::{BinaryHeap, HashMap};
use std::cmp::Ordering;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum MissionPriority {
    Critical = 0,
    High = 1,
    Normal = 2,
    Low = 3,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum MissionState {
    Queued,
    Analyzing,
    Executing,
    Verifying,
    Succeeded,
    Failed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, Eq, PartialEq)]
pub struct MissionTask {
    pub id: String,
    pub priority: MissionPriority,
    pub state: MissionState,
    pub created_at: u64,
}

impl Ord for MissionTask {
    fn cmp(&self, other: &Self) -> Ordering {
        // Higher priority (lower numeric value) comes first
        other.priority.clone() as u32 as i32
            .cmp(&(self.priority.clone() as u32 as i32))
            .then_with(|| other.created_at.cmp(&self.created_at))
    }
}

impl PartialOrd for MissionTask {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

pub struct MissionScheduler {
    queue: Arc<Mutex<BinaryHeap<MissionTask>>>,
    active_missions: Arc<Mutex<HashMap<String, MissionTask>>>,
}

impl MissionScheduler {
    pub fn new() -> Self {
        Self {
            queue: Arc::new(Mutex::new(BinaryHeap::new())),
            active_missions: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn schedule(&self, id: String, priority: MissionPriority) {
        let task = MissionTask {
            id: id.clone(),
            priority,
            state: MissionState::Queued,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        let mut queue = self.queue.lock().unwrap();
        queue.push(task.clone());
        
        let mut active = self.active_missions.lock().unwrap();
        active.insert(id, task);
    }

    pub fn pop_next(&self) -> Option<MissionTask> {
        let mut queue = self.queue.lock().unwrap();
        if let Some(mut task) = queue.pop() {
            task.state = MissionState::Executing;
            let mut active = self.active_missions.lock().unwrap();
            active.insert(task.id.clone(), task.clone());
            return Some(task);
        }
        None
    }

    pub fn update_state(&self, id: String, state: MissionState) {
        let mut active = self.active_missions.lock().unwrap();
        if let Some(task) = active.get_mut(&id) {
            task.state = state;
        }
    }

    pub fn get_status(&self, id: String) -> Option<MissionState> {
        let active = self.active_missions.lock().unwrap();
        active.get(&id).map(|t| t.state.clone())
    }

    pub fn get_all_tasks(&self) -> Vec<MissionTask> {
        let active = self.active_missions.lock().unwrap();
        active.values().cloned().collect()
    }
}
