"""Entry point when run as module."""

import asyncio

from .database_builder import main

if __name__ == "__main__":
    asyncio.run(main())
