"""AEGIS executable entry point for `python3 -m aegis`."""

import sys

from aegis.cli import main

if __name__ == "__main__":
    sys.exit(main())
