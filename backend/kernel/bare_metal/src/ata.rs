// backend/kernel/bare_metal/src/ata.rs
use x86_64::instructions::port::Port;
use spin::Mutex;
use lazy_static::lazy_static;

pub struct AtaDriver {
    pub io_base: u16,
}

impl AtaDriver {
    pub fn new() -> Self {
        Self { io_base: 0x1F0 }
    }

    /// Read sectors from disk using PIO mode.
    pub fn read_sectors(&mut self, lba: u32, sector_count: u8, target: &mut [u16]) {
        unsafe {
            self.wait_for_ready();
            // 0x1F6: Drive/Head
            Port::<u8>::new(self.io_base + 6).write(0xE0 | (u8::try_from((lba >> 24) & 0x0F).unwrap()));
            // 0x1F2: Sector Count
            Port::<u8>::new(self.io_base + 2).write(sector_count);
            // 0x1F3: LBA Low
            Port::<u8>::new(self.io_base + 3).write(u8::try_from(lba & 0xFF).unwrap());
            // 0x1F4: LBA Mid
            Port::<u8>::new(self.io_base + 4).write(u8::try_from((lba >> 8) & 0xFF).unwrap());
            // 0x1F5: LBA High
            Port::<u8>::new(self.io_base + 5).write(u8::try_from((lba >> 16) & 0xFF).unwrap());
            // 0x1F7: Command (Read Sectors)
            Port::<u8>::new(self.io_base + 7).write(0x20u8);

            self.wait_for_ready();

            for i in 0..target.len() {
                // 0x1F0: Data Port (16-bit)
                target[i] = Port::<u16>::new(self.io_base).read();
            }
        }
    }

    /// Write sectors to disk using PIO mode.
    pub fn write_sectors(&mut self, lba: u32, sector_count: u8, source: &[u16]) {
        unsafe {
            self.wait_for_ready();
            Port::<u8>::new(self.io_base + 6).write(0xE0 | (u8::try_from((lba >> 24) & 0x0F).unwrap()));
            Port::<u8>::new(self.io_base + 2).write(sector_count);
            Port::<u8>::new(self.io_base + 3).write(u8::try_from(lba & 0xFF).unwrap());
            Port::<u8>::new(self.io_base + 4).write(u8::try_from((lba >> 8) & 0xFF).unwrap());
            Port::<u8>::new(self.io_base + 5).write(u8::try_from((lba >> 16) & 0xFF).unwrap());
            Port::<u8>::new(self.io_base + 7).write(0x30u8); // Command: Write Sectors
            
            // K-5: Poll DRQ before writing payload
            self.wait_for_drq().expect("ATA: DRQ poll failed during write");

            for i in 0..source.len() {
                Port::<u16>::new(self.io_base).write(source[i]);
            }
            
            // Task: Issue FLUSH CACHE (0xE7) to ensure persistence.
            Port::<u8>::new(self.io_base + 7).write(0xE7u8);
            self.wait_for_ready();
        }
    }

    fn wait_for_ready(&mut self) -> Result<(), &'static str> {
        unsafe {
            let mut status_port = Port::<u8>::new(self.io_base + 7);
            let mut timeout = 0;
            
            // Poll for BSY to clear
            while (status_port.read() & 0x80) != 0 {
                timeout += 1;
                if timeout > 1_000_000 { return Err("ATA Timeout: BSY stuck"); }
            }

            // Check for error bit
            if (status_port.read() & 0x01) != 0 {
                return Err("ATA Error detected in status register");
            }

            Ok(())
        }
    }

    fn wait_for_drq(&mut self) -> Result<(), &'static str> {
        unsafe {
            let mut status_port = Port::<u8>::new(self.io_base + 7);
            let mut timeout = 0;
            while (status_port.read() & 0x08) == 0 {
                timeout += 1;
                if timeout > 1_000_000 { return Err("ATA Timeout: DRQ not set"); }
            }
            Ok(())
        }
    }
}


lazy_static! {
    pub static ref ATA_PRIMARY: Mutex<AtaDriver> = Mutex::new(AtaDriver::new());
}

pub fn read_sectors(lba: u32, sector_count: u8, target: &mut [u16]) {
    ATA_PRIMARY.lock().read_sectors(lba, sector_count, target);
}

pub fn write_sectors(lba: u32, sector_count: u8, source: &[u16]) {
    ATA_PRIMARY.lock().write_sectors(lba, sector_count, source);
}