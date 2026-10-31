"""Nạp một công cụ từ thư mục skill TRONG GÓI (tên thư mục có gạch nối nên không import thẳng được).

Chép từ `founder-skill/tests/_load.py`, chỉ đổi gốc sang `packs/naota.founder/skills`, để test chạy
trên đúng tệp người dùng tải về chứ không phải bản ở repo gốc.

    python tests/naota.founder/test_unit_economics.py   (KHÔNG mạng, KHÔNG cần NAOTA_OS_DIR)
"""

import importlib.util
import os

STORE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(STORE, "packs", "naota.founder", "skills")


def load(folder, name):
    path = os.path.join(SKILLS_DIR, folder, name + ".py")
    spec = importlib.util.spec_from_file_location("founder_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def example(folder, name):
    return os.path.join(SKILLS_DIR, folder, name)
