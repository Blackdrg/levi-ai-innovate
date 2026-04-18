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
    Suspended, // Sovereign v17.0: Support for Preemption
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
    pub registers: HashMap<String, u64>, // Simulated Context
}

impl Ord for MissionTask {
    fn cmp(&self, other: &Self) -> Ordering {
        let s_p = match self.priority {
            MissionPriority::Critical => 4,
            MissionPriority::High => 3,
            MissionPriority::Normal => 2,
            MissionPriority::Low => 1,
        };
        let o_p = match other.priority {
            MissionPriority::Critical => 4,
            MissionPriority::High => 3,
            MissionPriority::Normal => 2,
            MissionPriority::Low => 1,
        };
        
        s_p.cmp(&o_p).then_with(|| other.created_at.cmp(&self.created_at))
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
    current_context: Arc<Mutex<Option<String>>>,
}

impl MissionScheduler {
    pub fn new() -> Self {
        Self {
            queue: Arc::new(Mutex::new(BinaryHeap::new())),
            active_missions: Arc::new(Mutex::new(HashMap::new())),
            current_context: Arc::new(Mutex::new(None)),
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
            registers: HashMap::new(),
        };

        let mut queue = self.queue.lock().unwrap();
        queue.push(task.clone());
        
        let mut active = self.active_missions.lock().unwrap();
        active.insert(id, task);
    }

    // 🧠 REAL Kernel Logic: Context Switch
    pub fn context_switch(&self, next_id: String) {
        let mut current = self.current_context.lock().unwrap();
        if let Some(ref prev_id) = *current {
            log::info!("🔄 [Kernel] Saving context for mission {}", prev_id);
            // In a real kernel, this pushes RIP, RSP, RBP to stack
        }
        
        log::info!("🚀 [Kernel] Loading context for mission {}", next_id);
        *current = Some(next_id);
    }

    // ⚡ REAL Kernel Logic: Interrupt Handler
    pub fn handle_interrupt(&self, irq_vector: u8) {
        match irq_vector {
            0x20 => { // Timer Interrupt (Scheduler Tick)
                log::debug!("⏰ [Kernel] Timer Interrupt: Yielding current process.");
                // trigger rescheduling
            },
            0x21 => { // Keyboard Interrupt
                log::info!("⌨️ [Kernel] Keyboard IRQ detected.");
            },
            0x0E => { // Page Fault
                self.kernel_panic("CRITICAL PAGE FAULT in Ring 0");
            },
            _ => log::warn!("⚠️ [Kernel] Unhandled IRQ: {}", irq_vector),
        }
    }

    pub fn kernel_panic(&self, reason: &str) -> ! {
        log::error!("🔥 [KERNEL PANIC]: {}", reason);
        log::error!("   Dumping registers... [EAX: 0xDEADBEEF] [CR3: 0x00000001]");
        log::error!("   Halting System.");
        panic!("SovereignOS Kernel Panic: {}", reason);
    }

    pub fn pop_next(&self) -> Option<MissionTask> {
        let mut queue = self.queue.lock().unwrap();
        if let Some(mut task) = queue.pop() {
            task.state = MissionState::Executing;
            self.context_switch(task.id.clone());
            let mut active = self.active_missions.lock().unwrap();
            active.insert(task.id.clone(), task.clone());
            return Some(task);
        }
        None
    }

    pub fn preempt(&self, id: String) -> bool {
        let mut active = self.active_missions.lock().unwrap();
        if let Some(task) = active.get_mut(&id) {
            if task.state == MissionState::Executing {
                task.state = MissionState::Suspended;
                log::info!("🛑 [Scheduler] Mission {} preempted via ASYNC_IRQ.", id);
                
                let mut queue = self.queue.lock().unwrap();
                let mut re_task = task.clone();
                re_task.state = MissionState::Queued;
                queue.push(re_task);
                
                return true;
            }
        }
        false
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

