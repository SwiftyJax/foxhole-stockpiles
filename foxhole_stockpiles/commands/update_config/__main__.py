"""Entry point for running update-config as a module."""

import asyncio

from foxhole_stockpiles.commands.update_config.update_config import main

if __name__ == "__main__":
    asyncio.run(main())
