"""Paths for the code-pack tests of naota.zalo, and server/ of NAOTA on sys.path.

The plugins in this pack run INSIDE a NAOTA server and import its modules (`zalo_cli`, `image_gen`,
`image_vision`, `conversations`), so their tests need a NAOTA checkout next to this repo. CI clones it;
locally point NAOTA_OS_DIR at yours (default: ../naota next to this repo).

    NAOTA_OS_DIR=/path/to/naota python tests/naota.zalo/test_zalo_read_images.py
"""
import os
import sys
from pathlib import Path

STORE = Path(__file__).resolve().parents[2]
PACK = STORE / "packs" / "naota.zalo"
ROOT = Path(os.environ.get("NAOTA_OS_DIR") or (STORE.parent / "naota")).resolve()
SERVER = ROOT / "server"
if not (SERVER / "zalo_cli.py").is_file():
    raise SystemExit(f"NAOTA checkout not found at {ROOT} (set NAOTA_OS_DIR)")
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
