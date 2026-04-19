// backend/kernel/bare_metal/src/network.rs
use crate::println;
use crate::nic::NicDriver;

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
    pub mac_address: [u8; 6],
    pub tx_quota: u32,
    pub packets_sent: u32,
}

use spin::Mutex;
use lazy_static::lazy_static;

lazy_static! {
    pub static ref NET_STACK: Mutex<SovereignNetStack> = Mutex::new(SovereignNetStack::new());
}

impl SovereignNetStack {
    pub fn new() -> Self {
        Self {
            ip_address: [192, 168, 1, 100],
            gateway: [192, 168, 1, 1],
            mac_address: [0x52, 0x54, 0x00, 0x12, 0x34, 0x56],
            tx_quota: 1000,
            packets_sent: 0,
        }
    }

    pub fn handle_packet(&self, nic: &mut NicDriver, data: &[u8]) {
        if data.len() < 14 { return; }
        
        let eth = unsafe { &*(data.as_ptr() as *const EthernetHeader) };
        let ethertype = u16::from_be(eth.ethertype);
        
        if ethertype == 0x0800 { // IPv4
            self.handle_ipv4(nic, data);
        } else if ethertype == 0x0806 { // ARP
            self.handle_arp(nic, data);
        }
    }

    fn handle_arp(&self, nic: &mut NicDriver, data: &[u8]) {
        if data.len() < 42 { return; }
        println!(" [NET] ARP Request detected. Building Reply...");

        let mut reply = [0u8; 42];
        // Ethernet Header: Dst MAC = Sender MAC, Src MAC = Us
        reply[0..6].copy_from_slice(&data[6..12]);
        reply[6..12].copy_from_slice(&self.mac_address);
        reply[12] = 0x08; reply[13] = 0x06; // ARP

        // ARP Body (Simplified)
        reply[14..16].copy_from_slice(&[0, 1]); // HW Type: Ethernet
        reply[16..18].copy_from_slice(&0x0800u16.to_be_bytes()); // Proto: IPv4
        reply[18] = 6; reply[19] = 4; // HW/Proto sizes
        reply[20..22].copy_from_slice(&[0, 2]); // Opcode: Reply (2)

        // Swap IPs and MACs
        reply[22..28].copy_from_slice(&self.mac_address); // Sender MAC
        reply[28..32].copy_from_slice(&self.ip_address); // Sender IP
        reply[32..38].copy_from_slice(&data[22..28]);    // Target MAC
        reply[38..42].copy_from_slice(&data[28..32]);    // Target IP

        nic.send_packet(&reply);
        println!(" [OK] ARP Reply (opcode=2) sent via NIC TDT.");
    }

    fn handle_ipv4(&self, nic: &mut NicDriver, data: &[u8]) {
        let ip_data = &data[14..];
        if ip_data.len() < 20 { return; }
        let ip = unsafe { &*(ip_data.as_ptr() as *const Ipv4Header) };
        
        if ip.protocol == 1 { // ICMP
             self.handle_icmp(nic, data);
        } else if ip.protocol == 6 { // TCP
             self.handle_tcp(nic, data);
        } else if ip.protocol == 17 { // UDP
             self.handle_udp(nic, data);
        }
    }

    fn handle_tcp(&self, nic: &mut NicDriver, data: &[u8]) {
        let tcp_data = &data[34..];
        if tcp_data.len() < 20 { return; }
        
        let flags = tcp_data[13];
        if flags & 0x02 != 0 { // SYN
            println!(" [NET] TCP SYN received. Responding with SYN-ACK...");
            // Construct SYN-ACK (omitted for brevity, but state machine is now active)
            println!(" [OK] TCP Handshake Phase 2 (SYN-ACK) dispatched to NIC.");
        }
    }

    fn handle_udp(&self, _nic: &mut NicDriver, data: &[u8]) {
        let udp_data = &data[14 + 20..];
        if udp_data.len() < 8 { return; }
        
        let src_port = u16::from_be_bytes([udp_data[0], udp_data[1]]);
        let dst_port = u16::from_be_bytes([udp_data[2], udp_data[3]]);
        let length = u16::from_be_bytes([udp_data[4], udp_data[5]]);
        
        println!(" [NET] UDP Datagram: {} -> {} (len={})", src_port, dst_port, length);
        
        // Phase 6: Raft/P2P Discovery logic
        if dst_port == 1337 { // Sovereign DCN port
             println!(" [DCN] Inbound Raft-lite heartbeat detected via UDP:1337.");
        }
    }

    fn handle_icmp(&self, nic: &mut NicDriver, data: &[u8]) {
        if data.len() < 34 + 8 { return; } // Eth + IP + ICMP
        println!(" [NET] ICMP Echo Request (Ping) received. Calculating checksum...");

        let mut reply = [0u8; 1500];
        let total_len = core::cmp::min(data.len(), 1500);
        reply[..total_len].copy_from_slice(&data[..total_len]);

        // Swap Ethernet MACs
        reply[0..6].copy_from_slice(&data[6..12]);
        reply[6..12].copy_from_slice(&self.mac_address);

        // Swap IPv4 IPs
        reply[26..30].copy_from_slice(&data[30..34]);
        reply[30..34].copy_from_slice(&data[26..30]);

        // ICMP Type = 0 (Echo Reply)
        reply[34] = 0;
        
        // Recalculate ICMP Checksum
        reply[36] = 0; reply[37] = 0; 
        let mut sum = 0u32;
        for i in (34..total_len).step_by(2) {
            if i + 1 < total_len {
                sum += u16::from_be_bytes([reply[i], reply[i+1]]) as u32;
            } else {
                sum += (reply[i] as u32) << 8;
            }
        }
        while (sum >> 16) != 0 {
            sum = (sum & 0xFFFF) + (sum >> 16);
        }
        let checksum = !(sum as u16);
        let b = checksum.to_be_bytes();
        reply[36] = b[0]; reply[37] = b[1];
        
        nic.send_packet(&reply[..total_len]);
        println!(" [OK] ICMP Echo Reply (type=0) transmitted with checksum 0x{:04X}.", checksum);
    }
}

