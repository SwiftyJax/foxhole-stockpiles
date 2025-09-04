"""Entry point when run as module."""

import asyncio

from .stockpile_scanner import main

if __name__ == "__main__":
    asyncio.run(main())
