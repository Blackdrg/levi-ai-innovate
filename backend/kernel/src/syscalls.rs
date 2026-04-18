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
}

pub struct SysCallDispatcher;

impl SysCallDispatcher {
    pub fn dispatch(call_type: SysCallType, args: Vec<u64>) -> Result<u64, String> {
        match call_type {
            SysCallType::Write => {
                // Implementation for sys_write
                Ok(0)
            },
            SysCallType::Kill => {
                // Implementation for sys_kill
                Ok(0)
            },
            _ => Err("Syscall not yet implemented in this Ring".to_string()),
        }
    }
}
