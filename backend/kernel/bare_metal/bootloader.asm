; backend/kernel/bare_metal/bootloader.asm
; Sovereign v17.5.0: Native Bootloader Entry (Legacy BIOS)
[org 0x7c00]

start:
    cli                         ; Disable interrupts
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00

    mov si, boot_msg
    call print_string

    ; 🔧 Transition to Protected Mode (Conceptual)
    ; 1. Load GDT (Global Descriptor Table)
    ; 2. Set PE bit in CR0
    ; 3. Jump to 32-bit segment
    
    ; 🧠 Graduation Goal: Load Rust Kernel Binary from Disk
    call load_rust_kernel
    
    hlt

print_string:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0e
    int 0x10
    jmp print_string
.done:
    ret

load_rust_kernel:
    ; Use INT 0x13 to load higher sectors into memory
    ret

boot_msg db 'LEVI SOVEREIGN OS: GRADUATING TO BARE-METAL...', 0

times 510-($-$$) db 0
dw 0xaa55 ; Boot signature
