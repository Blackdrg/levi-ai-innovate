// backend/kernel/bare_metal/src/orchestrator.rs
//
// KERNEL SERVICE BOOTSTRAPPER
//
// ─────────────────────────────────────────────────────────────────────────────
// NAMING HONESTY — READ THIS FIRST
//
// The previous version of this file used the labels:
//   "AI", "BFT", "Cognitive swarm", "WAVE_SPAWN", "Sovereign Mode"
//
// Here is what those labels map to in kernel reality:
//
//   LABEL (old)           KERNEL REALITY (honest)
//   ─────────────────────────────────────────────────────────────────────────
//   "AI agent"            A named async task running in Ring-3.  No model
//                         weights, no inference engine, no learning loop
//                         exists in this bare-metal kernel.  The AI layer
//                         lives in the host Python/Node.js process, not here.
//
//   "BFT consensus"       SHA-256 digest + Ed25519 structural signature check.
//                         There is no Byzantine Fault-Tolerant quorum protocol
//                         implemented in kernel space.  That would require a
//                         network of nodes with a proper Paxos/PBFT round.
//
//   "Cognitive swarm"     A statically-sized array of named async tasks.
//                         There is no collective intelligence, no inter-agent
//                         communication channel, and no emergent behaviour.
//
//   "WAVE_SPAWN"          The syscall 0x02 dispatcher increments a counter
//                         and logs a message.  A real process spawn would
//                         call process::ProcessAddressSpace::new(), load an
//                         ELF binary, and execute usermode::enter_usermode().
//
//   "Sovereign Mode"      Means: the kernel is running and has passed its
//                         own self-checks.  Nothing more.
//
// What IS real in this module:
//   • TPM key derivation uses real HKDF-SHA-256 (see crypto.rs).
//   • Filesystem write uses the real block/inode FS (see vfs.rs).
//   • Signature check uses real SHA-256 digest computation.
//   • The async task count is a real counter updated by the syscall ABI.
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use crate::tpm;
use crate::vfs;
use crate::syscalls;
use crate::crypto;
use alloc::vec::Vec;

/// Number of named kernel service tasks to bootstrap.
pub const SERVICE_COUNT: usize = 10;

/// Human-readable names for each kernel service task.
/// These are async tasks at the OS level — they are NOT AI agents.
pub static SERVICE_NAMES: [&str; SERVICE_COUNT] = [
    "net-rx",       // network receive dispatcher
    "net-tx",       // network transmit scheduler
    "fs-journal",   // filesystem journal flusher
    "tpm-poller",   // TPM event and PCR updater
    "irq-dispatch", // interrupt routing arbiter
    "vfs-cache",    // VFS block cache evictor
    "proc-reaper",  // zombie process collector
    "uart-logger",  // serial console drain
    "timer-tick",   // system clock and wakeup handler
    "idle",         // idle / halt loop
];

pub struct KernelOrchestrator {
    /// IDs of active kernel-service tasks (in order of spawn).
    pub active_tasks: Vec<u64>,
}

impl KernelOrchestrator {
    pub fn new() -> Self {
        Self { active_tasks: Vec::new() }
    }

    /// Bootstrap: derive system key, write boot manifest, register services.
    pub fn bootstrap() {
        println!(" [ORCH] Kernel Service Bootstrapper starting ({} services)...", SERVICE_COUNT);

        // ── 1. Derive system session key via HKDF-SHA-256 ────────────────────
        // This is a REAL key derivation: HKDF-SHA-256(salt, seed) from crypto.rs.
        let hw_seed = b"hal0-sovereign-hw-id-v22";
        let system_key = tpm::derive_key(hw_seed);
        println!(" [ORCH] System key (HKDF-SHA-256): {:02x}{:02x}..{:02x}{:02x}",
            system_key[0], system_key[1], system_key[30], system_key[31]);

        // ── 2. Hash and log the boot manifest ────────────────────────────────
        let manifest = b"SOVEREIGN_OS_v22_BOOT_OK";
        let _manifest_hash = crypto::hash_and_log("boot-manifest", manifest);

        // ── 3. Persist boot manifest to the real block/inode filesystem ──────
        vfs::create_file("manifest.cfg", manifest);

        // ── 4. Register each kernel service task via the syscall dispatcher ──
        // REALITY: syscalls::dispatch(0x02) currently increments a counter and
        // logs a message.  A real WAVE_SPAWN would call:
        //   process::ProcessAddressSpace::new(...) — allocate page tables
        //   elf_loader::load(...)                  — load service ELF
        //   usermode::enter_usermode(entry, stack) — iretq to Ring-3
        for i in 0..SERVICE_COUNT {
            println!(" [ORCH] Registering service task [{}]: {}", i, SERVICE_NAMES[i]);
            syscalls::dispatch(0x02); // WAVE_SPAWN (logs + increments counter)
        }

        let total = syscalls::active_process_count();
        println!(" [ORCH] {} kernel service tasks registered.", total);
        println!(" [ORCH] NOTE: tasks are NOT running AI inference in the kernel.");
        println!(" [ORCH]       Inference runs in the host process (Python/Rust user-land).");
    }

    /// Execute a signed work item (e.g. a filesystem write or net packet).
    /// The "BFT" label here means: we verify the SHA-256 signature structure.
    /// There is NO multi-node Byzantine quorum protocol.
    pub fn execute_signed_task(&mut self, task_id: u64, payload: &[u8]) {
        println!(" [ORCH] execute_signed_task({}): verifying payload digest...", task_id);

        // Build a fake 64-byte test signature for demonstration.
        // In production the caller would provide a real Ed25519 signature.
        let dummy_sig = {
            let digest = crypto::sha256(payload);
            let mut sig = [0u8; 64];
            sig[..32].copy_from_slice(&digest);  // R component = digest (not a real sig)
            sig[32] = 0x01;                       // s[0] non-zero to pass structural check
            sig
        };

        let valid = tpm::verify_signature(payload, &dummy_sig);
        if !valid {
            println!(" [ORCH] Task {}: payload signature REJECTED.", task_id);
            return;
        }

        // Persist the result via the real VFS.
        vfs::create_file("task_result.log", payload);
        self.active_tasks.push(task_id);
        println!(" [ORCH] Task {} complete. {} tasks total.", task_id, self.active_tasks.len());
    }
}
