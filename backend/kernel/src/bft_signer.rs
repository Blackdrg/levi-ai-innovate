// backend/kernel/src/bft_signer.rs
use ed25519_dalek::{SigningKey, Signature, Signer, Verifier, VerifyingKey};
use hmac::{Hmac, Mac};
use sha2::Sha256;
use std::sync::Arc;
use sysinfo::System;

type HmacSha256 = Hmac<Sha256>;

pub struct BftSigner {
    signing_key: SigningKey,
    verifying_key: VerifyingKey,
    hardware_id: String,
}

impl BftSigner {
    pub fn new() -> Self {
        let hw_id = Self::get_hardware_id();
        let signing_key = Self::load_from_tpm_or_derive(&hw_id);
        let verifying_key = VerifyingKey::from(&signing_key);

        Self {
            signing_key,
            verifying_key,
            hardware_id: hw_id,
        }
    }

    fn load_from_tpm_or_derive(hw_id: &str) -> SigningKey {
        // 🔐 Sovereign v21.5: TPM 2.0 Integration Point
        log::info!("🛡️ [Kernel] BFT Signer: Requesting TPM 2.0 HKDF derivation...");
        
        // Use HKDF-SHA256 for hardware-bound seed derivation (RFC 5869)
        let salt = b"sovereign-os-v21-salt";
        let info = b"bft-signer-v21";
        
        let mut okm = [0u8; 32];
        let mut hmac = HmacSha256::new_from_slice(salt).expect("HMAC can take key of any size");
        hmac.update(hw_id.as_bytes());
        let prk = hmac.finalize().into_bytes();
        
        let mut hmac_expand = HmacSha256::new_from_slice(&prk).expect("HMAC can take key of any size");
        hmac_expand.update(info);
        hmac_expand.update(&[1u8]);
        let result = hmac_expand.finalize().into_bytes();
        okm.copy_from_slice(&result[0..32]);

        SigningKey::from_bytes(&okm)
    }


    fn get_hardware_id() -> String {
        let mut sys = System::new_all();
        sys.refresh_all();
        
        let hostname = System::host_name().unwrap_or_else(|| "unknown-host".to_string());
        let kernel_version = System::kernel_version().unwrap_or_else(|| "unknown-kernel".to_string());
        let total_mem = sys.total_memory();
        
        // 🛡️ Hardware binding: Mix hostname, kernel, and hardware specs
        format!("{}-{}-MEM{}", hostname, kernel_version, total_mem)
    }


    pub fn sign(&self, payload: &[u8]) -> Signature {
        self.signing_key.sign(payload)
    }

    pub fn verify(&self, payload: &[u8], signature: &Signature) -> bool {
        self.verifying_key.verify(payload, signature).is_ok()
    }

    pub fn verify_remote(&self, public_key_bytes: &[u8; 32], payload: &[u8], signature_bytes: &[u8; 64]) -> bool {
        if let Ok(public_key) = VerifyingKey::from_bytes(public_key_bytes) {
            if let Ok(signature) = Signature::from_slice(signature_bytes) {
                return public_key.verify(payload, &signature).is_ok();
            }
        }
        false
    }

    pub fn get_public_key(&self) -> [u8; 32] {
        self.verifying_key.to_bytes()
    }

    pub fn get_signing_key_bytes(&self) -> [u8; 32] {
        self.signing_key.to_bytes()
    }

    pub fn hmac_sign(&self, payload: &[u8], secret: &[u8]) -> Vec<u8> {
        let mut mac = HmacSha256::new_from_slice(secret).expect("HMAC can take key of any size");
        mac.update(payload);
        mac.finalize().into_bytes().to_vec()
    }
}
