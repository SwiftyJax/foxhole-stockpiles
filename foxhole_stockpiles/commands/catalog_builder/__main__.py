"""Entry point when run as module."""

from .catalog_builder import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
