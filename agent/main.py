from __future__ import annotations

import asyncio
import sys

from config import load_config


async def _main() -> None:
    config = load_config()
    
    site = "naukri"
    if len(sys.argv) > 1:
        site = sys.argv[1].lower()
    
    print(f"Initializing agent for site: {site}")
    
    if site == "naukri":
        from naukri_agent import NaukriPlaywrightAgent
        agent = NaukriPlaywrightAgent(config)
    # elif site == "indeed":
    #     from indeed_agent import IndeedPlaywrightAgent
    #     agent = IndeedPlaywrightAgent(config)
    else:
        print(f"Site '{site}' is currently disabled or not supported.")
        return
        
    await agent.run()


if __name__ == "__main__":
    asyncio.run(_main())
