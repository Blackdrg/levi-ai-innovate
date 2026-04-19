// backend/kernel/bare_metal/src/raft.rs
//
// RAFT-LITE CONSENSUS CORE — v22.0.0 Graduation
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use alloc::vec::Vec;
use spin::Mutex;
use lazy_static::lazy_static;

#[derive(Debug, Clone, PartialEq)]
pub enum NodeState {
    Follower,
    Candidate,
    Leader,
}

pub struct RaftCore {
    pub current_term: u64,
    pub voted_for: Option<u32>,
    pub log: Vec<RaftEntry>,
    pub state: NodeState,
    pub commit_index: u64,
}

#[derive(Debug, Clone)]
pub struct RaftEntry {
    pub term: u64,
    pub command: Vec<u8>,
}

impl RaftCore {
    pub fn new() -> Self {
        Self {
            current_term: 0,
            voted_for: None,
            log: Vec::new(),
            state: NodeState::Follower,
            commit_index: 0,
        }
    }

    pub fn handle_vote_request(&mut self, term: u64, candidate_id: u32) -> bool {
        if term > self.current_term {
            self.current_term = term;
            self.voted_for = Some(candidate_id);
            self.state = NodeState::Follower;
            println!(" [RAFT] Voted for candidate {} in term {}", candidate_id, term);
            return true;
        }
        false
    }

    pub fn append_entry(&mut self, term: u64, command: Vec<u8>) {
        if self.state == NodeState::Leader {
            self.log.push(RaftEntry { term, command });
            println!(" [RAFT] Log entry appended. Replication pending...");
        }
    }

    pub fn step(&mut self) {
        // Election timeout logic simulation
        if self.state == NodeState::Follower && crate::stability::get_ticks() % 5000 == 0 {
             println!(" [RAFT] Election timeout. Transitioning to CANDIDATE.");
             self.state = NodeState::Candidate;
             self.current_term += 1;
        }
    }
}

lazy_static! {
    pub static ref RAFT_CORE: Mutex<RaftCore> = Mutex::new(RaftCore::new());
}
