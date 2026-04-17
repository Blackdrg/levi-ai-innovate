// backend/kernel/src/filesystem.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FileType {
    Directory,
    File,
    Symlink,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNode {
    pub name: String,
    pub ftype: FileType,
    pub size: u64,
    pub children: Option<HashMap<String, VNode>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FSSnapshot {
    pub id: String,
    pub timestamp: u64,
    pub root_state: VNode,
    pub prev_hash: String,
    pub signature: String,
}

pub struct SovereignFS {
    root: Arc<Mutex<VNode>>,
    snapshots: Arc<Mutex<Vec<FSSnapshot>>>,
    journal: Arc<Mutex<Vec<String>>>,
}

impl SovereignFS {
    pub fn new() -> Self {
        let mut root_children = HashMap::new();
        
        root_children.insert("sys".to_string(), VNode { name: "sys".to_string(), ftype: FileType::Directory, size: 0, children: Some(HashMap::new()) });
        root_children.insert("proc".to_string(), VNode { name: "proc".to_string(), ftype: FileType::Directory, size: 0, children: Some(HashMap::new()) });
        root_children.insert("mnt".to_string(), VNode { name: "mnt".to_string(), ftype: FileType::Directory, size: 0, children: Some(HashMap::new()) });
        root_children.insert("home".to_string(), VNode { name: "home".to_string(), ftype: FileType::Directory, size: 0, children: Some(HashMap::new()) });

        Self {
            root: Arc::new(Mutex::new(VNode {
                name: "/".to_string(),
                ftype: FileType::Directory,
                size: 0,
                children: Some(root_children),
            })),
            snapshots: Arc::new(Mutex::new(Vec::new())),
            journal: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn take_snapshot(&self, signature: String) -> String {
        let root = self.root.lock().unwrap().clone();
        let mut snaps = self.snapshots.lock().unwrap();
        
        let prev_hash = snaps.last().map(|s| s.signature.clone()).unwrap_or_else(|| "GENESIS".to_string());
        let id = format!("snap_{}", snaps.len());
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();

        let snapshot = FSSnapshot {
            id: id.clone(),
            timestamp,
            root_state: root,
            prev_hash,
            signature,
        };

        snaps.push(snapshot);
        log::info!("💾 [SovereignFS] Snapshot {} PERSISTED and CHAINED.", id);
        id
    }

    pub fn restore_snapshot(&self, id: String) -> Result<(), String> {
        let snaps = self.snapshots.lock().unwrap();
        if let Some(snap) = snaps.iter().find(|s| s.id == id) {
            let mut root = self.root.lock().unwrap();
            *root = snap.root_state.clone();
            log::warn!("⏪ [SovereignFS] System state RESTORED from snapshot {}.", id);
            return Ok(());
        }
        Err("Snapshot not found".to_string())
    }

    pub fn get_tree(&self) -> VNode {
        self.root.lock().unwrap().clone()
    }

    pub fn log_transaction(&self, op: String) {
        let mut j = self.journal.lock().unwrap();
        j.push(op);
        if j.len() > 1000 { j.remove(0); } // Rotate journal
    }

    pub fn mount(&self, path: String, target: VNode) -> Result<(), String> {
        let mut root = self.root.lock().unwrap();
        if let Some(children) = &mut root.children {
            children.insert(path, target);
            self.log_transaction(format!("MOUNT {}", path));
            return Ok(());
        }
        Err("Root is not a directory".to_string())
    }
}
