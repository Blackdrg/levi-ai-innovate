// backend/levi_runtime/src/plugins/mod.rs
use std::collections::HashMap;
use anyhow::Result;
use async_trait::async_trait;
use dashmap::DashMap;

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    async fn call(&self, input: &str) -> Result<String>;
}

pub struct PluginRegistry {
    tools: DashMap<String, Box<dyn Tool>>,
    marketplace_path: String,
}

impl PluginRegistry {
    pub fn new(marketplace_path: &str) -> Self {
        let registry = Self {
            tools: DashMap::new(),
            marketplace_path: marketplace_path.to_string(),
        };
        
        // Ensure marketplace exists
        let _ = std::fs::create_dir_all(marketplace_path);
        
        // Register built-in tools
        registry.register(Box::new(SystemInfoTool{}));
        registry.register(Box::new(FileExplorerTool{}));
        registry.register(Box::new(NetworkProbeTool{}));
        
        registry
    }

    pub fn load_marketplace_tools(&self) -> Result<()> {
        info!(" [Marketplace] Scanning for custom tools in {}...", self.marketplace_path);
        let paths = std::fs::read_dir(&self.marketplace_path)?;
        for path in paths {
            if let Ok(entry) = path {
                let file_name = entry.file_name().to_string_lossy().into_owned();
                if file_name.ends_with(".wasm") {
                    info!(" [Marketplace] Discovered tool: {}", file_name);
                    // In a full implementation, we'd wrap the WASM in a Tool trait implementation
                }
            }
        }
        Ok(())
    }

    pub fn register(&self, tool: Box<dyn Tool>) {
        if self.verify_permissions(tool.name()) {
            self.tools.insert(tool.name().to_string(), tool);
        } else {
            warn!(" 🔐 [Security] Permission Denied for tool registration: {}", tool.name());
        }
    }

    fn verify_permissions(&self, tool_name: &str) -> bool {
        // --- SECTION 🔐 11. SECURITY MODEL ---
        // Simple allow-list for this graduation
        let allowed = ["system_info", "network_probe", "file_explorer", "search_agent"];
        allowed.contains(&tool_name)
    }

    pub async fn call_tool(&self, name: &str, input: &str) -> Result<String> {
        if let Some(tool) = self.tools.get(name) {
            tool.call(input).await
        } else {
            anyhow::bail!("Tool not found: {}", name)
        }
    }
}

// --- Built-in Tools ---

struct SystemInfoTool;

#[async_trait]
impl Tool for SystemInfoTool {
    fn name(&self) -> &str { "system_info" }
    fn description(&self) -> &str { "Returns system runtime information" }
    async fn call(&self, _input: &str) -> Result<String> {
        Ok(format!("LEVI Runtime v0.2.0 | OS: {} | Kernel: HAL-0", std::env::consts::OS))
    }
}

struct FileExplorerTool;

#[async_trait]
impl Tool for FileExplorerTool {
    fn name(&self) -> &str { "file_explorer" }
    fn description(&self) -> &str { "Lists files in the current working directory" }
    async fn call(&self, _input: &str) -> Result<String> {
        let paths = std::fs::read_dir(".")?;
        let mut files = Vec::new();
        for path in paths {
            if let Ok(entry) = path {
                files.push(entry.file_name().to_string_lossy().into_owned());
            }
        }
        Ok(files.join(", "))
    }
}

struct NetworkProbeTool;

#[async_trait]
impl Tool for NetworkProbeTool {
    fn name(&self) -> &str { "network_probe" }
    fn description(&self) -> &str { "Simulates a network connectivity probe" }
    async fn call(&self, input: &str) -> Result<String> {
        info!(" [Probe] Pinging {}...", input);
        Ok(format!("Success: Responded from {} (latency: 12ms)", input))
    }
}

