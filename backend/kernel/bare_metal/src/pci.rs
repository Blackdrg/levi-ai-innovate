// backend/kernel/bare_metal/src/pci.rs
use x86_64::instructions::port::Port;
use crate::println;

pub struct PciDevice {
    pub bus: u8,
    pub device: u8,
    pub function: u8,
    pub vendor_id: u16,
    pub device_id: u16,
}

pub fn check_all_buses() {
    for bus in 0..256 {
        for device in 0..32 {
            check_device(bus as u8, device as u8);
        }
    }
}

fn check_device(bus: u8, device: u8) {
    let function = 0;
    let vendor_id = pci_config_read_word(bus, device, function, 0);
    if vendor_id == 0xFFFF { return; }
    
    let device_id = pci_config_read_word(bus, device, function, 2);
    println!(" [PCI] Device Found: Vendor 0x{:X}, Device 0x{:X}", vendor_id, device_id);

    // If it's a NIC (e.g. Intel 82540EM)
    if vendor_id == 0x8086 && device_id == 0x100E {
        println!("  -> Sovereign NIC (Intel e1000) Identified.");
    }
}

fn pci_config_read_word(bus: u8, device: u8, func: u8, offset: u8) -> u16 {
    let address = ((bus as u32) << 16) | ((device as u32) << 11) |
                  ((func as u32) << 8) | (offset as u32 & 0xFC) | 0x80000000;
                  
    let mut addr_port = Port::new(0xCF8);
    let mut data_port = Port::new(0xCFC);

    unsafe {
        addr_port.write(address);
        ((data_port.read() >> ((offset & 2) * 8)) & 0xFFFF) as u16
    }
}
