"""Configuration pytest : expose le harness TUI et les faux de ce dossier."""

import sys
from pathlib import Path

HERE = Path(__file__).parent
for path in (HERE, HERE.parent / "tui"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
