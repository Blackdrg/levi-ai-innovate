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
        // Derive key from hardware ID for "hardware-aware" sovereignty
        let hw_id = Self::get_hardware_id();
        let mut seed = [0u8; 32];
        let bytes = hw_id.as_bytes();
        for (i, &b) in bytes.iter().enumerate() {
            seed[i % 32] ^= b;
        }
        
        let signing_key = SigningKey::from_bytes(&seed);
        let verifying_key = VerifyingKey::from(&signing_key);

        Self {
            signing_key,
            verifying_key,
            hardware_id: hw_id,
        }
    }

    fn get_hardware_id() -> String {
        let mut sys = System::new_all();
        sys.refresh_all();
        
        let hostname = System::host_name().unwrap_or_else(|| "unknown-host".to_string());
        let kernel_version = System::kernel_version().unwrap_or_else(|| "unknown-kernel".to_string());
        
        format!("{}-{}", hostname, kernel_version)
    }

    pub fn sign(&self, payload: &[u8]) -> Signature {
        self.signing_key.sign(payload)
    }

    pub fn verify(&self, payload: &[u8], signature: &Signature) -> bool {
        self.verifying_key.verify(payload, signature).is_ok()
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
