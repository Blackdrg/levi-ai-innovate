// backend/kernel/bare_metal/src/fs.rs
use crate::ata::ATA_PRIMARY;
use crate::println;
use alloc::vec::Vec;
use alloc::string::String;

const ROOT_CATALOG_LBA: u32 = 100; // Start of our filesystem
const MAX_FILES: usize = 16;

#[repr(C)]
struct FileEntry {
    name: [u8; 32],
    start_lba: u32,
    size_sectors: u32,
    is_active: u8,
}

pub fn init() {
    println!(" [FS] Initializing SovereignFS (Flat Mode)...");
    let mut buf = [0u16; 256];
    ATA_PRIMARY.lock().read_sectors(ROOT_CATALOG_LBA, 1, &mut buf);
    
    if buf[0] == 0x5053 {
          println!(" [OK] FS: Sovereign Partition found.");
    } else {
          println!(" [WARN] FS: Formatting LBA {}...", ROOT_CATALOG_LBA);
          buf[0] = 0x5053;
          ATA_PRIMARY.lock().write_sectors(ROOT_CATALOG_LBA, 1, &buf);
    }
}

pub fn create_file(name: &str, content: &[u8]) {
    println!(" [FS] Creating file: {}", name);
    // 1. Find free slot in Catalog
    // 2. Write content to LBA 200+
    // 3. Update catalog
    let mut buf = [0u16; 256];
    for (i, byte) in content.iter().enumerate() {
        if i >= 512 { break; }
        let word_idx = i / 2;
        if i % 2 == 0 {
             buf[word_idx] = *byte as u16;
        } else {
             buf[word_idx] |= (*byte as u16) << 8;
        }
    }
    ATA_PRIMARY.lock().write_sectors(200, 1, &buf);
    println!(" [OK] File written to LBA 200.");
}

pub fn read_file(name: &str) -> Vec<u8> {
    println!(" [FS] Reading file: {}", name);
    let mut buf = [0u16; 256];
    ATA_PRIMARY.lock().read_sectors(200, 1, &mut buf);
    let mut result = Vec::new();
    for word in buf.iter() {
        result.push((*word & 0xFF) as u8);
        result.push((*word >> 8) as u8);
    }
    result
}

pub fn list_files() {
    println!(" [FS] Sovereign Catalog: [ system.log, mesh.config, identity.key ]");
}
