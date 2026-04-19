// backend/levi_runtime/src/runtime/mod.rs
use std::sync::Arc;
use tokio::sync::Semaphore;
use anyhow::Result;

pub mod daemon;
pub struct RuntimeContext {
    pub semaphore: Arc<Semaphore>,
}

impl RuntimeContext {
    pub fn new(max_concurrency: usize) -> Self {
        Self {
            semaphore: Arc::new(Semaphore::new(max_concurrency)),
        }
    }
}

pub trait LLM: Send + Sync {
    fn generate(&self, prompt: &str) -> Box<dyn std::future::Future<Output = Result<String>> + Send + Unpin + '_>;
}

pub struct OllamaLLM;

impl LLM for OllamaLLM {
    fn generate(&self, prompt: &str) -> Box<dyn std::future::Future<Output = Result<String>> + Send + Unpin + '_> {
        let prompt = prompt.to_string();
        Box::new(Box::pin(async move {
            // Simulated Ollama call
            Ok(format!("LLM Response to: {}", prompt))
        }))
    }
}
