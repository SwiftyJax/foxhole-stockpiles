"""Entry point when run as module."""

import asyncio
import sys

from .stockpile_scanner import main

if __name__ == "__main__":
    stockpile = asyncio.run(main())
    print(stockpile)
    sys.exit(0)
