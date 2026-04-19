// backend/kernel/bare_metal/src/serial.rs
use uart_16550::SerialPort;
use spin::Mutex;
use lazy_static::lazy_static;

lazy_static! {
    pub static ref SERIAL1: Mutex<SerialPort> = {
        let mut serial_port = unsafe { SerialPort::new(0x3F8) };
        serial_port.init();
        Mutex::new(serial_port)
    };
}

#[repr(C, packed)]
pub struct TelemetryRecord {
    pub magic: u32,      // 0xDEADBEEF or 0x4C455649
    pub seq_id: u64,
    pub pid: u32,
    pub syscall_id: u8,
    pub timestamp: u32,
    pub fidelity: u8,    // 0-255 score from kernel
}


pub fn write_record(record: &TelemetryRecord) {
    use x86_64::instructions::interrupts;
    interrupts::without_interrupts(|| {
        let mut serial = SERIAL1.lock();
        let bytes = unsafe {
            core::slice::from_raw_parts(
                (record as *const TelemetryRecord) as *const u8,
                core::mem::size_of::<TelemetryRecord>()
            )
        };
        for &b in bytes {
            serial.send(b);
        }
    });
}

#[doc(hidden)]
pub fn _print(args: core::fmt::Arguments) {
    use core::fmt::Write;
    use x86_64::instructions::interrupts;

    interrupts::without_interrupts(|| {
        SERIAL1.lock().write_fmt(args).expect("Printing to serial failed");
    });
}

/// Prints to the host through the serial interface.
#[macro_export]
macro_rules! serial_print {
    ($($arg:tt)*) => {
        $crate::serial::_print(format_args!($($arg)*));
    };
}

/// Prints to the host through the serial interface, appending a newline.
#[macro_export]
macro_rules! serial_println {
    () => ($crate::serial_print!("\n"));
    ($fmt:expr) => ($crate::serial_print!(concat!($fmt, "\n")));
    ($fmt:expr, $($arg:tt)*) => ($crate::serial_print!(
        concat!($fmt, "\n"), $($arg)*));
}
