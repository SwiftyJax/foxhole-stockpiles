"""Entry point when run as module."""

import asyncio

from .uasset_extractor import main

if __name__ == "__main__":
    asyncio.run(main())
