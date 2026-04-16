// backend/kernel/src/filesystem.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

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

pub struct SovereignFS {
    root: Arc<Mutex<VNode>>,
}

impl SovereignFS {
    pub fn new() -> Self {
        let mut root_children = HashMap::new();
        
        // Setup initial system directories
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
        }
    }

    pub fn get_tree(&self) -> VNode {
        self.root.lock().unwrap().clone()
    }

    pub fn mount(&self, path: String, target: VNode) -> Result<(), String> {
        // Simple mount logic
        let mut root = self.root.lock().unwrap();
        if let Some(children) = &mut root.children {
            children.insert(path, target);
            return Ok(());
        }
        Err("Root is not a directory".to_string())
    }
}
