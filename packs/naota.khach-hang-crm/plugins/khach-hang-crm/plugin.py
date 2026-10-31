"""Quản lý khách hàng (CRM) trên kho hội thoại khách đa kênh của NAOTA.

Gói này là TẦNG TRÊN của trang Hội thoại (Naota 1.0.0+): lõi Naota đã gom tin từ bot
Telegram, bot Zalo và Zalo cá nhân về một kho (khách -> hội thoại -> tin). Plugin đọc kho đó
qua đúng các hàm của `conversations` (tầng CRM 1.0.0+), không tự viết SQL: schema là của lõi, lõi đổi thì
hàm của lõi đổi theo, còn SQL chép ở đây sẽ gãy im lặng.

Tám tool, chia hai nhóm:
- CHỈ ĐỌC (readonly): danh sách khách, hồ sơ một khách, hội thoại, tìm tin, chờ trả lời, thống kê.
- GHI NHẸ (safe): gắn tag / ghi chú lên khách (ghi vào kho khách của lõi), xuất CSV vào
  thư mục exports/ của brain đang mở. Không tool nào gửi tin hay gọi ra ngoài; muốn trả lời
  khách thì dùng tool của kênh (zalo_send_message, bot Telegram...) như bình thường.

Ba luật viết plugin của Naota, giữ đúng:
1. `register(ctx)` là toàn bộ hợp đồng; handler nhận `(args, ctx)` và trả CHUỖI.
2. Sai đầu vào thì trả chuỗi bắt đầu bằng `ERROR:`, không ném exception.
3. Tên tool mang tiền tố riêng (`crm_`) để không đụng tool có sẵn.
"""
from __future__ import annotations

import csv
import io
import json
import time
from datetime import datetime
from pathlib import Path

_TRAN_KY_TU = 40_000     # kết quả dài hơn thì cắt: model đọc 40k ký tự đã là quá nhiều
_TRAN_DONG = 500


def _kho():
    """Kho hội thoại của lõi Naota (module `conversations`, tầng CRM có từ 1.0.0).
    Trả (module, None) hoặc (None, lý do)."""
    try:
        import conversations as cs
    except Exception:
        return None, ("ERROR: Naota này chưa có kho hội thoại khách (cần NAOTA 1.0.0 trở lên). "
                      "Cập nhật Naota rồi gọi lại.")
    if not hasattr(cs, "danh_sach_khach"):
        return None, ("ERROR: kho hội thoại của Naota này chưa có tầng CRM (cần NAOTA 1.0.0 trở lên). "
                      "Cập nhật Naota rồi gọi lại.")
    return cs, None


def _check():
    _, loi = _kho()
    return loi[7:] if loi else None


def _gio(ts):
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _so(v, mac, lo=1, cao=_TRAN_DONG):
    try:
        n = int(v) if v not in (None, "") else mac
    except (TypeError, ValueError):
        return mac
    return max(lo, min(n, cao))


def _ra(d):
    s = json.dumps(d, ensure_ascii=False, indent=1)
    if len(s) > _TRAN_KY_TU:
        s = s[:_TRAN_KY_TU] + "\n... (đã cắt, hãy thu hẹp bộ lọc hoặc giảm limit)"
    return s


def _khach_gon(c):
    return {
        "id": c["id"], "ten": c.get("name") or "(chưa có tên)",
        "kenh": c.get("channel_label") or c.get("channel"), "tai_khoan": c.get("account_name") or "",
        "id_tren_kenh": c.get("external_user_id"), "tags": c.get("tags") or [],
        "ghi_chu": c.get("note") or "", "so_tin": c.get("so_tin") or 0,
        "lan_dau": _gio(c.get("first_seen_at")), "lan_cuoi": _gio(c.get("last_seen_at")),
    }


def _hoi_thoai_gon(v):
    return {
        "id": v["id"], "ten": v.get("title") or v.get("customer_name") or v.get("external_chat_id"),
        "kenh": v.get("channel_label") or v.get("channel"),
        "bot_id": v.get("bot_id") or "", "loai": "nhóm" if v.get("chat_type") == "group" else "riêng",
        "che_do": v.get("mode"), "khach_id": v.get("customer_id"),
        "tin_cuoi": v.get("last_message") or "", "nguoi_noi_cuoi": v.get("last_sender_type") or "",
        "luc": _gio(v.get("last_message_at")), "chua_doc": v.get("unread_count") or 0,
        "so_tin": v.get("message_count") or 0, "tags": v.get("customer_tags") or [],
    }


def _tin_gon(m):
    d = {"id": m["id"], "ai": m.get("sender_type"), "ten": m.get("sender_name") or "",
         "luc": _gio(m.get("created_at")), "loai": m.get("message_type"), "text": m.get("text") or ""}
    meta = m.get("metadata") or {}
    if meta.get("file"):
        d["file"] = meta["file"]
    if isinstance(meta.get("attachment"), dict) and meta["attachment"].get("url"):
        d["url"] = meta["attachment"]["url"]
    return d


# ============================================================
# Tool chỉ đọc
# ============================================================
def crm_khach_hang(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    ds = st.danh_sach_khach(channel=str(a.get("kenh") or "").strip().lower(), tag=str(a.get("tag") or "").strip(),
                           q=str(a.get("q") or "").strip(), days=_so(a.get("ngay"), 0, 0, 3650),
                           limit=_so(a.get("limit"), 50))
    return _ra({"so_khach": len(ds), "khach": [_khach_gon(c) for c in ds]})


def crm_ho_so_khach(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    kid = a.get("khach_id")
    if not kid:
        q = str(a.get("q") or "").strip()
        if not q:
            return "ERROR: cần 'khach_id' hoặc 'q' (tên / username / id trên kênh) để tìm khách."
        ds = st.danh_sach_khach(q=q, limit=10)
        if not ds:
            return f"Không thấy khách nào khớp '{q}'."
        if len(ds) > 1:
            return _ra({"nhieu_ket_qua": True, "goi_y": "Hỏi lại người dùng rồi gọi với khach_id",
                        "khach": [_khach_gon(c) for c in ds]})
        kid = ds[0]["id"]
    try:
        kid = int(kid)
    except (TypeError, ValueError):
        return "ERROR: 'khach_id' phải là số."
    c = st.khach(kid)
    if not c:
        return f"ERROR: không có khách id {kid}."
    so_tin = _so(a.get("so_tin"), 30, 1, 200)
    hoi_thoai = []
    for v in st.hoi_thoai_cua_khach(kid):
        d = _hoi_thoai_gon(v)
        d["tin_gan_nhat"] = [_tin_gon(m) for m in st.tin_nhan(v["id"], limit=so_tin)]
        hoi_thoai.append(d)
    return _ra({"khach": _khach_gon(c), "hoi_thoai": hoi_thoai})


def crm_hoi_thoai(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    if a.get("hoi_thoai_id"):
        try:
            cid = int(a["hoi_thoai_id"])
        except (TypeError, ValueError):
            return "ERROR: 'hoi_thoai_id' phải là số."
        v = st.chi_tiet(cid)
        if not v:
            return f"ERROR: không có hội thoại id {cid}."
        return _ra({"hoi_thoai": _hoi_thoai_gon(v),
                    "tin": [_tin_gon(m) for m in st.tin_nhan(cid, limit=_so(a.get("limit"), 60, 1, 500))]})
    ds = st.danh_sach(channel=str(a.get("kenh") or "").strip().lower(), bot_id=str(a.get("bot_id") or "").strip(),
                      q=str(a.get("q") or "").strip(), limit=_so(a.get("limit"), 30))
    if a.get("chua_doc"):
        ds = [v for v in ds if (v.get("unread_count") or 0) > 0]
    return _ra({"so_hoi_thoai": len(ds), "hoi_thoai": [_hoi_thoai_gon(v) for v in ds]})


def crm_tim_tin(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    q = str(a.get("q") or "").strip()
    if not q:
        return "ERROR: thiếu 'q' (chữ cần tìm trong tin nhắn)."
    ds = st.tim_tin(q, channel=str(a.get("kenh") or "").strip().lower(), limit=_so(a.get("limit"), 40))
    return _ra({"so_tin": len(ds), "tin": [{
        "hoi_thoai_id": m["conversation_id"], "khach": m.get("customer_name") or m.get("title") or m.get("external_chat_id"),
        "kenh": m.get("channel"), "ai": m.get("sender_type"), "luc": _gio(m.get("created_at")), "text": m.get("text") or "",
    } for m in ds]})


def crm_cho_tra_loi(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    try:
        gio = float(a.get("gio") if a.get("gio") not in (None, "") else 2)
    except (TypeError, ValueError):
        return "ERROR: 'gio' phải là số giờ."
    ds = st.cho_tra_loi(max(0.0, gio), _so(a.get("limit"), 50))
    out = []
    for v in ds:
        d = _hoi_thoai_gon(v)
        try:
            d["cho_da_gio"] = round((time.time() - float(v.get("last_message_at") or time.time())) / 3600, 1)
        except Exception:
            d["cho_da_gio"] = None
        out.append(d)
    return _ra({"nguong_gio": gio, "so_hoi_thoai": len(out),
                "luu_y": "Với Zalo cá nhân, tin chủ tự trả lời bằng app trên điện thoại có thể không vào kho, "
                         "nên hội thoại đó có thể đã được trả lời rồi. Kiểm lại trước khi nhắn thêm.",
                "hoi_thoai": out})


def crm_thong_ke(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    ngay = _so(a.get("ngay"), 7, 1, 365)
    kenh = str(a.get("kenh") or "").strip().lower()
    tong = st.thong_ke(bot_id=str(a.get("bot_id") or "").strip(), channel=kenh)
    kh = st.thong_ke_khach(ngay, channel=kenh)
    return _ra({"hoi_thoai": tong, "khach": kh["khach"], "so_ngay": ngay,
                "khach_moi_theo_ngay": kh["khach_moi_theo_ngay"], "tag": kh["theo_tag"],
                "cho_tra_loi": kh["cho_tra_loi"]})


# ============================================================
# Tool ghi nhẹ (safe)
# ============================================================
def crm_gan_tag(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    try:
        kid = int(a.get("khach_id"))
    except (TypeError, ValueError):
        return "ERROR: thiếu 'khach_id' (số). Tìm bằng crm_khach_hang hoặc crm_ho_so_khach trước."
    c = st.khach(kid)
    if not c:
        return f"ERROR: không có khách id {kid}."
    tags = list(c.get("tags") or [])

    def _ds(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [x.strip() for x in str(v or "").split(",") if x.strip()]
    if a.get("tags") is not None:
        tags = _ds(a.get("tags"))
    for t in _ds(a.get("them")):
        if t not in tags:
            tags.append(t)
    bo = _ds(a.get("bo"))
    tags = [t for t in tags if t not in bo]
    tags = st.dat_tag_khach(kid, tags) or []
    if a.get("ghi_chu") is not None:
        st.dat_ghi_chu_khach(kid, str(a.get("ghi_chu") or ""))
    return _ra({"ok": True, "khach": _khach_gon(st.khach(kid))})


def crm_xuat_csv(args, ctx):
    st, loi = _kho()
    if loi:
        return loi
    a = args or {}
    root = getattr(ctx, "vault_root", None)
    if not root:
        return "ERROR: không biết brain đang mở nên không biết ghi CSV vào đâu."
    ds = st.danh_sach_khach(channel=str(a.get("kenh") or "").strip().lower(), tag=str(a.get("tag") or "").strip(),
                           q=str(a.get("q") or "").strip(), days=_so(a.get("ngay"), 0, 0, 3650), limit=5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "ten", "kenh", "tai_khoan", "id_tren_kenh", "tags", "ghi_chu", "so_tin", "lan_dau", "lan_cuoi"])
    for c in ds:
        g = _khach_gon(c)
        w.writerow([g["id"], g["ten"], g["kenh"], g["tai_khoan"], g["id_tren_kenh"],
                    ", ".join(g["tags"]), g["ghi_chu"], g["so_tin"], g["lan_dau"], g["lan_cuoi"]])
    thu_muc = Path(root) / "exports"
    thu_muc.mkdir(parents=True, exist_ok=True)
    ten = f"khach-hang-{datetime.now().strftime('%Y-%m-%d-%H%M')}.csv"
    dich = thu_muc / ten
    dich.write_text("﻿" + buf.getvalue(), encoding="utf-8")   # BOM để Excel mở đúng tiếng Việt
    return _ra({"ok": True, "so_khach": len(ds), "file": f"exports/{ten}",
                "goi_y": f"Nhúng vào câu trả lời bằng [{ten}](exports/{ten}) để người dùng tải."})


# ============================================================
# Đăng ký
# ============================================================
def _t(ctx, name, desc, handler, min_mode, emoji, props, required=None):
    ctx.register_tool(name=name, description=desc, handler=handler, min_mode=min_mode, emoji=emoji,
                      schema={"type": "object", "properties": props, "required": list(required or [])},
                      check_fn=_check)


def register(ctx):
    KENH = {"type": "string", "description": "Lọc kênh: telegram | zalo (bot) | zalo_personal (Zalo cá nhân). Trống = mọi kênh."}
    LIMIT = {"type": "integer", "description": "Số dòng tối đa."}
    _t(ctx, "crm_khach_hang",
       "CRM: danh sách khách hàng đã nhắn qua các kênh chat (Telegram, Zalo Bot, Zalo cá nhân), mới nhất trước. "
       "Lọc theo kênh, tag, chữ (tên/username/ghi chú) hoặc số ngày gần đây. Trả id khách để dùng cho tool khác.",
       crm_khach_hang, "readonly", "👥",
       {"kenh": KENH, "tag": {"type": "string", "description": "Chỉ khách có tag này (khớp nguyên từ)."},
        "q": {"type": "string", "description": "Tìm trong tên, username, id trên kênh, ghi chú."},
        "ngay": {"type": "integer", "description": "Chỉ khách có nhắn trong N ngày gần đây."}, "limit": LIMIT})
    _t(ctx, "crm_ho_so_khach",
       "CRM: hồ sơ MỘT khách: thông tin, tag, ghi chú, mọi hội thoại của người đó kèm tin gần nhất. "
       "Truyền khach_id, hoặc q (tên) để tìm; nhiều người trùng thì tool trả danh sách để hỏi lại.",
       crm_ho_so_khach, "readonly", "🪪",
       {"khach_id": {"type": "integer"}, "q": {"type": "string", "description": "Tên / username khách khi chưa biết id."},
        "so_tin": {"type": "integer", "description": "Số tin gần nhất mỗi hội thoại (mặc định 30)."}})
    _t(ctx, "crm_hoi_thoai",
       "CRM: danh sách hội thoại khách (mọi kênh) hoặc toàn bộ tin của MỘT hội thoại khi truyền hoi_thoai_id. "
       "Lọc theo kênh, bot, chưa đọc, chữ.",
       crm_hoi_thoai, "readonly", "💬",
       {"hoi_thoai_id": {"type": "integer", "description": "Đọc tin của hội thoại này."}, "kenh": KENH,
        "bot_id": {"type": "string", "description": "Chỉ hội thoại do chatbot này xử lý."},
        "chua_doc": {"type": "boolean"}, "q": {"type": "string"}, "limit": LIMIT})
    _t(ctx, "crm_tim_tin",
       "CRM: tìm chữ trong MỌI tin nhắn khách và bot (vd tên sản phẩm, 'hoàn tiền', số điện thoại). Trả hội thoại chứa tin đó.",
       crm_tim_tin, "readonly", "🔎", {"q": {"type": "string"}, "kenh": KENH, "limit": LIMIT}, ["q"])
    _t(ctx, "crm_cho_tra_loi",
       "CRM: hội thoại mà câu CUỐI là của khách và đã quá N giờ chưa ai trả lời (mặc định 2 giờ). "
       "Dùng để rà khách bị bỏ quên trước khi nhắn theo dõi.",
       crm_cho_tra_loi, "readonly", "⏰", {"gio": {"type": "number"}, "limit": LIMIT})
    _t(ctx, "crm_thong_ke",
       "CRM: thống kê: tổng hội thoại, hôm nay, chưa đọc, chờ trả lời, số khách, tin AI/khách, theo kênh, "
       "khách mới theo ngày trong N ngày, số khách mỗi tag.",
       crm_thong_ke, "readonly", "📊", {"ngay": {"type": "integer"}, "kenh": KENH, "bot_id": {"type": "string"}})
    _t(ctx, "crm_gan_tag",
       "CRM: gắn / bỏ tag và ghi chú lên một khách (vd 'VIP', 'Quan tâm', 'Đã mua'). 'them' và 'bo' sửa dần; "
       "'tags' thay cả danh sách; 'ghi_chu' thay ghi chú. Chỉ ghi vào kho khách của Naota, không gửi gì cho khách.",
       crm_gan_tag, "safe", "🏷️",
       {"khach_id": {"type": "integer"}, "them": {"type": "array", "items": {"type": "string"}},
        "bo": {"type": "array", "items": {"type": "string"}}, "tags": {"type": "array", "items": {"type": "string"}},
        "ghi_chu": {"type": "string"}}, ["khach_id"])
    _t(ctx, "crm_xuat_csv",
       "CRM: xuất danh sách khách (cùng bộ lọc như crm_khach_hang) ra file CSV trong thư mục exports/ của brain, "
       "mở được bằng Excel. Trả đường dẫn để nhúng vào câu trả lời.",
       crm_xuat_csv, "safe", "📤",
       {"kenh": KENH, "tag": {"type": "string"}, "q": {"type": "string"}, "ngay": {"type": "integer"}})
