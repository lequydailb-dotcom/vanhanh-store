"""Paths for the code-pack tests of vanhanh.zalo, and server/ of VANHANH on sys.path.

The plugins in this pack run INSIDE a VANHANH server and import its modules (`zalo_cli`, `image_gen`,
`image_vision`, `conversations`), so their tests need a VANHANH checkout next to this repo. CI clones it;
locally point VANHANH_OS_DIR at yours (default: ../vanhanh next to this repo).

    VANHANH_OS_DIR=/path/to/vanhanh python tests/vanhanh.zalo/test_zalo_read_images.py
"""
import os
import sys
from pathlib import Path

STORE = Path(__file__).resolve().parents[2]
PACK = STORE / "packs" / "vanhanh.zalo"
ROOT = Path(os.environ.get("VANHANH_OS_DIR") or (STORE.parent / "vanhanh")).resolve()
SERVER = ROOT / "server"
if not (SERVER / "zalo_cli.py").is_file():
    raise SystemExit(f"VANHANH checkout not found at {ROOT} (set VANHANH_OS_DIR)")
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
