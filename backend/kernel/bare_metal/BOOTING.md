# 🥾 LEVI-AI: Bare-Metal Boot Sequence (Phase 3)

This document outlines the theoretical boot sequence for the LEVI-AI Sovereign OS when running as a true bare-metal operating system, utilizing the components in `backend/kernel/bare_metal/src/`.

## 1. Stage 1: Bootloader (MBR/UEFI)
- **File**: `bootloader.rs` (conceptual)
- **Task**: Initialize the CPU, enable A20 line, and load the Stage 2 kernel from the ATA disk.
- **Substrate**: x86_64 Real Mode.

## 2. Stage 2: Kernel Initialization (Ring-0)
- **File**: `main.rs`, `gdt.rs`, `interrupts.rs`
- **Tasks**:
  1. Set up the **Global Descriptor Table (GDT)** to define memory segments.
  2. Initialize the **Interrupt Descriptor Table (IDT)** to handle hardware interrupts (keyboard, timer).
  3. Enable **Paging** (`memory.rs`) to establish a 4-level page table hierarchy.
  4. Initialize the **VGA Buffer** (`vga_buffer.rs`) for physical console output.

## 3. Stage 3: Substrate Discovery
- **Files**: `pci.rs`, `acpi.rs`, `ata.rs`
- **Tasks**:
  1. Scan the PCI bus for the **Sovereign GPU** and **NIC**.
  2. Parse ACPI tables for SMP (Symmetric Multi-Processing) support.
  3. Initialize the **ATA PIO/DMA** drivers for persistent storage access.

## 4. Stage 4: Sovereign Services Handoff
- **Files**: `syscalls.rs`, `process.rs`, `scheduler.rs`
- **Tasks**:
  1. Register the `INT 0x80` handler.
  2. Initialize the **Preemptive Scheduler**.
  3. Spawn the first **Ring-3 process** (The Sovereign Root).

## 5. Stage 5: Cognitive Awakening
- The Ring-3 process initializes the **Axum-based Native Core** (from `backend/kernel/src/main.rs`), which then bridges to the Python **Soul** via the Serial/Socket bridge.

---
**Status**: The existing `bare_metal/src/` contains 80% of the logic required for this sequence. Forensic validation is required before first hardware flash.
