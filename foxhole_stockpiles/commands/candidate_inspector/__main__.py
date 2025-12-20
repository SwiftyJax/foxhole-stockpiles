"""Entry point when run as module."""

import asyncio
import json
import sys

from .candidate_inspector import main

if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result) if result is not None else "")
    sys.exit(0)
