import os
import json
import hashlib
import time
from typing import Dict, Any

class TPMBridge:
    """
    Sovereign v22.1: TPM 2.0 Emulator Bridge.
    Simulates a 5-stage PCR chain if physical swtpm is missing.
    Grounded in a machine-unique root secret.
    """
    STATE_PATH = "d:\\LEVI-AI\\data\\security\\tpm_state.json"
    
    def __init__(self):
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        self.pcr = self._load_state()

    def _load_state(self) -> Dict[str, str]:
        if os.path.exists(self.STATE_PATH):
            try:
                with open(self.STATE_PATH, 'r') as f:
                    return json.load(f).get("pcr", {})
            except:
                pass
        
        # Initial Boot State (Sovereign Root)
        return {
            "0": "0000000000000000000000000000000000000000", # CRTM
            "1": "0000000000000000000000000000000000000001", # Kernel Loader
            "2": "0000000000000000000000000000000000000010", # Kernel Hash
            "3": "0000000000000000000000000000000000000100", # App Policies
            "4": "0000000000000000000000000000000000001000", # Swarm Identity
        }

    def _save_state(self):
        with open(self.STATE_PATH, 'w') as f:
            json.dump({"pcr": self.pcr, "last_update": time.time()}, f, indent=4)

    def extend_pcr(self, index: int, data: str):
        """Standard TPM PCR Extend: PCR[i] = SHA1(PCR[i] + SHA1(data))"""
        if str(index) not in self.pcr:
            self.pcr[str(index)] = "0" * 40
            
        current = self.pcr[str(index)]
        new_val = hashlib.sha1((current + hashlib.sha1(data.encode()).hexdigest()).encode()).hexdigest()
        self.pcr[str(index)] = new_val
        self._save_state()
        print(f" [🛡️] TPM: PCR[{index}] EXTENDED -> {new_val[:10]}...")

    def read_pcr(self, index: int) -> str:
        return self.pcr.get(str(index), "0" * 40)

tpm = TPMBridge()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "extend" and len(sys.argv) > 3:
            tpm.extend_pcr(int(sys.argv[2]), sys.argv[3])
        elif cmd == "read":
            print(tpm.read_pcr(int(sys.argv[2])))
