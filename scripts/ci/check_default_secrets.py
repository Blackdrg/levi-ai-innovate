from __future__ import annotations

import sys
from pathlib import Path


BLOCKED_PATTERNS = {
    "AUDIT_CHAIN_SECRET=change-me": "Replace AUDIT_CHAIN_SECRET before commit.",
    "AUDIT_CHAIN_SECRET=genesis_key": "Replace AUDIT_CHAIN_SECRET before commit.",
    "ENCRYPTION_KEY=kms_master_key": "Replace ENCRYPTION_KEY before commit.",
    "JWT_SECRET=sovereign_monolith_default_secret": "Replace JWT_SECRET before commit.",
    "INTERNAL_SERVICE_KEY=svc_internal_grad_777_absolute": "Replace INTERNAL_SERVICE_KEY before commit.",
}


def main(argv: list[str]) -> int:
    failing: list[str] = []
    for raw_path in argv[1:]:
        path = Path(raw_path)
        if not path.exists() or path.is_dir():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, message in BLOCKED_PATTERNS.items():
            if pattern in content:
                failing.append(f"{path}: {message}")
    if failing:
        print("\n".join(failing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
