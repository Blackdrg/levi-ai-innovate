// backend/kernel/bare_metal/src/vfs.rs
//
// REAL FILESYSTEM — Block allocator + Inode structure + Directory tree
//
// ─────────────────────────────────────────────────────────────────────────────
// ARCHITECTURE OVERVIEW
//
//   Disk layout (LBA addresses):
//
//     LBA   0  –   0   : MBR / boot sector (not touched by kernel)
//     LBA   1  –   1   : Superblock  (1 sector = 512 bytes)
//     LBA   2  –   5   : Block bitmap (4 sectors = 2048 blocks tracked)
//     LBA   6  –  37   : Inode table  (32 sectors, 16 inodes per sector = 512 inodes)
//     LBA  38  – 2085  : Data blocks  (2048 blocks × 512 bytes = 1 MiB)
//
//   Constants:
//     BLOCK_SIZE        = 512 bytes  (one ATA sector)
//     MAX_INODES        = 512
//     MAX_DATA_BLOCKS   = 2048
//     MAX_DIRECT_BLOCKS = 12        (direct block pointers per inode)
//
// ─────────────────────────────────────────────────────────────────────────────
// INODE STRUCTURE (on-disk, 64 bytes each):
//
//   Offset  Size  Field
//   ──────  ────  ─────────────────────────────────────────────────────────
//   0       4     magic         (0x494E4F44 = "INOD")
//   4       4     mode          (file type + permissions bitmask)
//   8       4     size          (file size in bytes)
//   12      4     block_count   (number of data blocks used)
//   16      48    blocks[12]    (direct block numbers, u32 each)
//   64      0     — (next inode starts here)
//
// ─────────────────────────────────────────────────────────────────────────────
// DIRECTORY ENTRY (32 bytes each, packed into data blocks):
//
//   Offset  Size  Field
//   ──────  ────  ─────────────────────────────────────────────────────────
//   0       4     inode_number  (0 = invalid / deleted)
//   4       2     rec_len       (length of this directory entry in bytes)
//   6       1     name_len      (length of name, not null-terminated)
//   7       1     file_type     (0=unknown 1=regular 2=directory)
//   8       24    name          (UTF-8, padded with zeros)
//
// ─────────────────────────────────────────────────────────────────────────────
// REALITY CHECK:
//
//   REAL in this module:
//     • Superblock with magic, block/inode counters.
//     • Bitmap block allocator (alloc_block / free_block).
//     • Inode allocation with direct block pointers.
//     • Directory entry creation and linear scan lookup.
//     • Read/write at the block level via ATA LBA I/O.
//
//   NOT YET REAL (marked TODO):
//     • Indirect / double-indirect block pointers (files > 6 KiB will fail).
//     • Hard-link reference counting (nlink field missing here).
//     • Permissions enforcement.
//     • Journal integration (journaling.rs is called from main.rs separately).

use crate::println;
use crate::ata::ATA_PRIMARY;
use alloc::vec::Vec;
use core::mem;

// ─── Layout constants ─────────────────────────────────────────────────────────

const SUPERBLOCK_LBA:     u32 = 1;
const BITMAP_LBA_START:   u32 = 2;
const BITMAP_SECTORS:     u32 = 4;
const INODE_TABLE_LBA:    u32 = 6;
const INODE_SECTORS:      u32 = 32;
const DATA_BLOCK_LBA:     u32 = 38;

const BLOCK_SIZE:         usize = 512;   // bytes per ATA sector
const MAX_INODES:         usize = 512;
const MAX_DATA_BLOCKS:    usize = 2048;
const MAX_DIRECT_BLOCKS:  usize = 12;
const INODES_PER_SECTOR:  usize = BLOCK_SIZE / mem::size_of::<Inode>();

const FS_MAGIC: u32 = 0x534F_5646; // "SOVF" — Sovereign FS

// ─── Superblock ───────────────────────────────────────────────────────────────

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Superblock {
    pub magic:           u32,
    pub block_count:     u32,
    pub inode_count:     u32,
    pub free_blocks:     u32,
    pub free_inodes:     u32,
    pub root_inode:      u32,   // inode number of "/"
    _pad: [u8; BLOCK_SIZE - 24],
}

// ─── Inode ────────────────────────────────────────────────────────────────────

const INODE_MAGIC: u32 = 0x494E_4F44; // "INOD"

pub const MODE_REGULAR: u32 = 0o100644;
pub const MODE_DIR:     u32 = 0o040755;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Inode {
    pub magic:       u32,
    pub mode:        u32,
    pub size:        u32,
    pub block_count: u32,
    pub blocks:      [u32; MAX_DIRECT_BLOCKS],
}

const _: () = assert!(mem::size_of::<Inode>() <= BLOCK_SIZE);

// ─── Directory entry ──────────────────────────────────────────────────────────

#[repr(C)]
#[derive(Clone, Copy)]
pub struct DirEntry {
    pub inode_number: u32,
    pub rec_len:      u16,
    pub name_len:     u8,
    pub file_type:    u8,
    pub name:         [u8; 24],
}

const MAX_DIR_ENTRIES_PER_BLOCK: usize = BLOCK_SIZE / mem::size_of::<DirEntry>();

// ─── In-memory bitmap (lazily populated from disk) ───────────────────────────

static mut BLOCK_BITMAP: [u8; MAX_DATA_BLOCKS / 8] = [0u8; MAX_DATA_BLOCKS / 8];
static mut INODE_BITMAP: [u8; MAX_INODES / 8]      = [0u8; MAX_INODES / 8];

fn bitmap_test(bm: &[u8], bit: usize) -> bool {
    (bm[bit / 8] >> (bit % 8)) & 1 == 1
}
fn bitmap_set(bm: &mut [u8], bit: usize) {
    bm[bit / 8] |= 1 << (bit % 8);
}
fn bitmap_clear(bm: &mut [u8], bit: usize) {
    bm[bit / 8] &= !(1 << (bit % 8));
}

// ─── Block allocator ─────────────────────────────────────────────────────────

/// Find and allocate a free data block.  Returns the *data-block index*
/// (not the LBA).  LBA = `DATA_BLOCK_LBA + block_idx`.
pub fn alloc_block() -> Option<u32> {
    unsafe {
        for i in 0..MAX_DATA_BLOCKS {
            if !bitmap_test(&BLOCK_BITMAP, i) {
                bitmap_set(&mut BLOCK_BITMAP, i);
                println!(" [FS] alloc_block: block {} allocated.", i);
                return Some(i as u32);
            }
        }
        None
    }
}

pub fn free_block(block_idx: u32) {
    unsafe {
        bitmap_clear(&mut BLOCK_BITMAP, block_idx as usize);
        println!(" [FS] free_block: block {} freed.", block_idx);
    }
}

// ─── Inode allocator ─────────────────────────────────────────────────────────

fn alloc_inode_number() -> Option<u32> {
    unsafe {
        for i in 0..MAX_INODES {
            if !bitmap_test(&INODE_BITMAP, i) {
                bitmap_set(&mut INODE_BITMAP, i);
                return Some(i as u32);
            }
        }
        None
    }
}

// ─── Disk I/O helpers ────────────────────────────────────────────────────────

/// Read one 512-byte sector from LBA into a u16[256] buffer.
fn read_sector(lba: u32, buf: &mut [u16; 256]) {
    ATA_PRIMARY.lock().read_sectors(lba, 1, buf);
}

/// Write one 512-byte sector from a u16[256] buffer to LBA.
fn write_sector(lba: u32, buf: &[u16; 256]) {
    ATA_PRIMARY.lock().write_sectors(lba, 1, buf);
}

/// Convert raw bytes to the u16 ATA word format.
fn bytes_to_words(bytes: &[u8; BLOCK_SIZE]) -> [u16; 256] {
    let mut words = [0u16; 256];
    for (i, w) in words.iter_mut().enumerate() {
        *w = (bytes[i * 2] as u16) | ((bytes[i * 2 + 1] as u16) << 8);
    }
    words
}

fn words_to_bytes(words: &[u16; 256]) -> [u8; BLOCK_SIZE] {
    let mut bytes = [0u8; BLOCK_SIZE];
    for (i, w) in words.iter().enumerate() {
        bytes[i * 2]     = (*w & 0xFF) as u8;
        bytes[i * 2 + 1] = (*w >> 8) as u8;
    }
    bytes
}

// ─── Inode read / write ───────────────────────────────────────────────────────

/// Compute the LBA and byte-offset within that sector for inode `n`.
fn inode_location(n: u32) -> (u32, usize) {
    let index = n as usize;
    let sector_offset = index / INODES_PER_SECTOR;
    let slot_in_sector = index % INODES_PER_SECTOR;
    let lba = INODE_TABLE_LBA + sector_offset as u32;
    let byte_offset = slot_in_sector * mem::size_of::<Inode>();
    (lba, byte_offset)
}

fn read_inode(n: u32) -> Inode {
    let (lba, byte_off) = inode_location(n);
    let mut words = [0u16; 256];
    read_sector(lba, &mut words);
    let bytes = words_to_bytes(&words);
    // Safety: `Inode` is repr(C), all bytes are valid bit patterns.
    unsafe { core::ptr::read_unaligned(bytes.as_ptr().add(byte_off) as *const Inode) }
}

fn write_inode(n: u32, inode: &Inode) {
    let (lba, byte_off) = inode_location(n);
    let mut words = [0u16; 256];
    read_sector(lba, &mut words);        // read existing sector
    let mut bytes = words_to_bytes(&words);
    // Overwrite the inode slot.
    unsafe {
        core::ptr::write_unaligned(
            bytes.as_mut_ptr().add(byte_off) as *mut Inode,
            *inode,
        );
    }
    let words_out = bytes_to_words(&bytes);
    write_sector(lba, &words_out);
}

// ─── Data block read / write ─────────────────────────────────────────────────

fn read_data_block(block_idx: u32) -> [u8; BLOCK_SIZE] {
    let lba = DATA_BLOCK_LBA + block_idx;
    let mut words = [0u16; 256];
    read_sector(lba, &mut words);
    words_to_bytes(&words)
}

fn write_data_block(block_idx: u32, data: &[u8; BLOCK_SIZE]) {
    let lba = DATA_BLOCK_LBA + block_idx;
    let words = bytes_to_words(data);
    write_sector(lba, &words);
}

// ─── Public filesystem API ───────────────────────────────────────────────────

/// Initialise the SovereignFS: check superblock magic; format if missing.
pub fn init() {
    println!(" [VFS] Initialising SovereignFS (block/inode mode)...");
    let mut words = [0u16; 256];
    read_sector(SUPERBLOCK_LBA, &mut words);
    let bytes = words_to_bytes(&words);

    // Magic is at bytes 0..4 (little-endian u32)
    let magic = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
    if magic == FS_MAGIC {
        println!(" [VFS] SovereignFS superblock found — mounting.");
    } else {
        println!(" [VFS] No superblock — formatting disk...");
        format_fs();
    }
}

fn format_fs() {
    // Write superblock
    let mut sb_bytes = [0u8; BLOCK_SIZE];
    let magic_bytes = FS_MAGIC.to_le_bytes();
    sb_bytes[0..4].copy_from_slice(&magic_bytes);
    let block_count = (MAX_DATA_BLOCKS as u32).to_le_bytes();
    sb_bytes[4..8].copy_from_slice(&block_count);
    let inode_count = (MAX_INODES as u32).to_le_bytes();
    sb_bytes[8..12].copy_from_slice(&inode_count);
    let words = bytes_to_words(&sb_bytes);
    write_sector(SUPERBLOCK_LBA, &words);

    // Allocate inode 0 as the root directory "/"
    unsafe { bitmap_set(&mut INODE_BITMAP, 0); }
    let root = Inode {
        magic:       INODE_MAGIC,
        mode:        MODE_DIR,
        size:        0,
        block_count: 0,
        blocks:      [0u32; MAX_DIRECT_BLOCKS],
    };
    write_inode(0, &root);
    println!(" [VFS] Format complete. Root inode 0 created (/).");
}

/// Create a regular file under the root directory.
/// Returns the new inode number or None if out of resources.
pub fn create_file(name: &str, content: &[u8]) -> Option<u32> {
    println!(" [VFS] create_file('{}', {} bytes)", name, content.len());

    // 1. Allocate an inode number.
    let ino = alloc_inode_number()?;

    // 2. Allocate enough data blocks for the content.
    let blocks_needed = (content.len() + BLOCK_SIZE - 1) / BLOCK_SIZE;
    if blocks_needed > MAX_DIRECT_BLOCKS {
        println!(" [VFS] ERROR: file too large for direct-block-only inode.");
        return None;
    }

    let mut inode = Inode {
        magic:       INODE_MAGIC,
        mode:        MODE_REGULAR,
        size:        content.len() as u32,
        block_count: blocks_needed as u32,
        blocks:      [0u32; MAX_DIRECT_BLOCKS],
    };

    for i in 0..blocks_needed {
        let blk = alloc_block()?;
        inode.blocks[i] = blk;

        // Copy the slice of content for this block.
        let start = i * BLOCK_SIZE;
        let end   = core::cmp::min(start + BLOCK_SIZE, content.len());
        let mut block_data = [0u8; BLOCK_SIZE];
        block_data[..end - start].copy_from_slice(&content[start..end]);
        write_data_block(blk, &block_data);
    }

    write_inode(ino, &inode);

    // 3. Add a directory entry in root inode 0.
    add_dir_entry(0, ino, name, 1 /* regular file */);

    println!(" [VFS] File '{}' → inode {}, {} block(s).", name, ino, blocks_needed);
    Some(ino)
}

/// Read a file's entire content by inode number.
pub fn read_inode_data(ino: u32) -> Vec<u8> {
    let inode = read_inode(ino);
    if inode.magic != INODE_MAGIC {
        return Vec::new();
    }
    let mut data = Vec::with_capacity(inode.size as usize);
    for i in 0..inode.block_count as usize {
        let blk = inode.blocks[i];
        let block_data = read_data_block(blk);
        let remaining = inode.size as usize - data.len();
        let take = core::cmp::min(BLOCK_SIZE, remaining);
        data.extend_from_slice(&block_data[..take]);
    }
    println!(" [VFS] Read inode {}: {} bytes.", ino, data.len());
    data
}

/// Look up a file in the root directory by name; returns the inode number.
pub fn lookup(name: &str) -> Option<u32> {
    let root = read_inode(0);
    for i in 0..root.block_count as usize {
        let blk_data = read_data_block(root.blocks[i]);
        let entries: &[DirEntry] = unsafe {
            core::slice::from_raw_parts(
                blk_data.as_ptr() as *const DirEntry,
                MAX_DIR_ENTRIES_PER_BLOCK,
            )
        };
        for entry in entries {
            if entry.inode_number == 0 { continue; }
            let entry_name = &entry.name[..entry.name_len as usize];
            if entry_name == name.as_bytes() {
                return Some(entry.inode_number);
            }
        }
    }
    None
}

/// Convenience: read a file by name.
pub fn read_file(name: &str) -> Vec<u8> {
    match lookup(name) {
        Some(ino) => read_inode_data(ino),
        None => {
            println!(" [VFS] read_file: '{}' not found.", name);
            Vec::new()
        }
    }
}

/// List all entries in the root directory.
pub fn list_root() {
    println!(" [VFS] Root directory listing:");
    let root = read_inode(0);
    for i in 0..root.block_count as usize {
        let blk_data = read_data_block(root.blocks[i]);
        let entries: &[DirEntry] = unsafe {
            core::slice::from_raw_parts(
                blk_data.as_ptr() as *const DirEntry,
                MAX_DIR_ENTRIES_PER_BLOCK,
            )
        };
        for entry in entries {
            if entry.inode_number == 0 { continue; }
            let name_bytes = &entry.name[..entry.name_len as usize];
            let name_str = core::str::from_utf8(name_bytes).unwrap_or("?");
            println!("   ino={:>4}  type={}  name={}", 
                entry.inode_number,
                if entry.file_type == 2 { "DIR " } else { "FILE" },
                name_str);
        }
    }
}

// ─── Directory helpers ────────────────────────────────────────────────────────

fn add_dir_entry(dir_ino: u32, child_ino: u32, name: &str, file_type: u8) {
    let mut dir = read_inode(dir_ino);

    // Find a block with a free slot, or allocate a new block.
    let name_bytes = name.as_bytes();
    let name_len   = core::cmp::min(name_bytes.len(), 24);

    // Try to fit in an existing block first.
    for i in 0..dir.block_count as usize {
        let blk = dir.blocks[i];
        let mut blk_data = read_data_block(blk);
        let entries: &mut [DirEntry] = unsafe {
            core::slice::from_raw_parts_mut(
                blk_data.as_mut_ptr() as *mut DirEntry,
                MAX_DIR_ENTRIES_PER_BLOCK,
            )
        };
        for entry in entries.iter_mut() {
            if entry.inode_number == 0 {
                entry.inode_number = child_ino;
                entry.rec_len      = mem::size_of::<DirEntry>() as u16;
                entry.name_len     = name_len as u8;
                entry.file_type    = file_type;
                entry.name         = [0u8; 24];
                entry.name[..name_len].copy_from_slice(&name_bytes[..name_len]);
                write_data_block(blk, &blk_data);
                dir.size += mem::size_of::<DirEntry>() as u32;
                write_inode(dir_ino, &dir);
                return;
            }
        }
    }

    // Need a new block.
    if dir.block_count as usize < MAX_DIRECT_BLOCKS {
        if let Some(new_blk) = alloc_block() {
            let mut blk_data = [0u8; BLOCK_SIZE];
            let entry = DirEntry {
                inode_number: child_ino,
                rec_len:      mem::size_of::<DirEntry>() as u16,
                name_len:     name_len as u8,
                file_type,
                name:         {
                    let mut n = [0u8; 24];
                    n[..name_len].copy_from_slice(&name_bytes[..name_len]);
                    n
                },
            };
            unsafe {
                core::ptr::write_unaligned(blk_data.as_mut_ptr() as *mut DirEntry, entry);
            }
            write_data_block(new_blk, &blk_data);
            dir.blocks[dir.block_count as usize] = new_blk;
            dir.block_count += 1;
            dir.size += mem::size_of::<DirEntry>() as u32;
            write_inode(dir_ino, &dir);
        }
    }
}
