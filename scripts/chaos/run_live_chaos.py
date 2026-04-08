from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import time
from typing import Any

import httpx


BASE_URL = os.getenv("LEVI_BASE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("LEVI_TEST_TOKEN", "sovereign_test_token_v14")
COMPOSE_FILE = os.getenv("LEVI_COMPOSE_FILE", "docker-compose.yml")


async def dispatch_mission(client: httpx.AsyncClient, prompt: str) -> dict[str, Any]:
    response = await client.post(
        f"{BASE_URL}/api/v1/orchestrator/mission",
        json={"input": prompt, "context": {"tier": "L2"}},
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )
    response.raise_for_status()
    return response.json()


async def get_health(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get(f"{BASE_URL}/health")
    response.raise_for_status()
    return response.json()


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, *args], check=True)


async def run_scenario(service: str, prompt: str, outage_seconds: int) -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        before = await get_health(client)
        mission = await dispatch_mission(client, prompt)
        print(json.dumps({"phase": "before", "health": before, "mission": mission}, indent=2))

        compose("stop", service)
        print(json.dumps({"phase": "outage", "service": service, "seconds": outage_seconds}))
        await asyncio.sleep(outage_seconds)

        during = await get_health(client)
        print(json.dumps({"phase": "during", "health": during}, indent=2))

        compose("start", service)
        await asyncio.sleep(5)
        after = await get_health(client)
        print(json.dumps({"phase": "after", "health": after}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local live chaos against Redis or Postgres.")
    parser.add_argument("--service", choices=["redis", "postgres"], required=True)
    parser.add_argument("--prompt", default="Run a resilient reasoning mission during infra chaos.")
    parser.add_argument("--outage-seconds", type=int, default=10)
    args = parser.parse_args()

    started = time.time()
    asyncio.run(run_scenario(args.service, args.prompt, args.outage_seconds))
    print(json.dumps({"status": "completed", "elapsed_s": round(time.time() - started, 2)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
