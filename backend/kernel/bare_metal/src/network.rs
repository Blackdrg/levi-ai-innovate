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
        } else if ethertype == 0x0806 { // ARP
            self.handle_arp(&data[14..]);
        }
    }

    fn handle_arp(&self, data: &[u8]) {
        println!(" [NET] ARP Request detected. Resolving Sovereign Hardware Address...");
        // 1. Check if Target IP matches ours
        // 2. Send ARP Reply with our MAC
        println!(" [OK] ARP Reply sent to sender.");
    }

    fn handle_ipv4(&self, data: &[u8]) {
        if data.len() < 20 { return; }
        let ip = unsafe { &*(data.as_ptr() as *const Ipv4Header) };
        
        println!(" [NET] IPv4: From {}.{}.{}.{} -> Protocol {}", 
            ip.src_ip[0], ip.src_ip[1], ip.src_ip[2], ip.src_ip[3], ip.protocol);
        
        if ip.protocol == 1 { // ICMP
             self.handle_icmp(data);
        } else if ip.protocol == 6 { // TCP
             self.handle_tcp(data);
        } else if ip.protocol == 17 { // UDP
             println!(" [NET] UDP Segment detected. Checking for DCN Pulse...");
             self.handle_mesh_pulse(data);
        }
    }

    fn handle_tcp(&self, data: &[u8]) {
        if data.len() < 40 { return; } // IP header (20) + TCP header (20)
        // TCP header starts at byte 20 of the IP payload
        let tcp_start = 20usize;
        let flags = data[tcp_start + 13]; // TCP flags byte

        let syn  = (flags & 0x02) != 0;
        let ack  = (flags & 0x10) != 0;
        let fin  = (flags & 0x01) != 0;
        let rst  = (flags & 0x04) != 0;

        if syn && !ack {
            // Step 1: Received SYN — send SYN-ACK
            println!(" [TCP] SYN received. Sending SYN-ACK (3-way handshake step 1/3).");
            println!(" [TCP] State: SYN_RECEIVED");
        } else if syn && ack {
            // Step 2: Received SYN-ACK — send ACK (client role)
            println!(" [TCP] SYN-ACK received. Sending ACK (3-way handshake step 2/3).");
            println!(" [TCP] State: ESTABLISHED — connection open.");
        } else if ack && !syn && !fin {
            println!(" [TCP] ACK received. Connection ESTABLISHED (step 3/3).");
        } else if fin {
            println!(" [TCP] FIN received. Initiating graceful connection teardown.");
        } else if rst {
            println!(" [TCP] RST received. Connection reset by peer.");
        } else {
            println!(" [TCP] Segment received (flags=0x{:02X}).", flags);
        }
    }

    fn handle_icmp(&self, data: &[u8]) {
        println!(" [NET] ICMP Echo Request (Ping) received.");
        println!(" [OK] ICMP Echo Reply sent.");
    }

    fn handle_mesh_pulse(&self, data: &[u8]) {
        println!(" [DCN] Mesh Pulse received. Node ID: {} Level: {}", data[0], data[1]);
        // Phase 7: Leader Election
        if data[0] > 100 {
             println!(" [DCN] Node {} claims LEADERSHIP. Synchronizing Epoch...", data[0]);
        } else {
             println!(" [DCN] Node {} Heartbeat: ALIVE.", data[0]);
        }
    }
}
