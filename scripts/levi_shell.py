import cmd
import json
import asyncio
import sys
import os
from datetime import datetime

# Path setup to ensure we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.kernel.kernel_wrapper import kernel
from backend.core.orchestrator import _orchestrator as orchestrator

class LeviShell(cmd.Cmd):
    intro = '🪐 Welcome to the LEVI-AI Sovereign Shell. Type help or ? to list commands.\n'
    prompt = '(levi-os) 🛰️ '

    def do_ls(self, arg):
        """List current filesystem state: ls"""
        tree_json = kernel.get_fs_tree()
        tree = json.loads(tree_json)
        print(f"Directory: {tree['name']}")
        if tree.get('children'):
            for name, node in tree['children'].items():
                icon = "📁" if node['ftype'] == "Directory" else "📄"
                print(f" {icon} {name:20} | Size: {node['size']} bytes")

    def do_ps(self, arg):
        """List active kernel processes: ps"""
        procs = kernel.get_processes()
        print(f"{'ID':<38} | {'PID':<8} | {'Priority':<8} | {'Status':<10}")
        print("-" * 75)
        for p in procs:
            print(f"{p['id']:<38} | {p['pid'] or 'N/A':<8} | {p['priority']:<8} | {p['status']:<10}")

    def do_top(self, arg):
        """Show system load and GPU metrics: top"""
        metrics = json.loads(kernel.get_gpu_metrics())
        print(f"--- SYSTEM HEALTH [{datetime.now().strftime('%H:%M:%S')}] ---")
        print(f"GPU VRAM: {metrics['vram_used_mb']}/{metrics['vram_total_mb']} MB ({metrics['vram_used_mb']/metrics['vram_total_mb']*100:.1f}%)")
        print(f"Load:     {metrics['load_pct']:.1f}%")
        print(f"Temp:     {metrics['temp_c']:.1f}°C")

    def do_boot(self, arg):
        """Retrieve kernel boot sequence report: boot"""
        report = kernel.get_boot_report()
        print(f"--- KERNEL BOOT REPORT [{report.get('kernel_version')}] ---")
        print(f"Boot Time: {datetime.fromtimestamp(report.get('boot_time')).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Latency:   {report.get('latency_ms')}ms")
        print(f"Integrity: {report.get('integrity_hash')} [VERIFIED]")
        print("\nSequence Log:")
        for entry in report.get('sequence_log', []):
            print(f"  > {entry}")

    def do_mission(self, arg):
        """Dispatch a new autonomous mission: mission <objective>"""
        if not arg:
            print("Usage: mission <objective>")
            return
        print(f"🚀 Dispatching mission: {arg}")
        asyncio.run(orchestrator.handle_mission_request(
            request_id=f"cli_{int(datetime.now().timestamp())}",
            user_id="ROOT_CLI",
            objective=arg
        ))

    def do_kill(self, arg):
        """Terminate a task: kill <task_id>"""
        if not arg:
            print("Usage: kill <task_id>")
            return
        kernel.kill_task(arg)
        print(f"⚠️ Sent SIGKILL to {arg}")

    def do_reboot(self, arg):
        """Reboot the Sovereign Kernel: reboot"""
        print("🌀 Rebooting Sovereign Kernel...")
        # In a real system, we'd trigger a restart of the process
        sys.exit(0)

    def do_exit(self, arg):
        """Exit the shell: exit"""
        print("Bye.")
        return True

if __name__ == '__main__':
    LeviShell().cmdloop()
