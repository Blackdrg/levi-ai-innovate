// backend/kernel/src/network_stack.rs
use std::collections::VecDeque;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IPv4Packet {
    pub source: [u8; 4],
    pub destination: [u8; 4],
    pub protocol: u8, // 6 = TCP, 17 = UDP
    pub payload: Vec<u8>,
}

pub struct SovereignNetworkStack {
    pub rx_queue: VecDeque<IPv4Packet>,
    pub tx_queue: VecDeque<IPv4Packet>,
    pub routing_table: std::collections::HashMap<[u8; 4], String>, // IP -> Interface
}

impl SovereignNetworkStack {
    pub fn new() -> Self {
        Self {
            rx_queue: VecDeque::new(),
            tx_queue: VecDeque::new(),
            routing_table: std::collections::HashMap::new(),
        }
    }

    pub fn receive_packet(&mut self, packet: IPv4Packet) {
        log::info!("🌐 [Network] Received packet from {:?}", packet.source);
        self.rx_queue.push_back(packet);
    }

    pub fn process_queues(&mut self) {
        // Handle TCP state machine simulation
        while let Some(packet) = self.rx_queue.pop_front() {
            if packet.protocol == 6 {
                log::debug!("TCP Packet processed for port binding.");
            }
        }
    }

    pub fn send_packet(&mut self, dest: [u8; 4], payload: Vec<u8>) {
        let packet = IPv4Packet {
            source: [127, 0, 0, 1],
            destination: dest,
            protocol: 6,
            payload,
        };
        self.tx_queue.push_back(packet);
        log::info!("🌐 [Network] Packet queued for transmission to {:?}", dest);
    }
}
