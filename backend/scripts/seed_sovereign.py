import asyncio
import logging
from backend.db.postgres import PostgresDB
from backend.db.models import UserProfile, CustomAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

async def seed_sovereign():
    """
    Initializes the Sovereign OS with standard system profiles 
    and the 'Sovereign' super-user.
    """
    logger.info("Initializing Sovereign OS Genesis Seed...")
    
    async with PostgresDB._session_factory() as session:
        async with session.begin():
            # 1. Create Sovereign System User
            sovereign_user = UserProfile(
                user_id="system_sovereign_000",
                tenant_id="sovereign_core",
                role="admin",
                persona_archetype="the_architect",
                response_style="precise"
            )
            await session.merge(sovereign_user)
            
            # 2. Seed Standard Agents
            agents = [
                CustomAgent(
                    agent_id="agent_researcher_v13",
                    user_id="system_sovereign_000",
                    name="The Researcher",
                    description="Deep-web and semantic retrieval specialist.",
                    config_json={
                        "tools": ["tavily_search", "vector_retrieve"],
                        "vibe": "academic"
                    }
                ),
                CustomAgent(
                    agent_id="agent_artisan_v13",
                    user_id="system_sovereign_000",
                    name="The Code Artisan",
                    description="High-fidelity software engineering and sandbox execution.",
                    config_json={
                        "tools": ["python_repl", "docker_sandbox"],
                        "vibe": "technical"
                    }
                )
            ]
            
            for agent in agents:
                await session.merge(agent)
                
        await session.commit()
    logger.info("Sovereign OS Genesis Seed complete. Ready for cognitive missions.")

if __name__ == "__main__":
    asyncio.run(seed_sovereign())
