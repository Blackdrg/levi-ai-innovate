# examples/community_agent.py
import asyncio
from sdk.python.levi_sdk import LeviClient, BaseAgent

class CommunityModeratorAgent(BaseAgent):
    """An example of a 3rd party agent built on LEVI."""
    async def moderate(self, community_post: str):
        print(f" 🛡️ [CommunityAgent] Analyzing post for sovereign compliance...")
        result = await self.run(f"Audit this content for compliance: {community_post}")
        print(f" ✅ [CommunityAgent] Audit Complete. Result: {result['status']}")

async def main():
    client = LeviClient()
    agent = CommunityModeratorAgent(client)
    
    await agent.moderate("This is a test post for the Sovereign ecosystem.")

if __name__ == "__main__":
    asyncio.run(main())
