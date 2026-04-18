#!/usr/bin/env python3
"""
LEVI-AI Integration Smoke Test
Run: python -m backend.tests.integration_smoke
Passes if all import chains resolve without exception.
"""
import sys
import traceback

PASS = []
FAIL = []

def check(label, fn):
    try:
        fn()
        PASS.append(label)
        print(f"  ✅  {label}")
    except Exception as e:
        FAIL.append(label)
        print(f"  ❌  {label}: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()

print("=" * 60)
print("  LEVI-AI Sovereign OS v22.0.0 — Integration Smoke Test")
print("=" * 60)

# ── Kernel wrapper ────────────────────────────────────────────────
print("\n[1] Kernel wrapper")
check("kernel import",                lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]))
check("kernel.get_gpu_metrics()",     lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]).kernel.get_gpu_metrics())
check("kernel.get_boot_report()",     lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]).kernel.get_boot_report())
check("kernel.flush_vram_buffer()",   lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]).kernel.flush_vram_buffer())
check("kernel.get_signing_key()",     lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]).kernel.get_signing_key())
check("kernel.get_drivers()",         lambda: __import__("backend.kernel.kernel_wrapper", fromlist=["kernel"]).kernel.get_drivers())

# ── Orchestrator ──────────────────────────────────────────────────
print("\n[2] Orchestrator")
check("orchestrator import",          lambda: __import__("backend.core.orchestrator", fromlist=["orchestrator"]))
check("_orchestrator alias",          lambda: getattr(__import__("backend.core.orchestrator", fromlist=["_orchestrator"]), "_orchestrator"))

# ── Brain ─────────────────────────────────────────────────────────
print("\n[3] Brain")
check("LeviBrain import",             lambda: __import__("backend.core.brain", fromlist=["LeviBrain"]))

# ── Memory manager shim ───────────────────────────────────────────
print("\n[4] Services")
check("services.memory_manager shim", lambda: __import__("backend.services.memory_manager", fromlist=["MemoryManager"]))

# ── Agent registry ────────────────────────────────────────────────
print("\n[5] Agents")
check("forensic agent import",        lambda: __import__("backend.agents.forensic", fromlist=["ForensicAgent"]))

# ── Summary ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = len(PASS) + len(FAIL)
print(f"  Result: {len(PASS)}/{total} passed")
if FAIL:
    print(f"  Failed: {', '.join(FAIL)}")
    sys.exit(1)
else:
    print("  ALL CHECKS PASSED ✅")
    sys.exit(0)
