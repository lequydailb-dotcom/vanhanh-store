"""Plugin của gói vanhanh.zalo (Vanhanh Store): công cụ KẾT BẠN trên Zalo cá nhân.

Vanhanh cần CÓ KHẢ NĂNG kết bạn, còn kết bạn với ai do model quyết định hoặc người dùng yêu cầu, không dựng tính
năng cứng. Nên plugin này CHỈ trao công cụ, không có luồng tự động nào (không "duyệt
vào nhóm thì tự kết bạn", không tự nhận mọi lời mời). Ai được dùng tới đâu là việc của mức quyền chung của Vanhanh: tool đọc chạy ở
mọi mức, tool hành động là `min_mode: full` như `zalo_send_message`, vì lời mời đã gửi đi thì người kia thấy ngay dưới tên chủ.

Cùng cách với plugin `zalo-group`: gọi lại chính CLI `vanhanh-zalo` bằng phiên đã quét QR (`server/zalo_cli.py` của lõi), không đăng
nhập lần hai, không gọi đi đâu ngoài Zalo. Lệnh dùng: `friend find`, `friend find-username`, `friend find-phones`,
`friend search`, `friend request-status`, `friend recommendations`, `friend sent-requests`, `friend add`, `friend accept`,
`friend reject`, `friend undo-request` (src/commands/friend.js của vanhanh-zalo).

Plugin còn có: tìm theo TÊN trong danh sách bạn bè, xem lời mời
đang chờ mình duyệt và lời mời mình đã gửi, rút lại lời mời, tra nhiều số điện thoại một lượt. Tìm người LẠ theo tên thì Zalo
không cho: chỉ số điện thoại hoặc username.

Tên gợi nhớ: đặt, bỏ và xem TÊN GỢI NHỚ
(alias) của bạn bè, bằng `friend alias`, `friend alias-remove`, `friend alias-list`. Tên gợi nhớ chỉ chủ tài khoản thấy, người kia
không được báo và tên Zalo của họ không đổi, nên hai tool đổi tên ở mức `safe` chứ không phải `full`: không gửi gì cho ai, và bỏ đi
là về tên cũ.

Duyệt người xin vào NHÓM không nằm ở đây: MCP chuẩn của kết nối Zalo đã có `zalo_list_join_requests` và
`zalo_review_join_requests`.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional, Tuple

import zalo_cli

MAX_MSG = 150                       # lời nhắn kèm lời mời kết bạn: Zalo chỉ hiện một dòng ngắn
_UID_RE = re.compile(r"^\d{4,25}$")
_PHONE_RE = re.compile(r"^\+?\d[\d .-]{6,18}\d$")
_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9._-]{3,40}$")
MAX_LIST = 50                       # trần số người trả về một lượt: đủ để chọn, không đổ cả danh bạ vào ngữ cảnh model
MAX_ALIAS = 60                      # tên gợi nhớ: một dòng ngắn hiện thay tên Zalo trong danh sách chat
MAX_PHONES = 20                     # trần số điện thoại tra một lượt: tra hàng loạt quá dày là kiểu Zalo coi như quét danh bạ


# ============================================================
# Tiện ích chung
# ============================================================
def _ready(args: dict) -> Tuple[Optional[dict], str]:
    """Kiểm điều kiện dùng được và chọn kết nối. Trả `(kết nối, "")` hoặc `(None, "ERROR: ...")`."""
    why = zalo_cli.check()
    if why:
        return None, "ERROR: " + why
    conn, why = zalo_cli.pick_connection(zalo_cli.connections(), str(args.get("connection_id") or ""))
    if not conn:
        return None, "ERROR: " + why
    return conn, ""


def _uid(args: dict) -> Tuple[str, str]:
    """`user_id` hợp lệ, hoặc câu lỗi chỉ đường lấy nó."""
    uid = str((args or {}).get("user_id") or "").strip()
    if not uid:
        return "", "ERROR: thiếu user_id (id Zalo của người đó). Lấy bằng zalo_find_user (số điện thoại hoặc username) " \
                    "hoặc zalo_group_members (thành viên một nhóm)."
    if not _UID_RE.match(uid):
        return "", f"ERROR: user_id '{uid}' không phải id Zalo (chuỗi số). Tìm id bằng zalo_find_user."
    return uid, ""


def _short(data: Any, limit: int = 600) -> Any:
    try:
        s = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(data)[:limit]
    return data if len(s) <= limit else s[:limit] + "..."


def _thanh_cong(ok: bool, err: str) -> bool:
    """Lệnh hành động thành công chưa. `zalo_cli.interpret` đòi có JSON trên stdout, nhưng zca-js có thể trả `undefined` cho
    lời mời/nhận lời mời, khi đó CLI in chữ "undefined" thay cho JSON dù đã làm xong và in dòng "✓ ..." ra stderr. Có "✓" mà
    không có "✗" thì coi là xong, kẻo báo lỗi oan rồi model gửi lại lần nữa."""
    if ok:
        return True
    e = str(err or "")
    return "✓" in e and "✗" not in e


def _done(**kw) -> str:
    return json.dumps({"ok": True, **kw}, ensure_ascii=False)


def _fail(what: str, err: str) -> str:
    """Hết giờ là kết cục KHÔNG RÕ (CLI có thể đã làm xong rồi mới bị giết): dặn kiểm trạng thái trước khi thử lại."""
    if zalo_cli.is_timeout(err):
        return (f"ERROR: {what} quá giờ và KHÔNG rõ đã thành công chưa ({err}). Xem lại bằng zalo_friend_status "
                "trước khi thử lại.")
    return f"ERROR: {what} không được. {err}"


def _profile(data: Any) -> dict:
    """Rút uid và tên từ kết quả `friend find` / `find-username` (zca-js trả khi phẳng, khi bọc trong `data`)."""
    u = data if isinstance(data, dict) else {}
    if not u.get("uid") and isinstance(u.get("data"), dict):
        u = u["data"]
    return {"uid": str(u.get("uid") or u.get("userId") or ""),
            "name": str(u.get("display_name") or u.get("displayName") or u.get("zalo_name") or u.get("zaloName") or ""),
            "avatar": str(u.get("avatar") or "")}


# ============================================================
# Tool đọc
# ============================================================
async def _find_user(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    q = str(args.get("query") or "").strip()
    if not q:
        return "ERROR: thiếu query (số điện thoại, id Zalo, hoặc username Zalo)."
    digits = re.sub(r"[ .-]", "", q)
    if _PHONE_RE.match(q) or _UID_RE.match(digits):
        ok, data, err = await zalo_cli.run_cli(conn, ["friend", "find"], [digits])
    elif _USERNAME_RE.match(q):
        ok, data, err = await zalo_cli.run_cli(conn, ["friend", "find-username"], [q.lstrip("@")])
    else:
        return "ERROR: query phải là số điện thoại, id Zalo (chuỗi số) hoặc username Zalo. Tìm theo TÊN thì dùng " \
               "zalo_group_members (trong một nhóm) hoặc zalo_search_threads (người đã từng nhắn)."
    if not ok:
        return f"ERROR: không tìm được người dùng Zalo '{q}'. {err}"
    p = _profile(data)
    if not p["uid"]:
        return f"ERROR: không có người dùng Zalo nào khớp '{q}' (có thể họ tắt cho tìm bằng số điện thoại)."
    return _done(account=conn["label"], query=q, user_id=p["uid"], name=p["name"], avatar=p["avatar"])


async def _status(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "request-status"], [uid])
    if not ok:
        return f"ERROR: không xem được trạng thái kết bạn với {uid}. {err}"
    d = data if isinstance(data, dict) else {}
    return _done(account=conn["label"], user_id=uid,
                 is_friend=bool(d.get("is_friend")),
                 # Tên trường của Zalo: is_requested = MÌNH đã gửi lời mời cho họ; is_requesting = HỌ đang mời mình.
                 i_sent_request=bool(d.get("is_requested")),
                 they_sent_request=bool(d.get("is_requesting")),
                 raw=_short(d))


def _nguoi(u: Any) -> dict:
    """Một người trong danh sách (bạn bè, lời mời) -> {user_id, name}. zca-js đặt tên trường khác nhau tuỳ lệnh."""
    u = u if isinstance(u, dict) else {}
    return {"user_id": str(u.get("userId") or u.get("uid") or u.get("user_id") or ""),
            "name": str(u.get("displayName") or u.get("display_name") or u.get("zaloName") or u.get("zalo_name") or "")}


async def _search_friends(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    name = str(args.get("name") or "").strip()
    if len(name) < 2:
        return "ERROR: thiếu name (ít nhất 2 ký tự của tên bạn bè cần tìm)."
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "search"], [name])
    if not ok:
        return f"ERROR: không tìm được trong danh sách bạn bè. {err}"
    ds = [p for p in (_nguoi(u) for u in (data if isinstance(data, list) else [])) if p["user_id"]]
    return _done(account=conn["label"], name=name, count=len(ds), friends=ds[:MAX_LIST],
                 truncated=len(ds) > MAX_LIST,
                 note="" if ds else "Không có bạn bè nào có tên này. Người chưa kết bạn thì tìm bằng zalo_find_user "
                                    "(số điện thoại hoặc username).")


async def _incoming(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "recommendations"], [])
    if not ok:
        return f"ERROR: không đọc được lời mời kết bạn. {err}"
    items = (data or {}).get("recommItems") if isinstance(data, dict) else None
    moi = []
    for it in items or []:
        d = (it or {}).get("dataInfo") or {}
        # recommType 2 = người ta gửi lời mời cho mình; còn lại là Zalo gợi ý kết bạn, không phải lời mời.
        if d.get("recommType") != 2:
            continue
        p = _nguoi(d)
        if p["user_id"]:
            p["message"] = str((d.get("recommInfo") or {}).get("message") or "")
            moi.append(p)
    return _done(account=conn["label"], count=len(moi), requests=moi[:MAX_LIST], truncated=len(moi) > MAX_LIST)


async def _sent(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "sent-requests"], [])
    if not ok:
        # Zalo trả mã 112 khi chưa gửi lời mời nào; CLI in "No sent friend requests" thay vì JSON.
        if "No sent friend requests" in str(err) or "(112)" in str(err):
            return _done(account=conn["label"], count=0, requests=[])
        return f"ERROR: không đọc được lời mời đã gửi. {err}"
    ds = []
    for uid, u in (data.items() if isinstance(data, dict) else []):
        p = _nguoi(u)
        p["user_id"] = p["user_id"] or str(uid)
        if _UID_RE.match(p["user_id"]):
            ds.append(p)
    return _done(account=conn["label"], count=len(ds), requests=ds[:MAX_LIST], truncated=len(ds) > MAX_LIST)


def _so(q: str) -> str:
    return re.sub(r"[ .-]", "", q)


async def _find_phones(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    raw = args.get("phones")
    if isinstance(raw, str):
        raw = re.split(r"[,;\n]+", raw)
    phones, sai = [], []
    for x in raw or []:
        q = str(x or "").strip()
        if not q:
            continue
        if _PHONE_RE.match(q):
            phones.append(_so(q))
        else:
            sai.append(q)
    phones = list(dict.fromkeys(phones))
    if sai:
        return f"ERROR: không phải số điện thoại: {', '.join(sai[:5])}."
    if not phones:
        return "ERROR: thiếu phones (danh sách số điện thoại)."
    if len(phones) > MAX_PHONES:
        return f"ERROR: tối đa {MAX_PHONES} số một lượt (tra dày quá Zalo có thể coi là quét danh bạ). Chia thành nhiều lượt."
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "find-phones"], phones)
    if not ok:
        return f"ERROR: không tra được các số điện thoại. {err}"
    found = []
    for phone, u in (data.items() if isinstance(data, dict) else []):
        p = _nguoi(u)
        if p["user_id"]:
            found.append(dict(phone=str(phone), **p))
    # Zalo có thể trả số ở dạng 84xxxxxxxxx dù hỏi 0xxxxxxxxx: so 9 chữ số cuối.
    co = {f["phone"][-9:] for f in found}
    return _done(account=conn["label"], found=found, not_found=[x for x in phones if x[-9:] not in co])


# ============================================================
# Tool hành động
# ============================================================
async def _add(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    msg = str(args.get("message") or "").strip()
    if len(msg) > MAX_MSG:
        return f"ERROR: lời nhắn kèm lời mời dài quá {MAX_MSG} ký tự."
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "add"], [uid], ["-m", msg] if msg else [])
    if not _thanh_cong(ok, err):
        return _fail("gửi lời mời kết bạn", err)
    return _done(account=conn["label"], user_id=uid, message=msg, result=_short(data))


async def _accept(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "accept"], [uid])
    if not _thanh_cong(ok, err):
        return _fail("nhận lời mời kết bạn", err)
    return _done(account=conn["label"], user_id=uid, result=_short(data))


async def _reject(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "reject"], [uid])
    if not _thanh_cong(ok, err):
        return _fail("từ chối lời mời kết bạn", err)
    return _done(account=conn["label"], user_id=uid, result=_short(data))


async def _undo(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "undo-request"], [uid])
    if not _thanh_cong(ok, err):
        return _fail("rút lại lời mời kết bạn", err)
    return _done(account=conn["label"], user_id=uid, result=_short(data))


# ============================================================
# Tên gợi nhớ (alias) của bạn bè
# ============================================================
async def _aliases(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    try:
        page = max(1, int(args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "alias-list"], [], ["-c", "100", "-p", str(page)])
    if not ok:
        return f"ERROR: không đọc được danh sách tên gợi nhớ. {err}"
    items = (data or {}).get("items") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    ds = []
    for it in items or []:
        it = it if isinstance(it, dict) else {}
        uid = str(it.get("userId") or it.get("uid") or "")
        if _UID_RE.match(uid):
            ds.append({"user_id": uid, "alias": str(it.get("alias") or "")})
    return _done(account=conn["label"], page=page, count=len(ds), aliases=ds[:MAX_LIST], truncated=len(ds) > MAX_LIST,
                 note="Mỗi trang tối đa 100 người; còn nữa thì gọi lại với page kế tiếp." if len(ds) >= 100 else "")


async def _set_alias(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    alias = " ".join(str(args.get("alias") or "").split())
    if not alias:
        return "ERROR: thiếu alias (tên gợi nhớ muốn đặt). Muốn bỏ tên gợi nhớ thì dùng zalo_remove_friend_alias."
    if len(alias) > MAX_ALIAS:
        return f"ERROR: tên gợi nhớ dài quá {MAX_ALIAS} ký tự."
    # Tên bắt đầu bằng "-" (vd "-VIP-") thì zalo_cli.run_cli tự đặt "--" trước tham số vị trí, CLI không tưởng là cờ.
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "alias"], [uid, alias])
    if not _thanh_cong(ok, err):
        return _fail("đặt tên gợi nhớ", err)
    return _done(account=conn["label"], user_id=uid, alias=alias, result=_short(data),
                 note="Tên gợi nhớ chỉ tài khoản này thấy; người kia không được báo.")


async def _remove_alias(args, ctx):
    args = args or {}
    conn, why = _ready(args)
    if not conn:
        return why
    uid, why = _uid(args)
    if not uid:
        return why
    ok, data, err = await zalo_cli.run_cli(conn, ["friend", "alias-remove"], [uid])
    if not _thanh_cong(ok, err):
        return _fail("bỏ tên gợi nhớ", err)
    return _done(account=conn["label"], user_id=uid, result=_short(data))


# ============================================================
# Đăng ký
# ============================================================
_CONN = {"connection_id": {"type": "string", "description": "id kết nối Zalo, chỉ cần khi đã đấu nhiều tài khoản"}}
_USER = {"user_id": {"type": "string", "description": "id Zalo của người đó (chuỗi số)"}}


def register(ctx):
    ctx.register_tool(
        name="zalo_find_user",
        description=(
            "Tìm một người dùng Zalo theo số điện thoại, id Zalo hoặc username, trả user_id và tên hiển thị. Chỉ đọc. "
            "Tìm theo tên trong một nhóm thì dùng zalo_group_members."
        ),
        handler=_find_user, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            "query": {"type": "string", "description": "số điện thoại, id Zalo, hoặc username Zalo"}, **_CONN},
            "required": ["query"]},
    )
    ctx.register_tool(
        name="zalo_friend_status",
        description=(
            "Trạng thái kết bạn giữa tài khoản Zalo đã kết nối và một người: đã là bạn chưa, mình đã gửi lời mời chưa, "
            "họ có đang gửi lời mời cho mình không. Chỉ đọc."
        ),
        handler=_status, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_USER, **_CONN}, "required": ["user_id"]},
    )
    ctx.register_tool(
        name="zalo_search_friends",
        description=(
            "Tìm theo TÊN trong danh sách bạn bè Zalo của tài khoản đã kết nối, trả user_id (dùng làm threadId để nhắn) "
            "và tên. Chỉ đọc. Người chưa là bạn thì dùng zalo_find_user."
        ),
        handler=_search_friends, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            "name": {"type": "string", "description": "một phần tên hiển thị hoặc tên Zalo"}, **_CONN},
            "required": ["name"]},
    )
    ctx.register_tool(
        name="zalo_friend_requests",
        description=(
            "Danh sách lời mời kết bạn người khác đang gửi tới tài khoản Zalo đã kết nối, chờ duyệt (user_id, tên, lời "
            "nhắn). Chỉ đọc. Nhận hay từ chối bằng zalo_accept_friend / zalo_reject_friend."
        ),
        handler=_incoming, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_CONN}},
    )
    ctx.register_tool(
        name="zalo_sent_friend_requests",
        description=(
            "Danh sách lời mời kết bạn tài khoản Zalo đã kết nối đã gửi đi mà người kia chưa nhận. Chỉ đọc. Rút lại bằng "
            "zalo_undo_friend_request."
        ),
        handler=_sent, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_CONN}},
    )
    ctx.register_tool(
        name="zalo_find_phones",
        description=(
            "Tra nhiều số điện thoại một lượt (tối đa 20), trả số nào có Zalo kèm user_id và tên, số nào không tìm thấy. "
            "Chỉ đọc."
        ),
        handler=_find_phones, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            "phones": {"type": "array", "items": {"type": "string"}, "description": "các số điện thoại"}, **_CONN},
            "required": ["phones"]},
    )
    ctx.register_tool(
        name="zalo_add_friend",
        description=(
            "Gửi lời mời kết bạn Zalo tới một người, bằng tài khoản Zalo đã kết nối. Tham số: user_id, message (lời nhắn "
            "kèm theo, tuỳ chọn, tối đa 150 ký tự)."
        ),
        handler=_add, min_mode="full", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            **_USER, "message": {"type": "string", "description": "lời nhắn kèm lời mời (tuỳ chọn)"}, **_CONN},
            "required": ["user_id"]},
    )
    ctx.register_tool(
        name="zalo_accept_friend",
        description="Nhận lời mời kết bạn Zalo mà một người đã gửi tới tài khoản Zalo đã kết nối. Tham số: user_id.",
        handler=_accept, min_mode="full", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_USER, **_CONN}, "required": ["user_id"]},
    )
    ctx.register_tool(
        name="zalo_reject_friend",
        description="Từ chối lời mời kết bạn Zalo mà một người đã gửi tới tài khoản Zalo đã kết nối. Tham số: user_id.",
        handler=_reject, min_mode="full", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_USER, **_CONN}, "required": ["user_id"]},
    )
    ctx.register_tool(
        name="zalo_friend_aliases",
        description=(
            "Danh sách tên gợi nhớ (alias) tài khoản Zalo đã kết nối đặt cho bạn bè: user_id và tên gợi nhớ, 100 người "
            "mỗi trang (tham số page). Chỉ đọc."
        ),
        handler=_aliases, min_mode="readonly", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            "page": {"type": "integer", "description": "trang, bắt đầu từ 1"}, **_CONN}},
    )
    ctx.register_tool(
        name="zalo_set_friend_alias",
        description=(
            "Đổi tên một khách hay bạn bè trên tài khoản Zalo đã kết nối, bằng tên gợi nhớ (alias): tên này hiện thay tên "
            "Zalo của họ, chỉ tài khoản này thấy, người kia không được báo. Tham số: user_id (lấy bằng zalo_search_friends "
            "hoặc zalo_find_user), alias (tối đa 60 ký tự)."
        ),
        handler=_set_alias, min_mode="safe", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            **_USER, "alias": {"type": "string", "description": "tên gợi nhớ muốn đặt"}, **_CONN},
            "required": ["user_id", "alias"]},
    )
    ctx.register_tool(
        name="zalo_remove_friend_alias",
        description=(
            "Bỏ tên gợi nhớ (alias) đã đặt cho một người trên tài khoản Zalo đã kết nối, để hiện lại tên Zalo gốc của họ. "
            "Tham số: user_id."
        ),
        handler=_remove_alias, min_mode="safe", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_USER, **_CONN}, "required": ["user_id"]},
    )
    ctx.register_tool(
        name="zalo_undo_friend_request",
        description="Rút lại lời mời kết bạn Zalo mà tài khoản đã kết nối đã gửi cho một người. Tham số: user_id.",
        handler=_undo, min_mode="full", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {**_USER, **_CONN}, "required": ["user_id"]},
    )
