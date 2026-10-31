"""Plugin zalo-image: gửi ảnh/file qua Zalo bằng phiên đã quét QR.

    NAOTA_OS_DIR=../naota python tests/naota.zalo/test_zalo_image.py

Không mạng, không gọi npx thật: thay hàm chạy tiến trình con bằng bản ghi lại argv, rồi soi
lệnh dựng ra có ĐÚNG không. Những gì file này canh:

1. RÀO ĐƯỜNG DẪN. Tool nhận đường dẫn từ chính câu chat, và đầu ra là GỬI RA NGOÀI, không thu
   hồi được. Không có rào "phải nằm trong brain" thì một câu khéo léo là tuồn được file khoá
   hay /etc/passwd ra một cuộc chat Zalo bất kỳ. Đây là thứ quan trọng nhất ở đây.
2. NHIỀU TÀI KHOẢN THÌ HỎI LẠI, KHÔNG ĐOÁN. Đoán sai nghĩa là tin nhắn đi dưới danh tính
   người khác.
3. DÙNG ĐÚNG HOME CỦA KẾT NỐI. Sai home là CLI không thấy phiên đăng nhập và tự bật QR mới -
   treo tiến trình con cho tới lúc hết giờ.
"""
from _paths import PACK, ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path
import asyncio
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


spec = importlib.util.spec_from_file_location(
    "zalo_image_plugin", PACK / "plugins" / "zalo-image" / "plugin.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class Ctx:
    def __init__(self, root):
        self.vault_root = str(root)


VAULT = Path(tempfile.mkdtemp(prefix="naota-zaloimg-")) / "brain"
(VAULT / "attachments").mkdir(parents=True)
(VAULT / "attachments" / "anh.jpg").write_bytes(b"fake")
(VAULT / "attachments" / "anh2.png").write_bytes(b"fake")
(VAULT / "bao-cao.pdf").write_bytes(b"fake")
NGOAI = VAULT.parent / "bi-mat.txt"
NGOAI.write_text("token", encoding="utf-8")

CTX = Ctx(VAULT)
_da_chay = []


def gia_lap(conns, rc=0, out='{"ok":true}', err=""):
    """Thay hai chỗ chạm thế giới thật: danh sách kết nối, và tiến trình con."""
    P._ket_noi_zalo = lambda: list(conns)
    P.shutil.which = lambda name: "/usr/bin/npx" if name == "npx" else None

    async def _chay(argv, home):
        _da_chay.append({"argv": argv, "home": home})
        return rc, out, err
    P._chay = _chay


MOT = [{"id": "c1", "label": "Zalo chính", "home": "/state/connector-home/zalo-a"}]
HAI = MOT + [{"id": "c2", "label": "Zalo phụ", "home": "/state/connector-home/zalo-b"}]


def goi(args):
    _da_chay.clear()
    return asyncio.run(P._send(args, CTX))


# ============================================================
# 1. Rào đường dẫn - phần quan trọng nhất
# ============================================================
gia_lap(MOT)
r = goi({"thread_id": "t1", "paths": ["../bi-mat.txt"]})
check("CANARY: đường dẫn trèo ra khỏi brain bị chặn", r.startswith("ERROR") and "NGOÀI brain" in r)
check("bị chặn thì KHÔNG chạy lệnh nào cả", not _da_chay)

r = goi({"thread_id": "t1", "paths": [str(NGOAI)]})
check("CANARY: đường dẫn TUYỆT ĐỐI ngoài brain cũng bị chặn", r.startswith("ERROR"))
check("đường dẫn tuyệt đối ngoài brain cũng không chạy lệnh", not _da_chay)

r = goi({"thread_id": "t1", "paths": ["attachments/khong-co.jpg"]})
check("file không tồn tại thì báo NGAY, không đẩy sang CLI",
      r.startswith("ERROR") and "không thấy file" in r and not _da_chay)

r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"] * 11})
check("chặn gửi quá nhiều file một lượt", r.startswith("ERROR") and not _da_chay)

# ============================================================
# 2. Tham số thiếu
# ============================================================
check("thiếu thread_id thì nói rõ cách tìm",
      "zalo_search_threads" in goi({"paths": ["attachments/anh.jpg"]}))
check("thiếu paths thì báo lỗi", goi({"thread_id": "t1"}).startswith("ERROR"))

# ============================================================
# 3. Dựng lệnh đúng
# ============================================================
r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg", "attachments/anh2.png"],
         "caption": "ảnh sản phẩm", "thread_type": 1})
d = json.loads(r)
argv = _da_chay[0]["argv"]
check("gửi thành công trả JSON đọc được", d.get("ok") and d["sent"] == 2 and d["kind"] == "image")
# Hỏi lõi bản nào đang ghim thay vì chép chuỗi: lõi đổi bản CLI thì test vẫn đúng.
check("chạy đúng package đã ghim", P.zalo_cli.CLI_PACKAGE in argv)
check("dùng lệnh con send-image cho ảnh", "send-image" in argv and "msg" in argv)
# --json phải đứng TRƯỚC lệnh con: nó là cờ toàn cục của program (commander), đặt sau
# "msg send-image" là commander coi như tham số lạ của lệnh con.
check("cờ --json đứng trước lệnh con", argv.index("--json") < argv.index("msg"))
check("truyền đúng threadId", "t1" in argv)
check("đường dẫn đưa sang CLI là TUYỆT ĐỐI (CLI resolve theo cwd của nó, không phải của Naota)",
      all(Path(a).is_absolute() for a in argv if a.endswith((".jpg", ".png"))))
check("truyền loại hội thoại (nhóm = 1)", argv[argv.index("-t") + 1] == "1")
check("truyền lời nhắn kèm", argv[argv.index("-m") + 1] == "ảnh sản phẩm")
check("CANARY: chạy trong HOME của đúng kết nối Zalo (nếu không CLI đòi quét QR lại)",
      _da_chay[0]["home"] == MOT[0]["home"])

# ============================================================
# 3b. FILE đi qua MCP (zalo_cli.send_files), KHÔNG qua CLI send-file
# ============================================================
# `msg send-file` treo tới 120 giây với một file Excel 11 KB, vì Zalo chỉ xác nhận file qua kết nối thời
# gian thực mà lệnh CLI chạy một lần không mở. Nên file đi qua tool MCP của lõi.
(VAULT / "danh-sach.xlsx").write_bytes(b"PK")
(VAULT / "attachments" / "so-do.bmp").write_bytes(b"BM")
_gui = []
_tra = {"v": (True, {"success": True}, "")}


async def send_files_gia(conn_id, home, thread_id, files, thread_type=0, caption=""):
    _gui.append({"conn_id": conn_id, "home": home, "thread_id": thread_id, "files": list(files),
                 "thread_type": thread_type, "caption": caption})
    return _tra["v"]


co_san = getattr(P.zalo_cli, "send_files", None)
P.zalo_cli.send_files = send_files_gia
r = goi({"thread_id": "t1", "paths": ["danh-sach.xlsx"], "caption": "Gửi chị danh sách", "thread_type": 0})
check("CANARY: file Excel KHÔNG chạy lệnh CLI nào (đường đó treo)", not _da_chay)
check("file Excel đi qua send_files của lõi, đúng tài khoản, HOME, cuộc chat, lời nhắn",
      len(_gui) == 1 and _gui[0]["conn_id"] == "c1" and _gui[0]["home"] == MOT[0]["home"]
      and _gui[0]["thread_id"] == "t1" and _gui[0]["caption"] == "Gửi chị danh sách"
      and _gui[0]["files"] == [(VAULT / "danh-sach.xlsx").resolve()])
check("thành công trả JSON kind=file", json.loads(r)["kind"] == "file" and json.loads(r)["files"] == ["danh-sach.xlsx"])

_gui.clear()
r = goi({"thread_id": "t1", "paths": ["bao-cao.pdf"]})
check("PDF cũng đi đường MCP", len(_gui) == 1 and not _da_chay and json.loads(r)["kind"] == "file")
_gui.clear()
r = goi({"thread_id": "t1", "paths": ["attachments/so-do.bmp"]})
check("CANARY: ảnh .bmp cũng là FILE với zca-js nên đi đường MCP (đi CLI là treo)", len(_gui) == 1 and not _da_chay)

_tra["v"] = (False, None, "Zalo did not confirm the upload of danh-sach.xlsx within 60s. Nothing was sent.")
r = goi({"thread_id": "t1", "paths": ["danh-sach.xlsx"]})
check("Zalo không xác nhận thì ERROR kèm nguyên nhân, không báo đã gửi", r.startswith("ERROR") and "Nothing was sent" in r)
_tra["v"] = (False, None, "quá 120 " + P.zalo_cli.TIMEOUT_MARK)
r = goi({"thread_id": "t1", "paths": ["danh-sach.xlsx"]})
check("lời gọi MCP quá giờ thì nhắc kiểm cuộc chat trước khi gửi lại (file có thể đã tới)",
      r.startswith("ERROR") and "kiểm tra cuộc chat" in r)

del P.zalo_cli.send_files
_gui.clear()
r = goi({"thread_id": "t1", "paths": ["danh-sach.xlsx"]})
check("CANARY: Naota cũ chưa có send_files thì báo cập nhật NGAY, không chạy CLI (không treo 120 giây)",
      r.startswith("ERROR") and "1.0.0" in r and not _da_chay and not _gui)
if co_san is not None:
    P.zalo_cli.send_files = co_san

r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg", "bao-cao.pdf"]})
check("trộn ảnh với file thì từ chối chứ không tự đoán", r.startswith("ERROR") and not _da_chay)

r = goi({"thread_id": "t1", "paths": "attachments/anh.jpg"})
check("paths đưa vào một chuỗi cũng nhận (model hay truyền vậy)", json.loads(r)["sent"] == 1)

r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"], "thread_type": 7})
check("thread_type lạ thì kẹp về 0 (cá nhân), không truyền số bậy sang CLI",
      _da_chay[0]["argv"][_da_chay[0]["argv"].index("-t") + 1] == "0")

# ============================================================
# 4. Nhiều tài khoản: hỏi lại, không đoán
# ============================================================
gia_lap(HAI)
r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"]})
check("CANARY: hai tài khoản mà không nêu rõ thì TỪ CHỐI, không gửi bừa",
      r.startswith("ERROR") and not _da_chay)
check("và liệt kê ra để chọn", "Zalo chính" in r and "Zalo phụ" in r)
r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"], "connection_id": "c2"})
check("nêu rõ connection_id thì gửi bằng đúng tài khoản đó",
      json.loads(r)["account"] == "Zalo phụ" and _da_chay[0]["home"] == HAI[1]["home"])
check("connection_id lạ thì báo lỗi",
      goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"], "connection_id": "xxx"}).startswith("ERROR"))

# ============================================================
# 5. Chưa đủ điều kiện thì nói rõ phải làm gì
# ============================================================
gia_lap([])
r = goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"]})
check("chưa đấu Zalo thì chỉ đúng chỗ cần bấm", "trang Kết nối" in r)

gia_lap(MOT)
P.shutil.which = lambda name: None
check("máy chưa có Node thì nói rõ", "nodejs.org" in goi({"thread_id": "t1", "paths": ["attachments/anh.jpg"]}))

# ============================================================
# 6. Lỗi từ CLI phải nổi lên, không nuốt
# ============================================================
gia_lap(MOT, rc=1, out="", err="Thread not found")
r = goi({"thread_id": "sai", "paths": ["attachments/anh.jpg"]})
check("CLI lỗi thì trả ERROR kèm nguyên nhân", r.startswith("ERROR") and "Thread not found" in r)

# ============================================================
# 7. Khai báo plugin: PHẢI ở mức full (gửi ra ngoài, không rút lại được)
# ============================================================
import fastyaml  # noqa: E402

y = fastyaml.safe_load((PACK / "plugins" / "zalo-image" / "plugin.yaml").read_text(encoding="utf-8"))
check("plugin khai min_mode full", y.get("min_mode") == "full")
check("plugin khai đúng tool", y.get("tools") == ["zalo_send_image"])


class ThuCtx:
    def __init__(self):
        self.tools = []

    def register_tool(self, **kw):
        self.tools.append(kw)


tc = ThuCtx()
P.register(tc)
check("register 1 tool", len(tc.tools) == 1 and tc.tools[0]["name"] == "zalo_send_image")
check("CANARY: tool đăng ký ở mức full, chế độ suggest không tự gửi tin được",
      tc.tools[0]["min_mode"] == "full")
check("có check_fn để báo thiếu điều kiện trước khi gọi", callable(tc.tools[0]["check_fn"]))

if fails:
    print("\nFAIL - test_zalo_image: " + str(len(fails)) + " lỗi: " + ", ".join(fails))
    sys.exit(1)
print("\nOK - test_zalo_image: tất cả pass")
