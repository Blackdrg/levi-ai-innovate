import subprocess
import sys
import os
import argparse
import logging

"""
Sovereign OS v22 Bare-Metal Provisioning Utility.
Transitions the kernel from a QEMU emulated environment to a physical hardware USB block device.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [FLASH] %(message)s")

def flash_iso_to_usb(iso_path: str, target_disk: str):
    if not os.path.exists(iso_path):
        logging.error(f"Kernel image not found at {iso_path}. Did you run 'cargo bootimage'?")
        sys.exit(1)
        
    logging.info(f"Preparing to flash {iso_path} to physically bound device {target_disk}...")
    
    if sys.platform == "linux" or sys.platform == "darwin":
        logging.warning("⚠️ WARNING: This will irreversibly overwrite the target block device.")
        confirm = input(f"Type 'CONFIRM' to flash {target_disk}: ")
        if confirm != "CONFIRM":
            logging.error("Aborted by user.")
            sys.exit(0)
            
        logging.info("Initiating block transfer...")
        result = subprocess.run(["sudo", "dd", f"if={iso_path}", f"of={target_disk}", "bs=4M", "status=progress"])
        
        if result.returncode == 0:
            logging.info("✅ Core successfully written to bare-metal medium. Syncing fs...")
            subprocess.run(["sync"])
            logging.info("You may now boot the physical node with secure-boot enabled.")
        else:
            logging.error("Failed to write to device.")
    else:
        logging.info(f"Target OS is Windows. The 'dd' utility is not natively available.")
        logging.info(f"Action: Please use Rufus or balenaEtcher to flash the generated kernel ISO:")
        logging.info(f"   => {os.path.abspath(iso_path)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flash Sovereign OS kernel to physical media.")
    parser.add_argument("--iso", default="backend/kernel/bare_metal/target/x86_64-sovereign/release/bootimage-sovereign_kernel.bin", help="Path to kernel bootimage.")
    parser.add_argument("--disk", required=True, help="Target raw block device (e.g., /dev/sdX or /dev/disk2).")
    
    args = parser.parse_args()
    flash_iso_to_usb(args.iso, args.disk)
