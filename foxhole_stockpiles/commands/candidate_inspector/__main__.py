"""Entry point when run as module."""

import asyncio

from .candidate_inspector import main

if __name__ == "__main__":
    asyncio.run(main())
