// backend/kernel/bare_metal/src/keyboard.rs
use alloc::vec::Vec;
use x86_64::instructions::port::Port;
use crate::println;
use pc_keyboard::{layouts, HandleControl, Keyboard, ScancodeSet1, DecodedKey};
use spin::Mutex;
use lazy_static::lazy_static;

lazy_static! {
    static ref KEYBOARD: Mutex<Keyboard<layouts::Us104Key, ScancodeSet1>> =
        Mutex::new(Keyboard::new(layouts::Us104Key, ScancodeSet1,
            HandleControl::Ignore)
        );
    
    static ref INPUT_BUF: Mutex<Vec<char>> = Mutex::new(Vec::with_capacity(128));
}

pub fn handle_interrupt() {
    let mut port = Port::new(0x60);
    let scancode: u8 = unsafe { port.read() };
    let mut keyboard = KEYBOARD.lock();

    if let Ok(Some(key_event)) = keyboard.add_byte(scancode) {
        if let Some(key) = keyboard.process_keyevent(key_event) {
            match key {
                DecodedKey::Unicode(character) => {
                    INPUT_BUF.lock().push(character);
                    println!("{}", character);
                },
                DecodedKey::RawKey(_) => {},
            }
        }
    }
}

pub fn pop_char() -> Option<char> {
    let mut buf = INPUT_BUF.lock();
    if buf.is_empty() {
        None
    } else {
        Some(buf.remove(0))
    }
}
