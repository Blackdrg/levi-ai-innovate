// backend/kernel/bare_metal/src/fs_api.rs
//
// FILE DESCRIPTOR SYSTEM — v22.0.0 Graduation
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::vfs;
use alloc::vec::Vec;
use spin::Mutex;
use lazy_static::lazy_static;

const MAX_FDS: usize = 32;

pub struct FileDescriptor {
    pub inode: u32,
    pub offset: u32,
    pub used: bool,
}

pub struct FdTable {
    pub fds: [FileDescriptor; MAX_FDS],
}

impl FdTable {
    pub fn new() -> Self {
        const EMPTY_FD: FileDescriptor = FileDescriptor { inode: 0, offset: 0, used: false };
        Self { fds: [EMPTY_FD; MAX_FDS] }
    }

    pub fn open(&mut self, path: &str) -> Option<usize> {
        let ino = vfs::lookup(path)?;
        for (i, fd) in self.fds.iter_mut().enumerate() {
            if !fd.used {
                fd.inode = ino;
                fd.offset = 0;
                fd.used = true;
                return Some(i);
            }
        }
        None
    }

    pub fn read(&mut self, fd_idx: usize, len: usize) -> Option<Vec<u8>> {
        if fd_idx >= MAX_FDS || !self.fds[fd_idx].used { return None; }
        
        let fd = &mut self.fds[fd_idx];
        let data = vfs::read_inode_data(fd.inode);
        let start = core::cmp::min(fd.offset as usize, data.len());
        let end = core::cmp::min(start + len, data.len());
        
        let slice = data[start..end].to_vec();
        fd.offset += slice.len() as u32;
        Some(slice)
    }

    pub fn close(&mut self, fd_idx: usize) {
        if fd_idx < MAX_FDS {
             self.fds[fd_idx].used = false;
        }
    }
}

lazy_static! {
    pub static ref GLOBAL_FD_TABLE: Mutex<FdTable> = Mutex::new(FdTable::new());
}
