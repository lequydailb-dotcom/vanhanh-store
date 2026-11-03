"""Plugin zalo-friend: công cụ kết bạn Zalo (tìm người, trạng thái, gửi, nhận, từ chối lời mời).

    VANHANH_OS_DIR=../vanhanh python tests/vanhanh.zalo/test_zalo_friend.py   (KHÔNG mạng: thay chỗ chạy CLI bằng bản ghi lại lệnh)

Vanhanh cần CÓ KHẢ NĂNG kết bạn, còn kết bạn với ai do model quyết định hoặc người dùng yêu cầu, không dựng
tính năng cứng. Nên test canh đúng ba thứ:
  1. Mỗi tool gọi ĐÚNG lệnh CLI với ĐÚNG tham số, và id sai khuôn bị chặn trước khi chạm Zalo.
  2. Thành công/thất bại đọc đúng: CLI thoát mã 0 cả khi Zalo từ chối ("✗"), và có thể in "undefined" thay JSON khi đã làm xong ("✓").
  3. Phân quyền theo mức chung: tool đọc là readonly, tool hành động là full. Không có luồng tự động nào.
  4. (gói 1.3.0) Tìm theo tên trong bạn bè, lời mời chờ duyệt / đã gửi, rút lại lời mời, tra nhiều số: đọc đúng khuôn zca-js,
     có trần số người và số điện thoại, "chưa gửi lời mời nào" (mã 112) là danh sách rỗng chứ không phải lỗi.
"""
from _paths import PACK, ROOT, SERVER  # noqa: E402,F401
import asyncio
import importlib.util
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import zalo_cli  # noqa: E402

fails = []


def check(name, cond, them=""):
    print(("ok   " if cond else "FAIL ") + name + (("  [" + str(them) + "]") if them and not cond else ""))
    if not cond:
        fails.append(name)


spec = importlib.util.spec_from_file_location("zalo_friend_plugin", PACK / "plugins" / "zalo-friend" / "plugin.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

MOT = [{"id": "c1", "label": "Zalo chính", "home": "/state/zalo-a"}]
RAN = []
REPLY = {"rc": 0, "out": "{}", "err": ""}


def fake_world(rc=0, out="{}", err=""):
    zalo_cli.AUTO_INSTALL = False
    zalo_cli.connections = lambda: list(MOT)
    zalo_cli.check = lambda: None
    zalo_cli.shutil = type("S", (), {"which": staticmethod(lambda n: "/usr/bin/npx" if n == "npx" else None)})
    zalo_cli.os = type("O", (), {"name": "posix", "environ": {}, "path": __import__("os").path})
    REPLY.update(rc=rc, out=out, err=err)

    async def run(argv, home, timeout=120):
        RAN.append({"argv": argv, "home": home})
        return REPLY["rc"], REPLY["out"], REPLY["err"]
    zalo_cli.run = run


def call(fn, args):
    RAN.clear()
    return asyncio.run(fn(args, None))


def cli_args():
    a = RAN[-1]["argv"]
    return a[a.index("--json") + 1:]


# ============================================================
# 1. Tìm người
# ============================================================
fake_world(out=json.dumps({"uid": "8812345", "display_name": "Lan Anh", "avatar": "https://a/b.jpg"}))
r = json.loads(call(P._find_user, {"query": "0912 345 678"}))
check("tìm theo số điện thoại: gọi friend find với số đã bỏ dấu cách", cli_args() == ["friend", "find", "0912345678"], cli_args())
check("tìm ra user_id và tên", r["ok"] and r["user_id"] == "8812345" and r["name"] == "Lan Anh", r)
fake_world(out=json.dumps({"data": {"uid": "77", "zaloName": "vuong"}}))
call(P._find_user, {"query": "@vuong"})
check("tìm theo username: gọi friend find-username, bỏ @", cli_args() == ["friend", "find-username", "vuong"], cli_args())
fake_world()
r = call(P._find_user, {"query": "Lan Anh ở nhóm spa"})
check("tìm theo tên tự do: không gọi CLI, chỉ sang zalo_group_members", r.startswith("ERROR") and "zalo_group_members" in r and not RAN, r)
fake_world(out="{}")
r = call(P._find_user, {"query": "0900000000"})
check("không có ai khớp: báo rõ, không bịa id", r.startswith("ERROR") and "không có người dùng" in r, r)

# ============================================================
# 2. Trạng thái
# ============================================================
fake_world(out=json.dumps({"is_friend": 0, "is_requested": 0, "is_requesting": 1}))
r = json.loads(call(P._status, {"user_id": "8812345"}))
check("trạng thái: gọi friend request-status", cli_args() == ["friend", "request-status", "8812345"], cli_args())
check("trạng thái: dịch đúng hai chiều lời mời (họ đang mời mình)", r["they_sent_request"] is True and r["i_sent_request"] is False
      and r["is_friend"] is False, r)

# ============================================================
# 3. Hành động
# ============================================================
fake_world(out='""')
r = json.loads(call(P._add, {"user_id": "8812345", "message": "Chào chị, em bên spa"}))
check("gửi lời mời: friend add kèm lời nhắn", cli_args() == ["friend", "add", "8812345", "-m", "Chào chị, em bên spa"], cli_args())
check("gửi lời mời: báo thành công", r["ok"] is True)
call(P._add, {"user_id": "8812345"})
check("không có lời nhắn thì không truyền -m rỗng", cli_args() == ["friend", "add", "8812345"], cli_args())
fake_world(out="undefined", err="  ✓ Accepted friend request from 8812345")
r = call(P._accept, {"user_id": "8812345"})
check("nhận lời mời: friend accept", cli_args() == ["friend", "accept", "8812345"], cli_args())
check("CLI in 'undefined' thay JSON nhưng có dấu ✓: vẫn là thành công", json.loads(r)["ok"] is True, r)
fake_world(out="", err="  ✗ User 8812345 may have blocked you or is unreachable.")
r = call(P._add, {"user_id": "8812345"})
check("Zalo từ chối (✗, mã thoát 0): báo lỗi kèm lý do", r.startswith("ERROR") and "blocked" in r, r)
fake_world(out='""')
call(P._reject, {"user_id": "8812345"})
check("từ chối lời mời: friend reject", cli_args() == ["friend", "reject", "8812345"], cli_args())

for bad in ("", "abc", "../x", "12"):
    fake_world()
    r = call(P._add, {"user_id": bad})
    check(f"user_id sai khuôn {bad!r}: chặn trước khi chạm Zalo", r.startswith("ERROR") and not RAN, r)
fake_world()
r = call(P._add, {"user_id": "8812345", "message": "x" * 200})
check("lời nhắn quá dài: chặn", r.startswith("ERROR") and not RAN, r)

# ============================================================
# 3b. Gói 1.3.0: bạn bè theo tên, lời mời, tra nhiều số
# ============================================================
fake_world(out=json.dumps([{"userId": "501", "displayName": "Lan Anh", "zaloName": "lananh"},
                           {"userId": "502", "displayName": "Lan Phương"}]))
r = json.loads(call(P._search_friends, {"name": "Lan"}))
check("tìm bạn theo tên: gọi friend search đúng tên", cli_args() == ["friend", "search", "Lan"], cli_args())
check("tìm bạn theo tên: trả user_id và tên từng người", r["count"] == 2 and r["friends"][0] == {"user_id": "501", "name": "Lan Anh"}, r)
fake_world(out="[]")
r = json.loads(call(P._search_friends, {"name": "Không ai"}))
check("không bạn nào khớp: chỉ sang zalo_find_user", r["count"] == 0 and "zalo_find_user" in r["note"], r)
fake_world()
r = call(P._search_friends, {"name": "L"})
check("tên quá ngắn: chặn trước khi gọi CLI", r.startswith("ERROR") and not RAN, r)
fake_world(out=json.dumps([{"userId": str(600 + i), "displayName": f"Bạn {i}"} for i in range(80)]))
r = json.loads(call(P._search_friends, {"name": "Bạn"}))
check("nhiều kết quả: có trần, báo đã cắt", len(r["friends"]) == P.MAX_LIST and r["truncated"] and r["count"] == 80, r["count"])

fake_world(out=json.dumps({"recommItems": [
    {"dataInfo": {"userId": "701", "displayName": "Khách A", "recommType": 2, "recommInfo": {"message": "Chào chị"}}},
    {"dataInfo": {"userId": "702", "displayName": "Gợi ý B", "recommType": 1}}]}))
r = json.loads(call(P._incoming, {}))
check("lời mời chờ duyệt: gọi friend recommendations", cli_args() == ["friend", "recommendations"], cli_args())
check("lời mời chờ duyệt: chỉ lấy lời mời thật (recommType 2), bỏ gợi ý của Zalo, giữ lời nhắn",
      r["count"] == 1 and r["requests"][0] == {"user_id": "701", "name": "Khách A", "message": "Chào chị"}, r)

fake_world(out=json.dumps({"8801001": {"displayName": "Anh C"}, "8801002": {"zaloName": "chi_d"}}))
r = json.loads(call(P._sent, {}))
check("lời mời đã gửi: gọi friend sent-requests", cli_args() == ["friend", "sent-requests"], cli_args())
check("lời mời đã gửi: id lấy từ khoá khi zca-js không lặp lại trong giá trị",
      sorted(x["user_id"] for x in r["requests"]) == ["8801001", "8801002"] and r["count"] == 2, r)
fake_world(rc=0, out="", err="  ● No sent friend requests")
r = json.loads(call(P._sent, {}))
check("chưa gửi lời mời nào (Zalo mã 112): danh sách rỗng, không phải lỗi", r["ok"] and r["count"] == 0, r)

fake_world(out=json.dumps({"84912345678": {"uid": "901", "display_name": "Chị E"}}))
r = json.loads(call(P._find_phones, {"phones": ["0912 345 678", "0987.654.321", "0912345678"]}))
check("tra nhiều số: bỏ dấu cách/chấm và số trùng trước khi gọi CLI",
      cli_args() == ["friend", "find-phones", "0912345678", "0987654321"], cli_args())
check("tra nhiều số: số trả về dạng 84... vẫn khớp số hỏi dạng 0...; số không có Zalo vào not_found",
      [f["user_id"] for f in r["found"]] == ["901"] and r["not_found"] == ["0987654321"], r)
fake_world()
r = call(P._find_phones, {"phones": [f"09{i:08d}" for i in range(P.MAX_PHONES + 1)]})
check("quá trần số điện thoại một lượt: chặn, không gọi CLI", r.startswith("ERROR") and str(P.MAX_PHONES) in r and not RAN, r)
r = call(P._find_phones, {"phones": ["0912345678", "Lan Anh"]})
check("có mục không phải số điện thoại: chặn, nêu mục đó", r.startswith("ERROR") and "Lan Anh" in r and not RAN, r)
fake_world(out="{}")
call(P._find_phones, {"phones": "0912345678, 0987654321"})
check("phones gửi dạng chuỗi có dấu phẩy cũng hiểu", cli_args() == ["friend", "find-phones", "0912345678", "0987654321"], cli_args())

fake_world(rc=0, out="undefined", err="  ✓ Friend request to 8812345 cancelled")
r = json.loads(call(P._undo, {"user_id": "8812345"}))
check("rút lại lời mời: gọi friend undo-request, CLI in 'undefined' + ✓ vẫn là xong",
      cli_args() == ["friend", "undo-request", "8812345"] and r["ok"], (cli_args(), r))
fake_world()
r = call(P._undo, {"user_id": "abc"})
check("rút lại lời mời: id sai khuôn bị chặn trước khi chạm Zalo", r.startswith("ERROR") and not RAN, r)

# ============================================================
# 3b. Tên gợi nhớ: Vanhanh đổi tên khách trên tài khoản Zalo
# ============================================================
fake_world(out="{}")
r = json.loads(call(P._set_alias, {"user_id": "8812345", "alias": "  Chị Lan   khách sỉ  "}))
check("đặt tên gợi nhớ: đúng lệnh friend alias <id> <tên>, dấu cách thừa được gọn",
      cli_args() == ["friend", "alias", "8812345", "Chị Lan khách sỉ"] and r["ok"] and r["alias"] == "Chị Lan khách sỉ",
      (cli_args(), r))
fake_world(rc=0, out="undefined", err="✓ Alias set")
r = call(P._set_alias, {"user_id": "8812345", "alias": "Lan"})
check("đặt tên gợi nhớ: CLI in 'undefined' kèm ✓ vẫn là xong", json.loads(r)["ok"], r)
fake_world(rc=0, out="", err="✗ Set alias failed: not friend")
r = call(P._set_alias, {"user_id": "8812345", "alias": "Lan"})
check("đặt tên gợi nhớ: Zalo từ chối (✗) thì báo lỗi, không báo xong", r.startswith("ERROR"), r)
fake_world()
r = call(P._set_alias, {"user_id": "8812345", "alias": "   "})
check("đặt tên gợi nhớ: thiếu tên thì chặn, chỉ sang tool bỏ tên", r.startswith("ERROR") and "zalo_remove_friend_alias" in r
      and not RAN, r)
r = call(P._set_alias, {"user_id": "8812345", "alias": "x" * 61})
check("đặt tên gợi nhớ: quá 60 ký tự thì chặn trước khi chạm Zalo", r.startswith("ERROR") and not RAN, r)
r = call(P._set_alias, {"user_id": "abc", "alias": "Lan"})
check("đặt tên gợi nhớ: id sai khuôn bị chặn", r.startswith("ERROR") and not RAN, r)
fake_world(out="{}")
call(P._set_alias, {"user_id": "8812345", "alias": "-VIP-"})
check("tên bắt đầu bằng '-' không bị CLI hiểu là cờ", cli_args() == ["friend", "alias", "--", "8812345", "-VIP-"], cli_args())
fake_world(out="{}")
r = json.loads(call(P._remove_alias, {"user_id": "8812345"}))
check("bỏ tên gợi nhớ: đúng lệnh friend alias-remove <id>", cli_args() == ["friend", "alias-remove", "8812345"] and r["ok"],
      (cli_args(), r))
fake_world(out=json.dumps({"items": [{"userId": "8812345", "alias": "Chị Lan"}, {"userId": "x", "alias": "rác"}]}))
r = json.loads(call(P._aliases, {"page": 2}))
check("xem tên gợi nhớ: đúng lệnh, đọc đúng khuôn, bỏ id sai khuôn",
      cli_args() == ["friend", "alias-list", "-c", "100", "-p", "2"] and r["aliases"] == [{"user_id": "8812345", "alias": "Chị Lan"}]
      and r["page"] == 2, (cli_args(), r))

# ============================================================
# 4. Đăng ký và phân quyền
# ============================================================
import yaml  # noqa: E402

y = yaml.safe_load((PACK / "plugins" / "zalo-friend" / "plugin.yaml").read_text(encoding="utf-8"))


class Ctx:
    def __init__(self):
        self.tools = []

    def register_tool(self, **kw):
        self.tools.append(kw)


tc = Ctx()
P.register(tc)
by = {t["name"]: t for t in tc.tools}
check("mười ba tool, khớp plugin.yaml", sorted(by) == sorted(y["tools"]) and len(by) == 13, sorted(by))
check("tool đọc chạy ở mọi mức", all(by[n]["min_mode"] == "readonly" for n in (
    "zalo_find_user", "zalo_find_phones", "zalo_search_friends", "zalo_friend_status", "zalo_friend_requests",
    "zalo_sent_friend_requests", "zalo_friend_aliases")))
check("tool hành động cần mức Toàn quyền, như gửi tin Zalo", all(by[n]["min_mode"] == "full" for n in (
    "zalo_add_friend", "zalo_accept_friend", "zalo_reject_friend", "zalo_undo_friend_request")))
check("đổi hay bỏ tên gợi nhớ ở mức safe: không gửi gì cho ai, chỉ tài khoản này thấy, bỏ đi là về tên cũ",
      by["zalo_set_friend_alias"]["min_mode"] == "safe" and by["zalo_remove_friend_alias"]["min_mode"] == "safe")
check("mọi tool có check_fn và handler", all(callable(t["check_fn"]) and callable(t["handler"]) for t in tc.tools))
check("plugin không có hook tự chạy (không luồng tự động nào)", y.get("hooks") == [] and not hasattr(P, "on_event"))
check("không dùng em dash", chr(0x2014) not in open(__file__, encoding="utf-8").read()
      and chr(0x2014) not in (PACK / "plugins" / "zalo-friend" / "plugin.py").read_text(encoding="utf-8")
      and chr(0x2014) not in (PACK / "plugins" / "zalo-friend" / "plugin.yaml").read_text(encoding="utf-8"))

if fails:
    print("\nFAIL - test_zalo_friend: " + str(len(fails)) + " lỗi: " + ", ".join(fails))
    sys.exit(1)
print("\nOK - test_zalo_friend: tất cả pass")
