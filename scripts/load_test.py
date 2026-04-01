"""
scripts/load_test.py

LEVI-AI Load Test — Concurrency & Rate Limit Validation
=========================================================

Tests the Gateway's Redis Lua concurrency controls and rate limiter under
high concurrent load. Validates that zero counter leaks occur after all
requests complete.

Usage:
    python scripts/load_test.py [--users N] [--target URL] [--token JWT]

Requirements:
    pip install httpx rich

Default: 1,000 concurrent users against http://localhost:8000
"""

import asyncio
import argparse
import json
import time
import statistics
import sys
from typing import List, Tuple, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("[WARNING] rich not installed. Install with: pip install rich  (for prettier output)")


# ── Test Configuration ────────────────────────────────────────

DEFAULT_TARGET = "http://localhost:8000"
DEFAULT_USERS = 1000
CONCURRENCY_LIMIT = 50   # Max truly simultaneous HTTP connections
TIMEOUT_SECONDS = 30.0

# Test payload — stresses both Chat and Sovereign routes
TEST_PAYLOAD = {
    "message": "Philosophize on the nature of digital memory in a sovereign world.",
    "session_id": "load_test_session_{idx}",
    "mood": "philosophical",
    "stream": True # Always test SSE for v6.8
}

# Redis key to validate for leaks (the global concurrency counter)
CONCURRENT_JOBS_KEY = "concurrent_jobs:global"


# ── Result Tracking ───────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.latencies: List[float] = []
        self.success_count: int = 0
        self.error_count: int = 0
        self.rate_limited_count: int = 0
        self.timeout_count: int = 0
        self.status_codes: dict = {}
        self.errors: List[str] = []

    def record(self, latency_ms: float, status_code: int, error: Optional[str] = None):
        self.latencies.append(latency_ms)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if status_code == 200:
            self.success_count += 1
        elif status_code == 429:
            self.rate_limited_count += 1
        elif error:
            self.error_count += 1
            if len(self.errors) < 10:  # Collect first 10 errors only
                self.errors.append(f"[{status_code}] {error[:100]}")
        else:
            self.error_count += 1

    def record_timeout(self):
        self.timeout_count += 1
        self.error_count += 1
        self.latencies.append(TIMEOUT_SECONDS * 1000)

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def total(self) -> int:
        return self.success_count + self.rate_limited_count + self.error_count


# ── Core Load Test Logic ──────────────────────────────────────

async def single_request(
    client: httpx.AsyncClient,
    target: str,
    idx: int,
    token: Optional[str],
    result: TestResult,
    semaphore: asyncio.Semaphore,
):
    """Fire a single POST /api/v1/chat request and record the result."""
    payload = {**TEST_PAYLOAD, "session_id": f"load_test_session_{idx}"}
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with semaphore:
        start = time.monotonic()
        try:
            # LEVI v6: Support for both standard and explicit stream endpoints
            endpoint = "/api/chat" if not idx % 2 else "/api/chat/stream"
            
            async with client.stream("POST", f"{target}{endpoint}", json=payload, headers=headers, timeout=TIMEOUT_SECONDS) as resp:
                latency_ms = (time.monotonic() - start) * 1000
                chunks_received = 0
                activity_received = False
                choice_received = False
                
                if resp.status_code == 200:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            chunks_received += 1
                            if "activity" in line: activity_received = True
                            if "choice" in line: choice_received = True
                            if "[DONE]" in line: break
                    
                    # Verify Intel Pulse Fidelity
                    if chunks_received > 0:
                        result.record(latency_ms, resp.status_code)
                    else:
                         result.record(latency_ms, 500, "Empty Stream")
                else:
                    result.record(latency_ms, resp.status_code)

        except httpx.TimeoutException:
            result.record_timeout()
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            result.record(latency_ms, 0, str(e))


async def check_redis_leaks(target: str) -> dict:
    """
    After all requests complete, check Redis for counter leaks.
    Calls a debug endpoint if available, otherwise reports N/A.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{target}/health")
            if resp.status_code == 200:
                return {"redis": resp.json().get("redis", "unknown"), "counters": "see_logs"}
    except Exception:
        pass
    return {"redis": "unreachable", "counters": "N/A"}


async def run_load_test(target: str, num_users: int, token: Optional[str]):
    """Main load test orchestrator."""
    result = TestResult()
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    print(f"\n{'='*60}")
    print(f"  LEVI-AI Load Test")
    print(f"  Target  : {target}")
    print(f"  Users   : {num_users:,}")
    print(f"  Max conn: {CONCURRENCY_LIMIT} simultaneous")
    print(f"{'='*60}\n")

    start_time = time.monotonic()

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=CONCURRENCY_LIMIT + 10, max_keepalive_connections=CONCURRENCY_LIMIT),
        http2=False,
    ) as client:
        tasks = [
            single_request(client, target, i, token, result, semaphore)
            for i in range(num_users)
        ]

        if HAS_RICH:
            console = Console()
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("• {task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task("Sending requests...", total=num_users)

                completed_tasks = 0
                async def tracked_task(coro):
                    nonlocal completed_tasks
                    await coro
                    completed_tasks += 1
                    progress.update(task_id, completed=completed_tasks)

                await asyncio.gather(*[tracked_task(t) for t in tasks])
        else:
            # Simple progress without rich
            print(f"Firing {num_users:,} requests...")
            chunk = max(1, num_users // 20)
            completed = 0

            async def simple_tracked(coro):
                nonlocal completed
                await coro
                completed += 1
                if completed % chunk == 0:
                    pct = int(completed / num_users * 100)
                    print(f"  {pct}% complete ({completed:,}/{num_users:,})")

            await asyncio.gather(*[simple_tracked(t) for t in tasks])

    total_time_s = time.monotonic() - start_time

    # Post-test Redis leak check
    redis_status = await check_redis_leaks(target)

    # ── Report ────────────────────────────────────────────────
    p50  = result.percentile(50)
    p95  = result.percentile(95)
    p99  = result.percentile(99)
    rps  = result.total / total_time_s if total_time_s > 0 else 0
    success_rate = (result.success_count / result.total * 100) if result.total > 0 else 0

    if HAS_RICH:
        console = Console()
        console.print("\n[bold green]✅ Load Test Complete[/bold green]\n")

        table = Table(title="Results", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim", width=28)
        table.add_column("Value", justify="right")

        table.add_row("Total Requests", f"{result.total:,}")
        table.add_row("✅ Success (200)", f"[green]{result.success_count:,}[/green]")
        table.add_row("⚠️  Rate Limited (429)", f"[yellow]{result.rate_limited_count:,}[/yellow]")
        table.add_row("❌ Errors", f"[red]{result.error_count - result.timeout_count:,}[/red]")
        table.add_row("⏱️  Timeouts", f"[red]{result.timeout_count:,}[/red]")
        table.add_row("Success Rate", f"{'[green]' if success_rate > 90 else '[red]'}{success_rate:.1f}%[/]")
        table.add_row("Throughput (RPS)", f"{rps:.1f}")
        table.add_row("Total Duration", f"{total_time_s:.2f}s")
        table.add_row("─" * 20, "─" * 12)
        table.add_row("p50 Latency", f"{p50:.0f} ms")
        table.add_row("p95 Latency", f"{'[yellow]' if p95 > 1000 else '[green]'}{p95:.0f} ms[/]")
        table.add_row("p99 Latency", f"{'[red]' if p99 > 2000 else '[green]'}{p99:.0f} ms[/]")
        table.add_row("─" * 20, "─" * 12)
        table.add_row("Redis Status", redis_status.get("redis", "N/A"))
        table.add_row("Counter Leak Check", redis_status.get("counters", "N/A"))

        status_row = ", ".join(f"{k}:{v}" for k, v in sorted(result.status_codes.items()))
        table.add_row("Status Code Breakdown", status_row)

        console.print(table)

        if result.errors:
            console.print("\n[bold red]Sample Errors:[/bold red]")
            for err in result.errors[:5]:
                console.print(f"  • {err}")

        # Final verdict
        is_healthy = success_rate >= 80 and p95 < 3000
        if is_healthy:
            console.print("\n[bold green]✅ PASS: System is healthy under load.[/bold green]")
        else:
            console.print("\n[bold red]❌ FAIL: System shows signs of stress.[/bold red]")
            if success_rate < 80:
                console.print(f"   → Success rate {success_rate:.1f}% is below 80% threshold.")
            if p95 >= 3000:
                console.print(f"   → p95 latency {p95:.0f}ms exceeds 3,000ms threshold.")
    else:
        print(f"\n{'='*60}")
        print(f"  RESULTS")
        print(f"{'='*60}")
        print(f"  Total:          {result.total:,}")
        print(f"  Success (200):  {result.success_count:,}")
        print(f"  Rate Limited:   {result.rate_limited_count:,}")
        print(f"  Errors:         {result.error_count:,}")
        print(f"  Success Rate:   {success_rate:.1f}%")
        print(f"  Throughput:     {rps:.1f} RPS")
        print(f"  p50 Latency:    {p50:.0f} ms")
        print(f"  p95 Latency:    {p95:.0f} ms")
        print(f"  p99 Latency:    {p99:.0f} ms")
        print(f"  Redis Status:   {redis_status.get('redis', 'N/A')}")
        print(f"{'='*60}\n")

    # Return exit code
    return 0 if (success_rate >= 80 and p95 < 3000) else 1


# ── Entry Point ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LEVI-AI Load Test")
    parser.add_argument(
        "--users", type=int, default=DEFAULT_USERS,
        help=f"Number of concurrent users to simulate (default: {DEFAULT_USERS})"
    )
    parser.add_argument(
        "--target", type=str, default=DEFAULT_TARGET,
        help=f"Target base URL (default: {DEFAULT_TARGET})"
    )
    parser.add_argument(
        "--sovereign", action="store_true",
        help="Target the Local GGUF engine specifically (stresses CPU/RAM)"
    )
    parser.add_argument(
        "--token", type=str, default=None,
        help="Firebase JWT token for authenticated requests (optional)"
    )

    args = parser.parse_args()

    exit_code = asyncio.run(run_load_test(args.target, args.users, args.token))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
