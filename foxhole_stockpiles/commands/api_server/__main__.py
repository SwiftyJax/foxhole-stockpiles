"""Entry point when run as module."""

import sys

from .api_server import main

if __name__ == "__main__":
    sys.exit(main())
