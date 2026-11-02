"""Naota Gate: cổng cho ChatGPT, Claude và AI khác làm việc cùng Naota qua một MCP connector.

Vì sao là một gói, không phải tính năng có sẵn
----------------------------------------------
Cửa này không nằm sẵn trong lõi vì nguyên tắc của Naota: mọi cuộc chat nằm chung MỘT nền tảng.
Ai vẫn muốn chat trên chatgpt.com hay claude.ai bằng gói của mình thì cài gói này, và việc cài là
lựa chọn có chủ ý của họ.

Bản 2.0.0 (cần Naota 1.1.0): tên mới Naota Gate (mã cũ `naota.naota-trong-chatgpt`, plugin
`naota-trong-chatgpt`), thêm Claude, và bốn tool chat lõi Naota cấp riêng cho cửa này: AI bên ngoài
đọc hội thoại của Naota và nhắn THẲNG vào khung chat như chủ gõ, thay vì giao việc qua Kanban. Lượt
đó chạy trên Naota như mọi lượt chat: chủ xem chữ chạy, bấm Dừng được, Naota học được.

Cách chạy
---------
Người dùng chat trên chatgpt.com hay claude.ai như bình thường, còn AI đó tự gọi sang Naota qua
tính năng MCP connector chính thức. Naota vốn đã là một MCP server đầy đủ (hub mà Claude Code và
Codex dùng); gói này chỉ thêm CỬA: OAuth 2.1 tối giản, đúng phần các AI đó dùng.

  - khám phá: RFC 9728 (protected resource) + RFC 8414 (authorization server)
  - đăng ký client động: RFC 7591 (ChatGPT tự đăng ký, không phải dán client id)
  - mã cấp quyền + PKCE S256 (bắt buộc, không nhận `plain`)
  - làm mới token có XOAY vòng (dùng lại refresh cũ là thu hồi cả họ), thu hồi: RFC 7009

Bước "Cho phép" dựa vào ĐĂNG NHẬP DASHBOARD sẵn có (mật khẩu + 2FA), không thêm bí mật nào.

Dùng `ctx.register_http` và `ctx.register_well_known` của lõi.

Ranh giới an toàn
-----------------
- Naota chưa có mật khẩu quản trị thì mọi cửa OAuth trả 404: cửa đồng ý dựa vào đăng nhập.
- `redirect_uri` chỉ nhận máy của OpenAI, của Anthropic, hoặc chính máy của chủ (localhost, cho
  Claude Code và Claude Desktop). Kẻ tự đăng ký client trỏ về máy mình rồi dụ chủ bấm "Cho phép"
  sẽ không nhận được mã.
- Token, mã cấp quyền chỉ lưu dạng BĂM SHA-256. Tệp lộ ra không dùng được để gọi.
- Token của cửa này KHÔNG phải `hub_token` của Claude Code/Codex, và ngược lại.
- Mức quyền (full / auto / suggest) chủ chọn trên trang của gói; hub ép ở lớp cứng như mọi
  engine khác, đọc lại TỪNG lượt gọi nên hạ quyền có hiệu lực ngay.
- Các cửa máy chủ OpenAI gọi (đổi token, MCP...) khai `no_cookie`: lõi Naota gỡ cookie trước
  khi giao request cho gói, nên không trang lạ nào mượn được phiên của chủ qua đó.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import secrets
import threading
import time
from urllib.parse import urlencode, urlparse

TTL_ACCESS = 3600                   # 1 giờ; ChatGPT tự làm mới
TTL_REFRESH = 30 * 24 * 3600        # 30 ngày không dùng thì phải cho phép lại
TTL_MA = 300                        # mã cấp quyền sống 5 phút, dùng MỘT lần
TTL_YEU_CAU = 600                   # trang Cho phép mở quá 10 phút thì bắt đầu lại từ ChatGPT
MAX_CLIENT = 20                     # chặn ai đó đăng ký client tới đầy đĩa
MAX_YEU_CAU = 100
MUC_QUYEN = ("full", "auto", "suggest")
MUC_MAC_DINH = "full"               # mặc định: Naota tự làm

_HOST_REDIRECT = ("chatgpt.com", "chat.openai.com", "claude.ai", "claude.com")
_DUOI_REDIRECT = (".chatgpt.com", ".openai.com", ".claude.ai", ".claude.com", ".anthropic.com")
# Ứng dụng chạy trên máy của chủ (Claude Code, Claude Desktop) nhận mã qua localhost (RFC 8252):
# mã chỉ tới được chính máy đang mở trình duyệt, nên kẻ gian ở máy khác không nhặt được.
_HOST_MAY_NHA = ("localhost", "127.0.0.1", "::1")
# Plugin này từng tên `naota-trong-chatgpt` (gói 1.x). Lõi Naota chuyển đường /ext/<tên cũ>/ sang
# đây; trang khám phá OAuth cũng phải nhận tên cũ thì connector đã dán vào ChatGPT mới chạy tiếp.
SLUG_CU = "naota-trong-chatgpt"

_KHOA = threading.Lock()

HUONG_DAN = ("https://github.com/vuongtex/naota-store/blob/main/packs/"
             "naota.gate/docs/HUONG-DAN.md")


# ============================================================
# Đường và địa chỉ
# ============================================================

def _p(ctx, duoi: str = "", slug: str = "") -> str:
    """Đường tuyệt đối của gói trên Naota: /ext/<slug>/<duoi>."""
    return f"/ext/{slug or ctx.slug}/" + duoi


def _slug_goi(ctx, request) -> str:
    """Tên plugin trong ĐƯỜNG mà client vừa gọi: tên cũ nếu nó vẫn dùng địa chỉ của gói 1.x.
    Trả đúng tên đó trong metadata để `resource` khớp địa chỉ client đã lưu."""
    duong = str(request.url.path or "")
    return SLUG_CU if f"/ext/{SLUG_CU}/" in duong + "/" else ctx.slug


def _goc(request) -> str:
    """Gốc công khai của Naota, không có "/" cuối.

    Ưu tiên tên miền riêng đã khai ở trang Thương hiệu: nó ỔN ĐỊNH, còn header proxy thì đổi
    theo đường người ta đi vào. Issuer của OAuth mà đổi giữa chừng là ChatGPT coi như máy khác."""
    try:
        import config as cfgmod
        custom = ((cfgmod.read_settings().get("domain") or {}).get("custom") or "").strip().lower()
    except Exception:
        custom = ""
    if custom:
        return f"https://{custom}"
    import web_security
    return web_security.external_base(
        request.url.scheme, request.url.netloc, request.headers.get("x-forwarded-proto", ""),
        request.headers.get("x-forwarded-host", "")).rstrip("/")


def _co_mat_khau() -> bool:
    try:
        import config as cfgmod
        return bool(cfgmod.auth_enabled())
    except Exception:
        return False


def _co_phien(request) -> bool:
    import config as cfgmod
    return bool(cfgmod.valid_session(request.cookies.get("naota_session", "")))


def metadata_as(ctx, goc: str) -> dict:
    return {
        "issuer": goc,
        "authorization_endpoint": goc + _p(ctx, "oauth/authorize"),
        "token_endpoint": goc + _p(ctx, "oauth/token"),
        "registration_endpoint": goc + _p(ctx, "oauth/register"),
        "revocation_endpoint": goc + _p(ctx, "oauth/revoke"),
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["naota"],
    }


def metadata_pr(ctx, goc: str, slug: str = "") -> dict:
    return {
        "resource": goc + _p(ctx, "mcp", slug),
        "authorization_servers": [goc],
        "scopes_supported": ["naota"],
        "bearer_methods_supported": ["header"],
        "resource_name": "Naota",
    }


def www_authenticate(ctx, goc: str, mo_ta: str = "", slug: str = "") -> str:
    """Câu thách thức trả kèm 401. ChatGPT đọc `resource_metadata` để biết đi đâu đăng nhập.
    `mo_ta` PHẢI là ASCII: header HTTP chỉ nhận Latin-1, viết tiếng Việt vào là trả 500."""
    mo_ta = mo_ta.encode("ascii", "ignore").decode()
    phan = ['Bearer realm="naota"', 'error="invalid_token"']
    if mo_ta:
        phan.append(f'error_description="{mo_ta}"')
    phan.append(f'resource_metadata="{goc}/.well-known/oauth-protected-resource{_p(ctx, "mcp", slug)}"')
    return ", ".join(phan)


# ============================================================
# Cài đặt + kho (thư mục dữ liệu riêng của gói, không nằm trong brain)
# ============================================================

def _doc_json(p, mac_dinh: dict) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return mac_dinh


def _ghi_json(p, d: dict) -> None:
    tam = p.with_suffix(".tmp")
    tam.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(tam, 0o600)
    except OSError:
        pass
    os.replace(tam, p)


def muc_quyen(ctx) -> str:
    m = _doc_json(ctx.data_dir / "cai-dat.json", {}).get("muc_quyen")
    return m if m in MUC_QUYEN else MUC_MAC_DINH


def dat_muc_quyen(ctx, m: str) -> bool:
    if m not in MUC_QUYEN:
        return False
    with _KHOA:
        d = _doc_json(ctx.data_dir / "cai-dat.json", {})
        d["muc_quyen"] = m
        _ghi_json(ctx.data_dir / "cai-dat.json", d)
    return True


def _doc(ctx) -> dict:
    """Kho: client, token, yêu cầu đang chờ Cho phép, mã cấp quyền. Nằm TRÊN ĐĨA chứ không
    trong RAM: Naota nạp lại plugin mỗi khi bật/tắt một plugin bất kỳ, và một yêu cầu đang chờ
    mà mất giữa chừng là người dùng bấm Cho phép rồi nhận câu "quá hạn"."""
    d = _doc_json(ctx.data_dir / "kho.json", {})
    for k in ("clients", "tokens", "yeu_cau", "ma"):
        if not isinstance(d.get(k), dict):
            d[k] = {}
    return d


def _ghi(ctx, d: dict) -> None:
    # Chỉ dọn bản HẾT HẠN. Token đã thu hồi giữ tới hạn của nó: refresh đã xoay mà bị dùng lại
    # là dấu hiệu có người cầm bản sao, và phải còn bản ghi thì mới nhận ra được.
    now = time.time()
    for k in ("tokens", "yeu_cau", "ma"):
        d[k] = {h: t for h, t in d[k].items() if t.get("het", 0) > now}
    _ghi_json(ctx.data_dir / "kho.json", d)


def _bam(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")


def redirect_hop_le(uri: str) -> bool:
    try:
        u = urlparse(uri)
    except Exception:
        return False
    if not u.hostname:
        return False
    h = u.hostname.lower()
    if h in _HOST_MAY_NHA:
        return u.scheme in ("http", "https")
    if u.scheme != "https":
        return False
    return h in _HOST_REDIRECT or any(h.endswith(d) for d in _DUOI_REDIRECT)


def ten_ai(ten: str) -> str:
    """Tên ngắn của AI đang gọi, để nhãn "từ ChatGPT" / "từ Claude" trên khung chat của Naota."""
    t = str(ten or "").strip()
    thap = t.lower()
    if "chatgpt" in thap or "openai" in thap:
        return "ChatGPT"
    if "claude" in thap or "anthropic" in thap:
        return "Claude"
    return t[:40] or "AI"


def _noi(uri: str, q: dict) -> str:
    return uri + ("&" if "?" in uri else "?") + urlencode(q)


# ============================================================
# Luồng OAuth
# ============================================================

def dang_ky_client(ctx, body: dict) -> tuple:
    """(mã HTTP, JSON). RFC 7591, chỉ phần ChatGPT dùng: client công khai, không bí mật."""
    uris = body.get("redirect_uris") if isinstance(body, dict) else None
    if not isinstance(uris, list) or not uris or not all(
            isinstance(u, str) and redirect_hop_le(u) for u in uris):
        return 400, {"error": "invalid_redirect_uri",
                     "error_description": "redirect_uris must be https addresses of ChatGPT or Claude, or localhost"}
    ten = str(body.get("client_name") or "AI")[:120]
    with _KHOA:
        d = _doc(ctx)
        if len(d["clients"]) >= MAX_CLIENT:
            # Bỏ client cũ nhất CHƯA từng nhận token: đó là những lần kết nối bỏ dở.
            dang_dung = {t.get("client") for t in d["tokens"].values()}
            cu = sorted((c for c in d["clients"].values() if c["id"] not in dang_dung),
                        key=lambda c: c.get("tao", 0))
            if not cu:
                return 400, {"error": "invalid_client_metadata",
                             "error_description": "Quá nhiều kết nối. Ngắt bớt trên trang của gói."}
            d["clients"].pop(cu[0]["id"], None)
        cid = "gate-" + secrets.token_urlsafe(16)
        d["clients"][cid] = {"id": cid, "ten": ten, "redirect_uris": uris, "tao": time.time()}
        _ghi(ctx, d)
    return 201, {"client_id": cid, "client_name": ten, "redirect_uris": uris,
                 "token_endpoint_auth_method": "none",
                 "grant_types": ["authorization_code", "refresh_token"],
                 "response_types": ["code"]}


def bat_dau_uy_quyen(ctx, q: dict) -> tuple:
    """Kiểm yêu cầu từ ChatGPT.

    ("trang_loi", câu)   - không tin được redirect_uri nên KHÔNG được chuyển hướng về đó
    ("chuyen", url)      - lỗi báo ngược về ChatGPT theo đúng OAuth
    ("ok", yeu_cau)      - hiện trang Cho phép
    """
    cid = str(q.get("client_id") or "")
    with _KHOA:
        d = _doc(ctx)
        client = d["clients"].get(cid)
        if not client:
            return "trang_loi", "Không nhận ra kết nối này. Mở lại ChatGPT hoặc Claude và bấm kết nối lại."
        ru = str(q.get("redirect_uri") or "")
        if ru not in client["redirect_uris"]:
            return "trang_loi", "Địa chỉ quay về không khớp với lúc đăng ký."
        state = str(q.get("state") or "")
        if q.get("response_type") != "code":
            return "chuyen", _noi(ru, {"error": "unsupported_response_type",
                                       "error_description": "chỉ hỗ trợ code", "state": state})
        if not q.get("code_challenge") or q.get("code_challenge_method") != "S256":
            return "chuyen", _noi(ru, {"error": "invalid_request",
                                       "error_description": "bắt buộc PKCE S256", "state": state})
        yc = {"id": secrets.token_urlsafe(24), "client": cid, "ten": client["ten"],
              "redirect_uri": ru, "state": state, "challenge": str(q["code_challenge"])[:128],
              "het": time.time() + TTL_YEU_CAU}
        while len(d["yeu_cau"]) >= MAX_YEU_CAU:
            d["yeu_cau"].pop(min(d["yeu_cau"], key=lambda k: d["yeu_cau"][k]["het"]), None)
        d["yeu_cau"][yc["id"]] = yc
        _ghi(ctx, d)
    return "ok", yc


def ket_thuc_uy_quyen(ctx, yid: str, cho_phep: bool):
    """Chủ bấm Cho phép / Từ chối. Trả URL quay về ChatGPT, hoặc None nếu yêu cầu hết hạn."""
    with _KHOA:
        d = _doc(ctx)
        yc = d["yeu_cau"].pop(yid or "", None)
        if not yc or yc.get("het", 0) < time.time():
            _ghi(ctx, d)
            return None
        q = {}
        if cho_phep:
            ma = secrets.token_urlsafe(32)
            d["ma"][_bam(ma)] = {"client": yc["client"], "redirect_uri": yc["redirect_uri"],
                                 "challenge": yc["challenge"], "het": time.time() + TTL_MA}
            q["code"] = ma
        else:
            q = {"error": "access_denied", "error_description": "the Naota owner declined"}
        if yc["state"]:
            q["state"] = yc["state"]
        _ghi(ctx, d)
    return _noi(yc["redirect_uri"], q)


def _cap_token(d: dict, cid: str, ho: str) -> dict:
    """Một cặp access + refresh. `ho` gom các thế hệ refresh của cùng một lần cho phép."""
    now = time.time()
    at, rt = secrets.token_urlsafe(32), secrets.token_urlsafe(40)
    d["tokens"][_bam(at)] = {"loai": "access", "client": cid, "ho": ho, "het": now + TTL_ACCESS}
    d["tokens"][_bam(rt)] = {"loai": "refresh", "client": cid, "ho": ho, "het": now + TTL_REFRESH}
    return {"access_token": at, "token_type": "Bearer", "expires_in": TTL_ACCESS,
            "refresh_token": rt, "scope": "naota"}


def doi_token(ctx, f: dict) -> tuple:
    """(mã HTTP, JSON) cho POST token. Client công khai: không có client_secret, chỉ PKCE."""
    loai = f.get("grant_type")
    cid = str(f.get("client_id") or "")
    if loai == "authorization_code":
        ma, ver = str(f.get("code") or ""), str(f.get("code_verifier") or "")
        if not ma or not ver or not cid:
            return 400, {"error": "invalid_request"}
        with _KHOA:
            d = _doc(ctx)
            rec = d["ma"].pop(_bam(ma), None)       # MỘT lần, kể cả khi các bước sau hỏng
            _ghi(ctx, d)
            if not rec or rec["client"] != cid or rec.get("het", 0) < time.time():
                return 400, {"error": "invalid_grant"}
            ru = f.get("redirect_uri")
            if ru and ru != rec["redirect_uri"]:
                return 400, {"error": "invalid_grant", "error_description": "redirect_uri không khớp"}
            if not secrets.compare_digest(_s256(ver), rec["challenge"]):
                return 400, {"error": "invalid_grant", "error_description": "PKCE không khớp"}
            if cid not in d["clients"]:
                return 400, {"error": "invalid_client"}
            out = _cap_token(d, cid, secrets.token_urlsafe(12))
            _ghi(ctx, d)
        return 200, out
    if loai == "refresh_token":
        rt = str(f.get("refresh_token") or "")
        if not rt or not cid:
            return 400, {"error": "invalid_request"}
        with _KHOA:
            d = _doc(ctx)
            rec = d["tokens"].get(_bam(rt))
            if not rec or rec.get("loai") != "refresh" or rec.get("client") != cid:
                return 400, {"error": "invalid_grant"}
            if rec.get("thu_hoi"):
                # Refresh ĐÃ XOAY mà còn bị dùng lại: có người cầm bản sao. Thu hồi cả họ, bắt
                # cho phép lại, thay vì để hai bên cùng giữ một kết nối.
                for t in d["tokens"].values():
                    if t.get("ho") == rec.get("ho"):
                        t["thu_hoi"] = True
                _ghi(ctx, d)
                return 400, {"error": "invalid_grant", "error_description": "refresh đã dùng rồi"}
            if rec["het"] < time.time():
                return 400, {"error": "invalid_grant"}
            rec["thu_hoi"] = True
            out = _cap_token(d, cid, rec["ho"])
            _ghi(ctx, d)
        return 200, out
    return 400, {"error": "unsupported_grant_type"}


def kiem_token(ctx, raw: str):
    """Bản ghi của một access token còn hạn, hoặc None."""
    if not raw:
        return None
    rec = _doc(ctx)["tokens"].get(_bam(raw))
    if not rec or rec.get("loai") != "access" or rec.get("thu_hoi") or rec["het"] < time.time():
        return None
    return rec


def ten_client(ctx, rec) -> str:
    """Tên AI của một token (theo client đã đăng ký), cho nhãn nguồn trên khung chat."""
    c = _doc(ctx)["clients"].get(str((rec or {}).get("client") or "")) or {}
    return ten_ai(c.get("ten") or "")


def thu_hoi(ctx, raw: str) -> None:
    """RFC 7009: thu hồi một token và cả họ của nó. Không nói token có tồn tại hay không."""
    if not raw:
        return
    with _KHOA:
        d = _doc(ctx)
        rec = d["tokens"].get(_bam(raw))
        if not rec:
            return
        for t in d["tokens"].values():
            if t.get("ho") == rec.get("ho"):
                t["thu_hoi"] = True
        _ghi(ctx, d)


def ngat_tat_ca(ctx) -> int:
    """Nút "Ngắt mọi kết nối": xoá sạch client, token, yêu cầu, mã. Trả số client đã xoá."""
    with _KHOA:
        n = len(_doc(ctx)["clients"])
        _ghi(ctx, {"clients": {}, "tokens": {}, "yeu_cau": {}, "ma": {}})
    return n


def so_ket_noi(ctx) -> int:
    """Số lần cho phép còn hiệu lực (mỗi họ refresh còn sống là một)."""
    now = time.time()
    return len({t.get("ho") for t in _doc(ctx)["tokens"].values()
                if t.get("loai") == "refresh" and not t.get("thu_hoi") and t.get("het", 0) > now})


# ============================================================
# HTML (chữ tối thiểu 16px, đọc trên điện thoại)
# ============================================================

_CSS = """
:root { color-scheme: light dark; --nen:#f6f5f2; --the:#fff; --chu:#1d1d1f; --phu:#6b6b70;
        --vien:#dcdad4; --nhan:#c2410c; --nhan-chu:#fff; --loi:#dc2626; --tot:#15803d; }
@media (prefers-color-scheme: dark) {
  :root { --nen:#141414; --the:#1f1f1f; --chu:#eee; --phu:#a3a3a8; --vien:#3a3a3a;
          --tot:#4ade80; --loi:#f87171; }
}
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
       background:var(--nen); color:var(--chu); font-size:17px; line-height:1.5;
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; padding:16px; }
.the { background:var(--the); border:1px solid var(--vien); border-radius:16px; padding:28px 24px;
       width:100%; max-width:480px; }
h1 { font-size:22px; margin:0 0 8px; }
h2 { font-size:18px; margin:22px 0 8px; }
p { margin:0 0 14px; }
.phu { color:var(--phu); font-size:16px; }
ul { margin:0 0 18px; padding-left:20px; }
li { margin-bottom:6px; }
label { display:block; font-size:16px; margin:12px 0 6px; }
input, select { width:100%; font-size:17px; padding:12px; border-radius:10px;
                border:1px solid var(--vien); background:transparent; color:inherit; }
button { width:100%; font-size:17px; padding:13px; border-radius:10px; border:0; cursor:pointer;
         margin-top:12px; }
.chinh { background:var(--nhan); color:var(--nhan-chu); }
.phu-nut { background:transparent; color:var(--chu); border:1px solid var(--vien); }
.loi { color:var(--loi); font-size:16px; margin-top:10px; }
.tot { color:var(--tot); font-size:16px; margin-top:10px; }
code { font-size:16px; word-break:break-all; }
a { color:var(--nhan); }
.hop { display:flex; gap:8px; align-items:stretch; }
.hop input { flex:1; }
.hop button { width:auto; margin:0; padding:0 16px; }
"""


def _trang(than: str, status: int = 200):
    # `same-origin`, KHÔNG phải `no-referrer`. URL trang Cho phép mang state và code_challenge
    # nên không được rò sang trang khác qua Referer, và cả hai giá trị đều chặn được điều đó.
    # Nhưng `no-referrer` còn làm trình duyệt gửi `Origin: null` khi nộp form, hàng rào CSRF
    # của Naota coi "null" là nguồn lạ và chặn nút Cho phép (đo trên Chromium thật 23/09).
    from starlette.responses import HTMLResponse
    return HTMLResponse(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="same-origin"><title>Naota Gate</title>'
        f'<style>{_CSS}</style></head><body><div class="the">{than}</div></body></html>',
        status_code=status,
        headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                 "Content-Security-Policy": "frame-ancestors 'none'"})


_MO_TA_MUC = {
    "full": "Toàn quyền: đọc dữ liệu, nhắn vào khung chat để Naota làm, và làm việc thật (gửi tin, tạo đơn, đăng bài...)",
    "auto": "Tự làm có giới hạn: đọc dữ liệu và viết nháp, không làm việc ra bên ngoài",
    "suggest": "Chỉ đọc và gợi ý: không ghi file, không làm việc ra bên ngoài",
}


def _trang_dang_nhap():
    """Trình duyệt chưa vào dashboard: đăng nhập NGAY TẠI ĐÂY rồi tải lại, không bắt đi vòng."""
    return _trang("""
<h1>Đăng nhập Naota</h1>
<p class="phu">Một AI (ChatGPT, Claude...) đang xin quyền dùng Naota của bạn. Đăng nhập để xem và quyết định.</p>
<form id="f">
  <label for="u">Tài khoản</label><input id="u" name="username" autocomplete="username" required>
  <label for="p">Mật khẩu</label>
  <input id="p" name="password" type="password" autocomplete="current-password" required>
  <div id="o" style="display:none">
    <label for="c">Mã xác thực 2 lớp</label>
    <input id="c" name="code" inputmode="numeric" autocomplete="one-time-code">
  </div>
  <div id="e" class="loi" role="alert"></div>
  <button class="chinh" type="submit">Đăng nhập</button>
</form>
<script>
document.getElementById("f").onsubmit = async (ev) => {
  ev.preventDefault();
  const e = document.getElementById("e"); e.textContent = "";
  let r, d = {};
  try {
    r = await fetch("/auth/login", {method: "POST", body: new FormData(ev.target),
                                    credentials: "same-origin"});
    d = await r.json();
  } catch (x) { e.textContent = "Không gọi được Naota. Thử lại."; return; }
  if (d.ok) { location.reload(); return; }
  if (d.needs_2fa) document.getElementById("o").style.display = "";
  e.textContent = d.error || "Đăng nhập không thành công.";
};
</script>""")


def _trang_dong_y(ctx, yc: dict):
    muc = muc_quyen(ctx)
    host = html.escape(urlparse(yc["redirect_uri"]).hostname or "")
    ai = html.escape(ten_ai(yc["ten"]))
    return _trang(f"""
<h1>Cho phép {ai} dùng Naota?</h1>
<p><b>{html.escape(yc["ten"])}</b> trên <code>{host}</code> muốn gọi công cụ của Naota.</p>
<ul>
  <li>Dùng mọi kết nối bạn đã bật trong Naota (bán hàng, quảng cáo, lịch, Zalo...)</li>
  <li>Đọc hội thoại của Naota, và ở mức Toàn quyền thì nhắn vào khung chat để Naota làm tiếp</li>
  <li>Đọc và ghi trong brain đang mở, tạo việc và nhắc lịch</li>
  <li>Mức quyền: {html.escape(_MO_TA_MUC.get(muc, muc))}</li>
</ul>
<p class="phu">Đổi mức quyền hoặc ngắt kết nối bất cứ lúc nào trên trang của gói
(trang Plugin, thẻ Naota Gate, nút Mở trang).</p>
<form method="post" action="{_p(ctx, "oauth/authorize")}">
  <input type="hidden" name="yeu_cau" value="{html.escape(yc["id"])}">
  <button class="chinh" name="hanh_dong" value="cho_phep" type="submit">Cho phép</button>
  <button class="phu-nut" name="hanh_dong" value="tu_choi" type="submit">Từ chối</button>
</form>""")


def _trang_loi(cau: str, status: int = 400):
    return _trang(f"<h1>Không kết nối được</h1><p>{html.escape(cau)}</p>", status)


def _trang_cai_dat(ctx, request):
    goc = _goc(request)
    url = goc + _p(ctx, "mcp")
    muc = muc_quyen(ctx)
    https = goc.startswith("https://")
    if not _co_mat_khau():
        than_chinh = ('<p class="loi">Naota chưa có mật khẩu quản trị. Bước Cho phép dựa vào '
                      'đăng nhập, nên cửa này đang đóng. Đặt mật khẩu ở Cài đặt rồi quay lại.</p>')
    else:
        chon = "".join(
            f'<option value="{m}"{" selected" if m == muc else ""}>{html.escape(_MO_TA_MUC[m])}</option>'
            for m in MUC_QUYEN)
        canh_bao = "" if https else (
            '<p class="loi">ChatGPT và Claude chỉ nhận địa chỉ https. Gắn tên miền riêng cho Naota '
            '(Cài đặt, mục Giọng nói, thương hiệu và truy cập) rồi tải lại trang này.</p>')
        than_chinh = f"""
<h2>1. Dán địa chỉ này vào ChatGPT hoặc Claude</h2>
<p class="phu"><b>ChatGPT:</b> Settings, Apps &amp; Connectors, bật Developer mode, rồi Create. Ô "MCP Server URL", xác thực OAuth.</p>
<p class="phu"><b>Claude:</b> Settings, Connectors, Add custom connector. Dán địa chỉ rồi bấm Add.</p>
<div class="hop"><input id="url" readonly value="{html.escape(url)}">
<button class="phu-nut" id="chep" type="button">Chép</button></div>
{canh_bao}
<h2>2. Mức quyền của AI bên ngoài</h2>
<select id="muc">{chon}</select>
<div id="tb" class="phu" role="status"></div>
<h2>3. Kết nối đang dùng: <span id="so">{so_ket_noi(ctx)}</span></h2>
<button class="phu-nut" id="ngat" type="button">Ngắt mọi kết nối</button>
<script>
const tb = document.getElementById("tb");
document.getElementById("chep").onclick = async (ev) => {{
  const o = document.getElementById("url");
  try {{ await navigator.clipboard.writeText(o.value); }}
  catch (x) {{ o.select(); document.execCommand("copy"); }}
  ev.target.textContent = "Đã chép";
  setTimeout(() => ev.target.textContent = "Chép", 1500);
}};
async function goi(duong, body) {{
  const r = await fetch(duong, {{method: "POST", credentials: "same-origin",
    headers: {{"Content-Type": "application/json"}}, body: JSON.stringify(body || {{}})}});
  const d = await r.json().catch(() => ({{}}));
  if (!r.ok || !d.ok) throw new Error(d.error || ("Lỗi " + r.status));
  return d;
}}
document.getElementById("muc").onchange = async (ev) => {{
  tb.className = "phu"; tb.textContent = "Đang lưu...";
  try {{ await goi({json.dumps(_p(ctx, "cai-dat"))}, {{muc_quyen: ev.target.value}});
         tb.className = "tot"; tb.textContent = "Đã lưu. Có hiệu lực từ lượt gọi kế tiếp."; }}
  catch (x) {{ tb.className = "loi"; tb.textContent = x.message; }}
}};
document.getElementById("ngat").onclick = async () => {{
  if (!confirm("Ngắt mọi kết nối? Muốn dùng lại phải kết nối lại từ ChatGPT hoặc Claude.")) return;
  try {{ await goi({json.dumps(_p(ctx, "ngat"))});
         document.getElementById("so").textContent = "0";
         tb.className = "tot"; tb.textContent = "Đã ngắt mọi kết nối."; }}
  catch (x) {{ tb.className = "loi"; tb.textContent = x.message; }}
}};
</script>"""
    return _trang(f"""
<h1>Naota Gate</h1>
<p class="phu">Cổng cho ChatGPT, Claude và AI khác làm việc cùng Naota. AI đó đọc hội thoại của Naota
và nhắn vào khung chat như bạn gõ, nên bạn xem được tiến độ ngay trên Naota.
<a href="{HUONG_DAN}" target="_blank" rel="noopener">Hướng dẫn từng bước</a></p>
{than_chinh}""")


# ============================================================
# Handler HTTP
# ============================================================

def _tat():
    # 404 chứ không phải 403: chưa có mật khẩu nghĩa là cửa này KHÔNG tồn tại, không quảng bá gì.
    from starlette.responses import JSONResponse
    return JSONResponse({"error": "not_found"}, status_code=404)


def _json(payload, status=200):
    from starlette.responses import JSONResponse
    return JSONResponse(payload, status_code=status,
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


async def _doc_form(request) -> dict:
    """Thân POST dạng form hoặc JSON. OAuth chuẩn là form; vài client gửi JSON."""
    loai = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in loai:
            d = await request.json()
            return d if isinstance(d, dict) else {}
        return dict(await request.form())
    except Exception:
        return {}


def register(ctx):
    # ---- khám phá (bắt buộc nằm ở gốc tên miền, nên đi qua register_well_known) ----
    def wk_pr(request, ctx):
        if not _co_mat_khau():
            return _tat()
        duoi = request.url.path[len("/.well-known/oauth-protected-resource"):].rstrip("/")
        if duoi not in ("", _p(ctx, "mcp"), _p(ctx, "mcp", SLUG_CU)):
            return _tat()
        return _json(metadata_pr(ctx, _goc(request), SLUG_CU if duoi == _p(ctx, "mcp", SLUG_CU) else ""))

    def wk_as(request, ctx):
        if not _co_mat_khau():
            return _tat()
        return _json(metadata_as(ctx, _goc(request)))

    ctx.register_well_known("oauth-protected-resource", wk_pr)
    ctx.register_well_known("oauth-authorization-server", wk_as)
    ctx.register_well_known("openid-configuration", wk_as)

    # ---- đăng ký client (RFC 7591) ----
    async def dang_ky(request, ctx):
        if not _co_mat_khau():
            return _tat()
        try:
            body = await request.json()
        except Exception:
            body = {}
        ma, d = dang_ky_client(ctx, body if isinstance(body, dict) else {})
        return _json(d, ma)

    ctx.register_http("oauth/register", dang_ky, methods=("POST",), public=True, no_cookie=True)

    # ---- trang Cho phép ----
    # GET công khai nhưng GIỮ cookie: chưa đăng nhập thì hiện ô đăng nhập ngay tại đó.
    # POST KHÔNG công khai: lõi Naota tự đòi phiên trình duyệt thật và chặn CSRF.
    def uy_quyen(request, ctx):
        from starlette.responses import RedirectResponse
        if not _co_mat_khau():
            return _trang_loi("Naota chưa có mật khẩu quản trị nên chưa kết nối được AI bên ngoài.", 404)
        kq, gia_tri = bat_dau_uy_quyen(ctx, dict(request.query_params))
        if kq == "trang_loi":
            return _trang_loi(gia_tri)
        if kq == "chuyen":
            return RedirectResponse(gia_tri, status_code=302)
        if not _co_phien(request):
            return _trang_dang_nhap()
        return _trang_dong_y(ctx, gia_tri)

    async def uy_quyen_xac_nhan(request, ctx):
        from starlette.responses import RedirectResponse
        if not _co_mat_khau():
            return _trang_loi("Naota chưa có mật khẩu quản trị.", 404)
        f = await _doc_form(request)
        url = ket_thuc_uy_quyen(ctx, str(f.get("yeu_cau") or ""), f.get("hanh_dong") == "cho_phep")
        if not url:
            return _trang_loi("Yêu cầu này đã quá hạn. Mở lại ChatGPT hoặc Claude và kết nối lại.")
        return RedirectResponse(url, status_code=302)

    ctx.register_http("oauth/authorize", uy_quyen, public=True)
    ctx.register_http("oauth/authorize", uy_quyen_xac_nhan, methods=("POST",))

    # ---- đổi token + thu hồi ----
    async def token(request, ctx):
        if not _co_mat_khau():
            return _tat()
        ma, d = doi_token(ctx, await _doc_form(request))
        return _json(d, ma)

    async def thu_hoi_token(request, ctx):
        if not _co_mat_khau():
            return _tat()
        thu_hoi(ctx, str((await _doc_form(request)).get("token") or ""))
        return _json({})

    ctx.register_http("oauth/token", token, methods=("POST",), public=True, no_cookie=True)
    ctx.register_http("oauth/revoke", thu_hoi_token, methods=("POST",), public=True, no_cookie=True)

    # ---- MCP ----
    async def mcp(request, ctx):
        if not _co_mat_khau():
            return _tat()
        raw = str(request.headers.get("authorization") or "")
        raw = raw[7:].strip() if raw[:7].lower() == "bearer " else ""
        rec = kiem_token(ctx, raw)
        if not rec:
            from starlette.responses import JSONResponse
            return JSONResponse(
                {"error": "unauthorized", "error_description": "reconnect from ChatGPT or Claude"},
                status_code=401,
                headers={"WWW-Authenticate": www_authenticate(
                    ctx, _goc(request), "missing, invalid or expired token", _slug_goi(ctx, request))})
        import mcp_hub
        # Mức quyền đọc TỪNG LƯỢT, không đóng băng vào token: chủ hạ quyền là có hiệu lực ngay.
        # include_ambient=False: tool native của tài khoản Claude không liên quan ở đây.
        # raw_vault=None: brain do Naota tự suy (brain đang mở), không nhận header từ ngoài.
        # gate: bốn tool chat của lõi (tìm, đọc, gửi vào hội thoại, đọc kết quả), kèm tên AI đang gọi
        # để khung chat của Naota ghi "từ ChatGPT" / "từ Claude".
        return await mcp_hub.tra_loi_jsonrpc(request, muc_quyen(ctx), include_plugins=True,
                                             include_ambient=False, raw_vault=None,
                                             gate={"source": ten_client(ctx, rec)})

    def mcp_khac(request, ctx):
        # Streamable HTTP không trạng thái: không có luồng do máy chủ mở, không có phiên để xoá.
        if not _co_mat_khau():
            return _tat()
        from starlette.responses import JSONResponse
        return JSONResponse({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32000, "message": "Chỉ nhận POST."}},
                            status_code=405, headers={"Allow": "POST"})

    ctx.register_http("mcp", mcp, methods=("POST",), public=True, no_cookie=True)
    ctx.register_http("mcp", mcp_khac, methods=("GET", "DELETE"), public=True, no_cookie=True)

    # ---- trang của gói (lõi Naota đòi phiên trình duyệt thật cho cả ba) ----
    ctx.register_http("", lambda request, ctx: _trang_cai_dat(ctx, request))

    async def cai_dat(request, ctx):
        f = await _doc_form(request)
        if not dat_muc_quyen(ctx, str(f.get("muc_quyen") or "")):
            return _json({"ok": False, "error": "Mức quyền không hợp lệ."}, 400)
        return _json({"ok": True, "muc_quyen": muc_quyen(ctx)})

    ctx.register_http("cai-dat", cai_dat, methods=("POST",))
    ctx.register_http("ngat", lambda request, ctx: _json({"ok": True, "da_ngat": ngat_tat_ca(ctx)}),
                      methods=("POST",))
