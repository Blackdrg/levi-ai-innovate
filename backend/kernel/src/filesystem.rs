// backend/kernel/src/filesystem.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FileType {
    Directory,
    File,
    BlockDevice,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Inode {
    pub id: u64,
    pub ftype: FileType,
    pub size: u64,
    pub blocks: Vec<u64>, // Real CPU Block Pointers
    pub uid: u32,
    pub gid: u32,
    pub permissions: u16, // 0o755 style
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNode {
    pub name: String,
    pub inode_id: u64,
    pub ftype: FileType,
    pub size: u64,
    pub children: Option<HashMap<String, VNode>>,
}

pub struct SovereignFS {
    pub inodes: Arc<Mutex<HashMap<u64, Inode>>>,
    pub block_bitmap: Arc<Mutex<Vec<bool>>>, // 1 = Allocated
    root: Arc<Mutex<VNode>>,
    next_inode: Arc<Mutex<u64>>,
}

impl SovereignFS {
    pub fn new() -> Self {
        let mut block_bitmap = vec![false; 1048576]; // 1M * 4KB = 4GB virtual disk
        
        let root_inode = Inode {
            id: 1,
            ftype: FileType::Directory,
            size: 0,
            blocks: Vec::new(),
            uid: 0,
            gid: 0,
            permissions: 0o755,
        };

        let mut inodes = HashMap::new();
        inodes.insert(1, root_inode);

        Self {
            inodes: Arc::new(Mutex::new(inodes)),
            block_bitmap: Arc::new(Mutex::new(block_bitmap)),
            root: Arc::new(Mutex::new(VNode {
                name: "/".to_string(),
                inode_id: 1,
                ftype: FileType::Directory,
                size: 0,
                children: Some(HashMap::new()),
            })),
            next_inode: Arc::new(Mutex::new(2)),
        }
    }

    pub fn allocate_blocks(&self, size: u64) -> Result<Vec<u64>, String> {
        let mut bitmap = self.block_bitmap.lock().unwrap();
        let blocks_needed = (size + 4095) / 4096;
        let mut allocated = Vec::new();
        
        for i in 0..bitmap.len() {
            if !bitmap[i] {
                bitmap[i] = true;
                allocated.push(i as u64);
                if allocated.len() as u64 == blocks_needed {
                    return Ok(allocated);
                }
            }
        }
        Err("DISK FULL: Block allocation failed".to_string())
    }

    pub fn create_file(&self, name: String, size: u64, uid: u32) -> Result<u64, String> {
        let blocks = self.allocate_blocks(size)?;
        let mut ni = self.next_inode.lock().unwrap();
        let id = *ni;
        *ni += 1;

        let inode = Inode {
            id,
            ftype: FileType::File,
            size,
            blocks,
            uid,
            gid: uid,
            permissions: 0o644,
        };

        self.inodes.lock().unwrap().insert(id, inode);
        
        let mut root = self.root.lock().unwrap();
        if let Some(children) = &mut root.children {
            children.insert(name.clone(), VNode {
                name,
                inode_id: id,
                ftype: FileType::File,
                size,
                children: None,
            });
        }

        log::info!("💾 [FS] File created with Inode: {} ({} blocks allocated)", id, (size+4095)/4096);
        Ok(id)
    }

    pub fn get_tree(&self) -> VNode {
        self.root.lock().unwrap().clone()
    }
}

