// backend/kernel/bare_metal/src/network.rs
use crate::println;
use alloc::vec::Vec;

#[repr(C, packed)]
pub struct EthernetHeader {
    pub dst_mac: [u8; 6],
    pub src_mac: [u8; 6],
    pub ethertype: u16,
}

#[repr(C, packed)]
pub struct Ipv4Header {
    pub version_ihl: u8,
    pub dscp_ecn: u8,
    pub total_length: u16,
    pub identification: u16,
    pub flags_fragment: u16,
    pub ttl: u8,
    pub protocol: u8,
    pub checksum: u16,
    pub src_ip: [u8; 4],
    pub dst_ip: [u8; 4],
}

pub struct SovereignNetStack {
    pub ip_address: [u8; 4],
    pub gateway: [u8; 4],
}

impl SovereignNetStack {
    pub fn new() -> Self {
        Self {
            ip_address: [192, 168, 1, 100],
            gateway: [192, 168, 1, 1],
        }
    }

    pub fn handle_packet(&self, data: &[u8]) {
        if data.len() < 14 { return; }
        
        let eth = unsafe { &*(data.as_ptr() as *const EthernetHeader) };
        let ethertype = u16::from_be(eth.ethertype);
        
        println!(" [NET] Inbound Packet: EtherType 0x{:X}", ethertype);
        
        if ethertype == 0x0800 { // IPv4
            self.handle_ipv4(&data[14..]);
        }
    }

    fn handle_ipv4(&self, data: &[u8]) {
        if data.len() < 20 { return; }
        let ip = unsafe { &*(data.as_ptr() as *const Ipv4Header) };
        
        println!(" [NET] IPv4: From {}.{}.{}.{} -> Protocol {}", 
            ip.src_ip[0], ip.src_ip[1], ip.src_ip[2], ip.src_ip[3], ip.protocol);
        
        // 🌐 DHCP / DNS Hook
        if ip.protocol == 17 { // UDP
             println!(" [NET] UDP Segment detected. Checking for DCN Pulse...");
        }
    }
}
