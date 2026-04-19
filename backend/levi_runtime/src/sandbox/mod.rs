// backend/levi_runtime/src/sandbox/mod.rs
use wasmtime::*;
use anyhow::Result;
use tracing::info;

pub struct WasmSandbox {
    engine: Engine,
}

impl WasmSandbox {
    pub fn new() -> Result<Self> {
        let mut config = Config::new();
        config.async_support(true);
        config.epoch_interruption(true);
        
        let engine = Engine::new(&config)?;
        Ok(Self { engine })
    }

    pub async fn execute_agent_file(&self, path: &str) -> Result<()> {
        info!(" [Sandbox] Loading WASM Agent from {}...", path);
        let wasm_bytes = std::fs::read(path)?;
        self.execute_agent_code(&wasm_bytes).await
    }

    pub async fn execute_agent_code(&self, wasm_bytes: &[u8]) -> Result<()> {
        info!(" [Sandbox] Initialising WASM Agent Execution...");
        
        let module = Module::from_binary(&self.engine, wasm_bytes)?;
        let mut store = Store::new(&self.engine, ());
        
        // Setup imports, memory, etc.
        let mut linker = Linker::new(&self.engine);
        
        // Potential: Add WASI support
        // wasmtime_wasi::add_to_linker(&mut linker, |s| s)?;
        
        let instance = linker.instantiate_async(&mut store, &module).await?;
        let entry = instance.get_typed_func::<(), ()>(&mut store, "_start")?; // Use standard _start
        
        entry.call_async(&mut store, ()).await?;
        
        info!(" [Sandbox] WASM Agent Execution Complete.");
        Ok(())
    }
}

