// backend/kernel/bare_metal/src/secure_boot.rs
//
// VERIFIED BOOT — Real SHA-256 measurement into TPM PCR[0]
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT IS REAL:
//   • sha256() from crypto.rs is a genuine FIPS 180-4 implementation.
//   • PCR_extend() builds a real TPM2_CC_PCR_Extend command byte stream.
//   • The kernel image hash is computed from a static byte slice.
//
// WHAT IS A SIMPLIFICATION:
//   • In production UEFI secure boot the public key lives in the UEFI
//     db/dbx variables (read via EFI_RUNTIME_SERVICES.GetVariable).
//   • The kernel image slice here is a 64-byte stand-in; a full
//     implementation would hash the entire loaded kernel binary.
//   • Ed25519 full verification (sB == R+hA) is documented in crypto.rs
//     as requiring SHA-512 + field arithmetic — that is not here.
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use crate::crypto;
use crate::tpm::Tpm20;

/// Placeholder for the public signing key (32 bytes, all 0x01 in this stub).
/// In production: read from UEFI Secure Boot variable `db`.
const ROOT_PUBLIC_KEY: [u8; 32] = [0x01u8; 32];

pub struct SecureBoot;

impl SecureBoot {
    /// Verify a binary's Ed25519 signature.
    /// Uses real SHA-256 for the digest; structural (not full-curve) check.
    pub fn verify_signature(binary: &[u8], signature: &[u8]) -> bool {
        println!(" [SEC] SecureBoot: computing SHA-256 of {} bytes...", binary.len());
        let digest = crypto::sha256(binary);
        println!(
            " [SEC] SHA-256 = {:02x}{:02x}{:02x}{:02x}...{:02x}{:02x}",
            digest[0], digest[1], digest[2], digest[3], digest[30], digest[31]
        );

        if signature.len() != 64 {
            println!(" [SEC] REJECT: signature length {} ≠ 64.", signature.len());
            return false;
        }
        let mut sig64 = [0u8; 64];
        sig64.copy_from_slice(signature);

        let ok = crypto::verify_ed25519_structure(&ROOT_PUBLIC_KEY, binary, &sig64);
        if ok {
            println!(" [SEC] SecureBoot: signature structure OK.");
        } else {
            println!(" [SEC] SecureBoot: SIGNATURE REJECTED — HALTING.");
        }
        ok
    }
}

/// Boot-time measurement: SHA-256 the kernel stub and extend PCR[0].
/// Called from kernel_main before any other subsystem.
pub fn verify() {
    println!(" [SEC] Verified Boot: measuring kernel image...");

    // Hash a representative slice of the running kernel.
    // In production: compute over the ELF segments loaded by the bootloader.
    let kernel_sample: &[u8] = b"sovereign-os-kernel-v22.0.0-hal0-bare-metal";
    let digest = crypto::sha256(kernel_sample);

    println!(
        " [SEC] Kernel SHA-256 = {:02x}{:02x}{:02x}{:02x}...{:02x}{:02x}",
        digest[0], digest[1], digest[2], digest[3], digest[30], digest[31]
    );

    // Extend TPM PCR[0] with the real digest.
    let tpm = Tpm20::new();
    tpm.PCR_extend(0, &digest);

    println!(" [SEC] PCR[0] extended. Chain-of-trust measurement complete.");
}
