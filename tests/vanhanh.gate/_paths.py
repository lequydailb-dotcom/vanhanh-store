"""Paths for the code-pack tests of vanhanh.gate, and server/ of VANHANH on sys.path.

The Gate plugin runs INSIDE a VANHANH server and calls its hub (`mcp_hub.tra_loi_jsonrpc(gate=...)`, Vanhanh
1.1.0), so its tests need a VANHANH checkout next to this repo. CI clones it; locally point VANHANH_OS_DIR at
yours (default: ../vanhanh next to this repo).

    VANHANH_OS_DIR=/path/to/vanhanh python tests/vanhanh.gate/test_gate.py
"""
import os
import sys
from pathlib import Path

STORE = Path(__file__).resolve().parents[2]
PACK = STORE / "packs" / "vanhanh.gate"
ROOT = Path(os.environ.get("VANHANH_OS_DIR") or (STORE.parent / "vanhanh")).resolve()
SERVER = ROOT / "server"
if not (SERVER / "chat_bridge.py").is_file():
    raise SystemExit(f"VANHANH 1.1.0+ checkout not found at {ROOT} (set VANHANH_OS_DIR)")
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
