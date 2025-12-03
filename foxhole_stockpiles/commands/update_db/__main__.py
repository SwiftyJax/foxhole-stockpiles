"""Entry point for update-db command when run as a module."""

import asyncio
import sys

from foxhole_stockpiles.commands.update_db import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
