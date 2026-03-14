"""Entry point when run as module."""

import asyncio
import json
import sys

from .stockpile_scanner import main

if __name__ == "__main__":
    stockpile = asyncio.run(main())
    if stockpile is not None:
        print(json.dumps(stockpile, indent=2))
    sys.exit(0)
