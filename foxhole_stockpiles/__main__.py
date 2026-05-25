"""Entry point for ``python -m foxhole_stockpiles`` (alias for the ``fs`` command)."""

from foxhole_stockpiles.cli.app import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
