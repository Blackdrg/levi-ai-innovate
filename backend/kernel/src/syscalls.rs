// backend/kernel/src/syscalls.rs
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
pub enum SysCallType {
    Read = 0,
    Write = 1,
    Open = 2,
    Close = 3,
    Fork = 57,
    Exec = 59,
    Exit = 60,
    Kill = 62, // Send signal
    Mmap = 9,
    Munmap = 11,
    NetSend = 0x04,
    McmGraduate = 0x06,
    McmRead = 0x0C,
}

pub struct SysCallDispatcher;

impl SysCallDispatcher {
    pub fn dispatch(call_type: SysCallType, args: Vec<u64>) -> Result<u64, String> {
        // 🛡️ [Security] SysCall Filtering (seccomp-lite)
        if Self::is_blacklisted(&call_type) {
            log::error!("🔥 [Security] SANDBOX ESCAPE BLOCKED: Blacklisted SysCall {:?} rejected.", call_type);
            return Err("EPERM: SysCall forbidden by security policy".to_string());
        }

        match call_type {
            SysCallType::Write => {
                // Implementation for sys_write
                Ok(0)
            },
            SysCallType::Kill => {
                // Implementation for sys_kill
                Ok(0)
            },
            SysCallType::NetSend => {
                // Implementation for raw packet emission
                Ok(1)
            },
            SysCallType::McmGraduate => {
                // Implementation for tier-3 persistence
                Ok(1)
            },
            SysCallType::McmRead => {
                // Implementation for fact retrieval from Tier 3
                Ok(1)
            },
            _ => Err("Syscall not yet implemented in this Ring".to_string()),
        }
    }

    fn is_blacklisted(call_type: &SysCallType) -> bool {
        match call_type {
            SysCallType::Fork | SysCallType::Exec => {
                // Deny process spawning directly through syscalls; must use WAVE_SPAWN
                true
            },
            _ => false,
        }
    }
}
