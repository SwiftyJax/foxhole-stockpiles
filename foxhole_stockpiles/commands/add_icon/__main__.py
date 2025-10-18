"""Entry point when run as module."""

import asyncio

from .add_icon import main

if __name__ == "__main__":
    asyncio.run(main())
