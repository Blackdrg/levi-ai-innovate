async function createMission(input) {
  const res = await fetch(API_URL + "/api/v1/orchestrator/mission", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ input })
  });
  return res.json();
}

async function fetchMissions() {
    const res = await fetch(API_URL + "/api/v1/missions");
    return res.json();
}
