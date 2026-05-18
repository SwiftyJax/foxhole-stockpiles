"""Entry point for process_sav command."""

import asyncio

from foxhole_stockpiles.commands.process_sav.process_sav import main

if __name__ == "__main__":
    asyncio.run(main())
