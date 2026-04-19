// backend/kernel/bare_metal/src/crypto.rs
//
// HARDENED CRYPTOGRAPHY — SHA-256 + HKDF + Ed25519 (via crates)
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT IS REAL IN THIS MODULE:
//
//   1. SHA-256 — via `sha2` crate (FIPS 180-4 compliant).
//   2. HKDF-SHA-256 — via `hkdf` crate (RFC 5869 compliant).
//   3. Ed25519 — via `ed25519-dalek` crate (RFC 8032 compliant).
//      Perform s·B == R + H(R‖A‖M)·A check with SHA-512 internally.
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use sha2::{Sha256, Digest};
use ring::signature::{self, UnparsedPublicKey};
use ring::hkdf::{self, HKDF_SHA256};

/// Compute a real SHA-256 digest of `msg` using the `sha2` crate.
pub fn sha256(msg: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(msg);
    let result = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&result);
    out
}

/// Derive a 32-byte key from a hardware seed using HKDF-SHA-256 (RFC 5869).
pub fn derive_key_hkdf(seed: &[u8], context: &[u8]) -> [u8; 32] {
    let salt = ring::hkdf::Salt::new(HKDF_SHA256, b"sovereign-os-v21-salt");
    let prk = salt.extract(seed);
    let okm = prk.expand(&[context], HKDF_SHA256).expect("HKDF expansion failed");
    
    let mut out = [0u8; 32];
    okm.fill(&mut out).expect("HKDF fill failed");

    println!(" [CRYPTO] HKDF-SHA-256 key derived: {:02x}{:02x}...{:02x}{:02x}",
        out[0], out[1], out[30], out[31]);
    out
}

/// Verify an Ed25519 signature using `ring`.
pub fn verify_ed25519(public_key: &[u8; 32], message: &[u8], signature_bytes: &[u8; 64]) -> bool {
    let peer_public_key = UnparsedPublicKey::new(&signature::ED25519, public_key);
    
    match peer_public_key.verify(message, signature_bytes) {
        Ok(_) => {
            println!(" [CRYPTO] Ed25519: Signature VALID (verified via ring)");
            true
        }
        Err(_) => {
            println!(" [CRYPTO] Ed25519: Signature INVALID — REJECTED");
            false
        }
    }
}

/// Back-compat wrapper for the structural check.
pub fn verify_ed25519_structure(public_key: &[u8; 32], message: &[u8], signature: &[u8; 64]) -> bool {
    verify_ed25519(public_key, message, signature)
}

/// Sign a message using Ed25519 via the `ed25519-dalek` crate.
pub fn sign_ed25519(seed: &[u8; 32], message: &[u8]) -> [u8; 64] {
    use ed25519_dalek::{SigningKey, Signer};
    let signing_key = SigningKey::from_bytes(seed);
    let signature = signing_key.sign(message);
    let sig_bytes = signature.to_bytes();
    println!(" [CRYPTO] Ed25519: Message signed (64 bytes generated)");
    sig_bytes
}

/// SHA-256 of `data`, printed for audit.
pub fn hash_and_log(label: &str, data: &[u8]) -> [u8; 32] {
    let digest = sha256(data);
    println!(" [CRYPTO] SHA-256({}) = {:02x}{:02x}{:02x}{:02x}...{:02x}{:02x}",
        label,
        digest[0], digest[1], digest[2], digest[3],
        digest[30], digest[31]);
    digest
}
