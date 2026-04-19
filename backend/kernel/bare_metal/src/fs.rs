// backend/kernel/bare_metal/src/fs.rs
// Wrapper for VFS (Virtual File System) to maintain graduation ABI compatibility.
use crate::vfs;
use alloc::vec::Vec;

pub fn init() {
    vfs::init();
}

pub fn create_file(name: &str, content: &[u8]) {
    vfs::create_file(name, content);
}

pub fn read_file(name: &str) -> Vec<u8> {
    vfs::read_file(name)
}

pub fn list_files() {
    vfs::list_root();
}
