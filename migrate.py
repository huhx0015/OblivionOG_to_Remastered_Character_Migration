"""Project-root launcher for Oblivion OG to Remastered Character Migration."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oblivion_migrate.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
