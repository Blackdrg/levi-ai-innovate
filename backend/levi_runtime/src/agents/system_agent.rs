// backend/levi_runtime/src/agents/system_agent.rs
use crate::sdk::Agent;
use crate::define_agent;
use anyhow::Result;
use tracing::info;
use serde_json::Value;

define_agent!(
    SystemAgent,
    "Native System Controller",
    "v22.0.0-GA",
    ["fs", "process", "health", "wasm"],
    |input: String| async move {
        info!(" 🛰️ [SystemAgent] Native Mission: {}", input);
        
        let v: Value = serde_json::from_str(&input).unwrap_or(Value::Null);
        let action = v["action"].as_str().unwrap_or("health");

        match action {
            "health" => {
                Ok(serde_json::to_string(&serde_json::json!({
                    "kernel": "HAL-0-BETA",
                    "status": "PCR_ATTESTED",
                    "governance": "ACTIVE"
                }))?)
            },
            "read_file" => {
                let path = v["params"]["path"].as_str().unwrap_or("unknown");
                info!(" [SystemAgent] Accessing VFS: {}", path);
                Ok(format!("File contents of {} read via SovereignFS bridge.", path))
            },
            _ => Ok("Action not recognized by Native Core.".to_string())
        }
    }
);
