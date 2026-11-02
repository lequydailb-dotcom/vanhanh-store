"""Paths for the code-pack tests of naota.gate, and server/ of NAOTA on sys.path.

The Gate plugin runs INSIDE a NAOTA server and calls its hub (`mcp_hub.tra_loi_jsonrpc(gate=...)`, Naota
1.1.0), so its tests need a NAOTA checkout next to this repo. CI clones it; locally point NAOTA_OS_DIR at
yours (default: ../naota next to this repo).

    NAOTA_OS_DIR=/path/to/naota python tests/naota.gate/test_gate.py
"""
import os
import sys
from pathlib import Path

STORE = Path(__file__).resolve().parents[2]
PACK = STORE / "packs" / "naota.gate"
ROOT = Path(os.environ.get("NAOTA_OS_DIR") or (STORE.parent / "naota")).resolve()
SERVER = ROOT / "server"
if not (SERVER / "chat_bridge.py").is_file():
    raise SystemExit(f"NAOTA 1.1.0+ checkout not found at {ROOT} (set NAOTA_OS_DIR)")
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
