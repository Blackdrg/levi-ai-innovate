// backend/kernel/bare_metal/src/ata.rs
use x86_64::instructions::port::Port;
use spin::Mutex;
use lazy_static::lazy_static;

const DATA_PORT: u16 = 0x1F0;
const ERROR_PORT: u16 = 0x1F1;
const SECTOR_COUNT_PORT: u16 = 0x1F2;
const LBA_LOW_PORT: u16 = 0x1F3;
const LBA_MID_PORT: u16 = 0x1F4;
const LBA_HIGH_PORT: u16 = 0x1F5;
const DRIVE_HEAD_PORT: u16 = 0x1F6;
const COMMAND_STATUS_PORT: u16 = 0x1F7;

pub struct AtaDriver {
    data: Port<u16>,
    error: Port<u8>,
    sector_count: Port<u8>,
    lba_low: Port<u8>,
    lba_mid: Port<u8>,
    lba_high: Port<u8>,
    drive_head: Port<u8>,
    command_status: Port<u8>,
}

impl AtaDriver {
    pub fn new() -> Self {
        Self {
            data: Port::new(DATA_PORT),
            error: Port::new(ERROR_PORT),
            sector_count: Port::new(SECTOR_COUNT_PORT),
            lba_low: Port::new(LBA_LOW_PORT),
            lba_mid: Port::new(LBA_MID_PORT),
            lba_high: Port::new(LBA_HIGH_PORT),
            drive_head: Port::new(DRIVE_HEAD_PORT),
            command_status: Port::new(COMMAND_STATUS_PORT),
        }
    }

    pub fn read_sectors(&mut self, lba: u32, sector_count: u8, target: &mut [u16]) {
        unsafe {
            self.drive_head.write(0xE0 | (u8::try_from((lba >> 24) & 0x0F).unwrap()));
            self.sector_count.write(sector_count);
            self.lba_low.write(u8::try_from(lba & 0xFF).unwrap());
            self.lba_mid.write(u8::try_from((lba >> 8) & 0xFF).unwrap());
            self.lba_high.write(u8::try_from((lba >> 16) & 0xFF).unwrap());
            self.command_status.write(0x20); // Command: Read with retry

            while (self.command_status.read() & 0x80) != 0 {} // Wait for not busy
            while (self.command_status.read() & 0x08) == 0 {} // Wait for DRQ

            for i in 0..target.len() {
                target[i] = self.data.read();
            }
        }
    }
}

lazy_static! {
    pub static ref ATA_PRIMARY: Mutex<AtaDriver> = Mutex::new(AtaDriver::new());
}
