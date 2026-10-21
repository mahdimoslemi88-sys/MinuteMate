"""Entry point used by PyInstaller to build minutemate-engine.exe."""

import sys

from minutemate.cli import main

if __name__ == "__main__":
    sys.exit(main())
