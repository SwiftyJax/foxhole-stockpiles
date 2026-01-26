"""Entry point when run as module."""

import asyncio

from .catalog_builder import main

if __name__ == "__main__":
    asyncio.run(main())
