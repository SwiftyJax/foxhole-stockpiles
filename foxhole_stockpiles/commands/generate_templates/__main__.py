"""Entry point when run as module."""

import asyncio

from .generate_templates import main

if __name__ == "__main__":
    asyncio.run(main())
