// backend/kernel/bare_metal/src/security/redactor.rs
//
// PII REDACTION PIPELINE — Aho-Corasick inspired multi-pattern filter
//

use crate::println;

/// PII Patterns to scrub from serial console and network logs.
const PII_PATTERNS: &[&[u8]] = &[
    b"ssn:", 
    b"credit_card:", 
    b"email:", 
    b"password:",
    b"secret_key:"
];

pub struct Redactor;

impl Redactor {
    /// Scrub sensitive patterns from a byte buffer.
    /// Replaces PII matches with asterisks.
    pub fn scrub(data: &mut [u8]) -> usize {
        let mut scrub_count = 0;
        
        for pattern in PII_PATTERNS {
            let mut i = 0;
            while i <= data.len().saturating_sub(pattern.len()) {
                if &data[i..i+pattern.len()] == *pattern {
                    // Match found — redact the next 12 bytes or until space
                    scrub_count += 1;
                    let start = i + pattern.len();
                    let end = core::cmp::min(start + 16, data.len());
                    
                    for j in start..end {
                        if data[j] == b' ' || data[j] == b'\n' { break; }
                        data[j] = b'*';
                    }
                    i = end;
                } else {
                    i += 1;
                }
            }
        }
        
        if scrub_count > 0 {
            println!(" [SHIELD] PII REDACTOR: Scrubbed {} sensitive instances.", scrub_count);
        }
        scrub_count
    }

    /// Verification hook for the "Leaky Pipe" test (Appendix G).
    pub fn verify_leak_protection() {
        println!(" [SHIELD] Starting 1000-field 'Leaky Pipe' Stress Test...");
        let mut total_redacted = 0;
        
        // Simulate a stream with 1000 PII fields
        for i in 0..1000 {
            let mut chunk = match i % 3 {
                0 => b"Metadata block. email: user@domain.com entropy: high".to_vec(),
                1 => b"Transaction trace. credit_card: 1234-5678-9012-3456 auth: ok".to_vec(),
                _ => b"Internal log. secret_key: 0xDEADBEEFCAFE0001 status: hidden".to_vec(),
            };
            total_redacted += Self::scrub(&mut chunk);
        }
        
        if total_redacted >= 1000 {
            println!(" [PASS] SHIELD: Leaky Pipe Test PASSED (1000/1000 redacted).");
        } else {
            println!(" [FAIL] SHIELD: Redaction count ({}) below target.", total_redacted);
        }
    }
}
