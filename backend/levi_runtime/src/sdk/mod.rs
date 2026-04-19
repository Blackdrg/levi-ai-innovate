// backend/levi_runtime/src/sdk/mod.rs
use anyhow::Result;
use async_trait::async_trait;
use serde::{Serialize, Deserialize};
use uuid::Uuid;

#[async_trait]
pub trait Agent: Send + Sync {
    fn id(&self) -> Uuid;
    fn metadata(&self) -> AgentMetadata;
    async fn execute(&self, input: String) -> Result<String>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMetadata {
    pub name: String,
    pub version: String,
    pub capabilities: Vec<String>,
}

use serde_json::Value;

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    async fn execute(&self, input: Value) -> Result<Value>;
}


// Macro to simplify agent creation for developers
#[macro_export]
macro_rules! define_agent {
    ($name:ident, $title:expr, $vers:expr, $caps:expr, $body:expr) => {
        pub struct $name {
            pub id: uuid::Uuid,
        }
        
        impl $name {
            pub fn new() -> Self {
                Self { id: uuid::Uuid::new_v4() }
            }
        }
        
        #[async_trait::async_trait]
        impl $crate::sdk::Agent for $name {
            fn id(&self) -> uuid::Uuid { self.id }
            fn metadata(&self) -> $crate::sdk::AgentMetadata {
                $crate::sdk::AgentMetadata {
                    name: $title.to_string(),
                    version: $vers.to_string(),
                    capabilities: $caps.iter().map(|s| s.to_string()).collect(),
                }
            }
            async fn execute(&self, input: String) -> anyhow::Result<String> {
                let func = $body;
                func(input).await
            }
        }
    };
}
