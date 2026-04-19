// backend/kernel/bare_metal/src/scheduler.rs
use crate::process::{ProcessControlBlock, ProcessState};
use alloc::collections::VecDeque;
use spin::Mutex;
use lazy_static::lazy_static;
use x86_64::registers::control::Cr3;

lazy_static! {
    pub static ref SCHEDULER: Mutex<Scheduler> = Mutex::new(Scheduler::new());
}

pub struct Scheduler {
    processes: VecDeque<ProcessControlBlock>,
    wait_queue: VecDeque<ProcessControlBlock>,
    current_pid: Option<u64>,
}

impl Scheduler {
    pub fn new() -> Self {
        Self {
            processes: VecDeque::new(),
            wait_queue: VecDeque::new(),
            current_pid: None,
        }
    }

    pub fn block_current(&mut self) {
        if let Some(mut current) = self.processes.pop_front() {
             current.state = ProcessState::Blocked;
             self.wait_queue.push_back(current);
        }
    }

    pub fn wakeup(&mut self, pid: u64) {
        if let Some(idx) = self.wait_queue.iter().position(|p| p.pid == pid) {
             let mut p = self.wait_queue.remove(idx).unwrap();
             p.state = ProcessState::Ready;
             self.processes.push_back(p);
        }
    }

    pub fn add_process(&mut self, pcb: ProcessControlBlock) {
        self.processes.push_back(pcb);
    }

    /// Preemptive schedule called by timer interrupt.
    pub fn schedule(&mut self) {
        if self.processes.is_empty() { return; }

        // Round-robin: move current to back, get next
        let mut next_pcb = self.processes.pop_front().unwrap();
        
        // CR3 swap
        unsafe {
            let (current_cr3, flags) = Cr3::read();
            if current_cr3.start_address() != next_pcb.pml4_phys {
                Cr3::write(next_pcb.pml4_phys, flags);
            }
        }

        // Register restore simulation (Hard reality: requires assembly stub)
        next_pcb.state = ProcessState::Running;
        self.current_pid = Some(next_pcb.pid);
        self.processes.push_back(next_pcb);
    }

    pub fn cleanup_zombies(&mut self) -> usize {
        let original_count = self.processes.len();
        self.processes.retain(|p| p.state != ProcessState::Terminated);
        original_count - self.processes.len()
    }
}
