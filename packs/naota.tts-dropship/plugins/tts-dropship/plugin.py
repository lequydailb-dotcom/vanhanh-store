"""Plugin gói: bán dropship trên sàn TTS (dropship.thitruongsi.com).

Sàn TTS không có MCP server và không phát hành API key công khai, nên gói này gọi THẲNG
api.thitruongsi.com bằng chính token phiên đăng nhập của người dùng, lấy từ Local Storage của
trình duyệt và cất trong kết nối "tts-dropship" (mã hoá bởi secrets_store). Kết nối đó là một
connector ẢO: nó không có URL MCP để mở phiên, nó chỉ giữ token cho plugin này dùng, giống cách
Meta Ads Graph API đang làm.

Bản 1.1.0: đối chiếu lại TỪNG đường với sàn thật
-----------------------------------------------
Bản 1.0.x viết theo một bản khảo sát chỉ bắt được tên trường, không bắt được thân request. Tìm
hàng và đọc đơn từng hỏng, nên bản này được viết lại bằng hai
nguồn sự thật: lược đồ GraphQL sàn tự khai (`__schema`, sàn để mở) và mã web của chính
dropship.thitruongsi.com (tệp app.js mà trình duyệt tải về). Những điều đã sửa, để người đọc
sau biết vì sao mã trông thế này:

- Truy vấn GraphQL chọn trường sàn không có. Phần tự sửa cũ chỉ biết một dạng lỗi (lớp bọc) nên
  không cứu được. Nay nó soi lược đồ và BỎ trường không còn, xem `_tu_sua`.
- Từ khoá có dấu hoặc có dấu cách mà không mã hoá thì sàn chết với câu lỗi RỖNG. Nay mã hoá
  đầy đủ như `qs.stringify` của web sàn.
- Trên sàn này `city` là TỈNH/THÀNH còn `province` là QUẬN/HUYỆN (form tạo khách của web sàn
  ghi đúng như vậy). Bản cũ gửi ngược. Khách mới còn phải gửi địa chỉ trong mảng `addresses`.
- Bộ tách địa chỉ của sàn đọc "Quận 1" thành "Q. 12" trong một phép thử thật. Nên gói tự đối
  chiếu địa chỉ với danh mục địa giới của chính sàn trước khi cho tạo khách, xem `_khop_dia_chi`.
- Giỏ hàng nhận `{items: [{variant_id, quantity, dropship_selling_price, note}]}`. Báo giá ship
  nhận `destination: {customer_address_id}`. Đơn nhận `payment_method: "cod"` chữ thường và
  `shipping_lines` ở dạng riêng chứ không phải nguyên mục báo giá, xem `_rate_sang_line`. Sàn
  trả đơn vừa tạo ở `order`, không phải `data.order`.
- Sàn có địa chỉ gia hạn token thật: GET /v1/user/api/token/refresh?refresh_token=... Web sàn
  gọi nó mỗi khi gặp 401. Gói nay cũng vậy, nên dán @refreshToken một lần là hết cảnh 3 ngày
  lại phải dán token.
- GraphQL báo token hết hạn bằng `errors[0].message == "401"` với HTTP 200, không phải mã 401.

Bốn điều vẫn quyết định hình dạng của file này
---------------------------------------------
1. **Cờ `dropship=true` phải đi kèm gần như mọi request.** Thiếu nó sàn trả dữ liệu của tài
   khoản mua sỉ thường, tức là số liệu SAI mà trông vẫn đúng. Cờ này đặt ở lớp client (`_api`).

2. **Đây là API nội bộ, không có tài liệu chính thức.** Tài liệu truy vấn nằm trong
   `graphql.json` như DỮ LIỆU và sửa được lúc chạy, mọi tool ghi nhận `raw_body` để đè nguyên
   thân request khi sàn đổi hình dạng.

3. **Đơn đã tạo thì KHÔNG SỬA ĐƯỢC.** Nên `tts_create_order`, `tts_cancel_order` và
   `tts_order_action` bắt xác nhận hai bước: lần gọi đầu chỉ dựng bản xem trước và KHÔNG chạm
   mạng ghi, phải gọi lại với `confirm=true` mới thực thi. Chốt nằm trong MÃ.

4. **Lệnh ghi KHÔNG BAO GIỜ tự thử lại khi sàn lỗi 5xx hay đứt mạng giữa chừng.** Một lệnh tạo
   đơn gửi đi rồi mới đứt thì có thể đơn đã nằm trên sàn; thử lại là ra hai đơn thật. Chỉ lệnh
   đọc mới được lặp.

Cố ý KHÔNG có trong gói này
---------------------------
- **Rút tiền.** Gói chỉ đọc biểu phí rút; không có đường thực thi, kể cả ở mức Toàn quyền.
- **Thêm/xoá tài khoản ngân hàng.** Chỉ đọc danh sách.
- **Tìm sản phẩm bằng ảnh, đồng bộ TikTok Shop, tải ảnh vận đơn.** Chưa xác minh được hình dạng
  thân request, viết đại ra một tool gọi sai thì tệ hơn là không có tool.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

CONNECTOR_ID = "tts-dropship"
API = "https://api.thitruongsi.com"
WEB = "https://dropship.thitruongsi.com"
# Địa chỉ gia hạn token, lấy nguyên văn trong mã web của sàn (hàm refreshToken trong app.js).
DUONG_GIA_HAN = API + "/v1/user/api/token/refresh"

# Tự đặt hàng đợi: sàn chưa công bố giới hạn nào, nên giữ khoảng 4 request mỗi giây và lùi dần
# khi bị 429/5xx. Đây là phép lịch sự với một API nội bộ, và cũng là cách không bị chặn IP.
_MIN_INTERVAL = 0.25
_RETRY_STATUS = (429, 500, 502, 503, 504)
_MAX_RETRY = 3

# Token còn dưới ngần này thì thử gia hạn trước khi dùng (giây).
_REFRESH_TRUOC = 24 * 3600

# Trần kích thước một câu trả lời. Sàn trả nguyên danh sách sản phẩm, đủ để nuốt trọn cửa sổ
# ngữ cảnh của model nếu không chặn.
_TRAN_KY_TU = 40000

# Hình dạng một JWT: ba khối base64url nối bằng dấu chấm, khối đầu luôn bắt đầu
# bằng "eyJ" (chính là '{"' đã mã hoá).
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*")

_nhip = {"lan_cuoi": 0.0}
# Token vừa gia hạn trong phiên chạy này. Sàn có thể xoay vòng refresh token, nên hai lệnh gọi
# gần nhau mà cùng đi gia hạn thì lệnh sau cầm refresh token đã bị huỷ. Giữ token mới vài phút
# là đủ để lệnh sau dùng lại thay vì đi xin lần nữa.
_vua_gia_han = {"tok": "", "luc": 0.0}


# ============================================================
# Kết nối và token
# ============================================================
def _conn():
    """Kết nối tts-dropship đang bật (ưu tiên cái đặt mặc định). None nếu chưa có."""
    try:
        import mcp_store
    except Exception:
        return None
    co = [c for c in mcp_store.list_connections()
          if c.get("connector_id") == CONNECTOR_ID and c.get("enabled", True)]
    if not co:
        return None
    for c in co:
        if c.get("is_default"):
            return c
    return co[0]


def _secrets(conn):
    try:
        import mcp_store
    except Exception:
        return {}
    return mcp_store.connection_secrets(conn["id"]) or {}


def _jwt_exp(tok: str) -> int:
    """Hạn dùng ghi trong JWT, kiểu Unix. 0 nếu không đọc được.

    KHÔNG xác thực chữ ký, và không cần: đây chỉ để biết khi nào nên đi xin token mới."""
    try:
        than = tok.split(".")[1]
        than += "=" * (-len(than) % 4)
        return int(json.loads(base64.urlsafe_b64decode(than.encode())).get("exp") or 0)
    except Exception:
        return 0


def _con_lai(tok: str) -> int:
    exp = _jwt_exp(tok)
    return int(exp - time.time()) if exp else -1


def _het_han_noi_gi(con_lai: int) -> str:
    if con_lai == -1:
        return ("Token không đọc được hạn dùng. Có thể bạn dán thiếu hoặc dán nhầm ô. Vào trang "
                "Kết nối > TTS Dropship > Sửa, rồi dán lại nguyên văn giá trị @publicToken.")
    return (f"Token TTS đã hết hạn {abs(con_lai) // 3600} giờ trước và không tự gia hạn được. "
            f"Mở {WEB}, đăng nhập lại, bấm F12 > Console, chạy "
            "copy(localStorage.getItem('@publicToken')) rồi dán vào trang Kết nối > TTS "
            "Dropship > Sửa. Làm tương tự với @refreshToken để lần sau Naota tự gia hạn.")


async def _gia_han(conn, sec):
    """Đổi refresh token lấy access token mới. (token_moi, lý_do_thất_bại).

    Dùng đúng đường web của sàn đang dùng: GET kèm `refresh_token` trên query string, sàn trả
    `{data: {access_token, ...}}`. Ô `refresh_url` của kết nối vẫn còn để đè địa chỉ này nếu
    sàn đổi, nhưng để trống là dùng địa chỉ mặc định."""
    if _vua_gia_han["tok"] and time.time() - _vua_gia_han["luc"] < 300:
        return _vua_gia_han["tok"], ""
    url = (sec.get("refresh_url") or "").strip() or DUONG_GIA_HAN
    rt = (sec.get("refresh_token") or "").strip()
    if not rt:
        return None, "chưa dán @refreshToken nên không có gì để đổi"
    if not url.lower().startswith("https://"):
        return None, "'Địa chỉ gia hạn token' phải là https"
    if rt.startswith("eyJ") and 0 <= _con_lai(rt) <= 0:
        return None, "refresh token cũng đã hết hạn, phải lấy lại cả hai token"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, params={"refresh_token": rt},
                            headers={"accept": "application/json", "origin": WEB,
                                     "referer": WEB + "/"})
        d = r.json() if r.content else {}
    except Exception as e:
        return None, f"{type(e).__name__} khi gọi địa chỉ gia hạn"
    if r.status_code >= 400:
        return None, (f"sàn từ chối refresh token (HTTP {r.status_code}). Refresh token có thể "
                      "đã hết hạn hoặc bạn đã đăng xuất trên trình duyệt, nên lấy lại cả hai token")
    if not isinstance(d, dict):
        return None, "địa chỉ gia hạn trả về thứ không phải JSON object"
    tang = d.get("data") if isinstance(d.get("data"), dict) else d
    moi = ""
    for k in ("access_token", "accessToken", "token", "publicToken", "public_token"):
        if isinstance(tang.get(k), str) and tang[k].count(".") == 2:
            moi = tang[k].strip()
            break
    if not moi:
        return None, "không tìm thấy access token trong câu trả lời của địa chỉ gia hạn"
    rt_moi = ""
    for k in ("refresh_token", "refreshToken"):
        if isinstance(tang.get(k), str) and tang[k].strip():
            rt_moi = tang[k].strip()
            break
    _vua_gia_han.update(tok=moi, luc=time.time())
    try:
        import mcp_store
        patch = {"access_token": moi}
        if rt_moi and rt_moi != rt:
            patch["refresh_token"] = rt_moi
        mcp_store.update_connection(conn["id"], {"fields": patch})
    except Exception as e:
        # Gia hạn được nhưng không ghi lại được thì vẫn dùng token mới cho lượt này; chỉ là lượt
        # sau phải gia hạn lại. Đổi một phiền toái nhỏ lấy việc không làm hỏng bản ghi kết nối.
        return moi, f"lấy được token mới nhưng chưa lưu lại được ({type(e).__name__})"
    return moi, ""


async def _token(ep_gia_han=False):
    """(token, lỗi). Kiểm hạn trước, tự gia hạn khi sắp hết, rồi mới trả về.

    `ep_gia_han=True` là khi sàn vừa từ chối token dù hạn ghi trên token còn dài (người dùng
    đăng xuất, đổi mật khẩu): lúc đó đi gia hạn ngay chứ không tin con số exp."""
    conn = _conn()
    if not conn:
        return None, ("Chưa kết nối TTS Dropship. Vào trang Kết nối, chọn 'TTS Dropship "
                      "(thitruongsi.com)', làm theo hướng dẫn lấy token từ trình duyệt rồi bấm "
                      "Kết nối. Sau đó gọi lại tool này.")
    sec = _secrets(conn)
    tok = (sec.get("access_token") or "").strip()
    if not tok:
        return None, ("Kết nối TTS Dropship chưa có token. Vào trang Kết nối > TTS Dropship > "
                      "Sửa và dán giá trị @publicToken.")
    if _vua_gia_han["tok"] and time.time() - _vua_gia_han["luc"] < 300 and not ep_gia_han:
        return _vua_gia_han["tok"], None
    con_lai = _con_lai(tok)
    if con_lai > _REFRESH_TRUOC and not ep_gia_han:
        return tok, None
    moi, vi_sao = await _gia_han(conn, sec)
    if moi:
        return moi, None
    if ep_gia_han:
        return None, ("Sàn TTS từ chối token và Naota không tự gia hạn được (%s). %s"
                      % (vi_sao, _het_han_noi_gi(con_lai if con_lai <= 0 else 0)))
    if con_lai <= 0:
        return None, _het_han_noi_gi(con_lai) + f" (tự gia hạn không chạy: {vi_sao})"
    # Còn hạn nhưng sắp hết: vẫn chạy bình thường, cảnh báo đi kèm kết quả chứ không chặn.
    return tok, None


def _canh_bao_han():
    """Câu cảnh báo kèm vào kết quả khi token sắp hết hạn mà không tự gia hạn được."""
    conn = _conn()
    if not conn:
        return ""
    sec = _secrets(conn)
    tok = (sec.get("access_token") or "").strip()
    if not tok or _vua_gia_han["tok"]:
        return ""
    con_lai = _con_lai(tok)
    if 0 < con_lai <= _REFRESH_TRUOC and not (sec.get("refresh_token") or "").strip():
        return (f"Token TTS còn khoảng {max(1, con_lai // 3600)} giờ là hết hạn và kết nối chưa "
                "có @refreshToken nên Naota không tự gia hạn được. Vào trang Kết nối > TTS "
                "Dropship > Sửa, dán thêm @refreshToken để khỏi phải làm lại mỗi 3 ngày.")
    return ""


def _check():
    """check_fn của mọi tool: chặn sớm khi chưa kết nối. Không chạm mạng."""
    conn = _conn()
    if not conn:
        return ("Chưa kết nối TTS Dropship. Vào trang Kết nối, chọn 'TTS Dropship "
                "(thitruongsi.com)' và làm theo hướng dẫn lấy token từ trình duyệt.")
    if not (_secrets(conn).get("access_token") or "").strip():
        return "Kết nối TTS Dropship chưa có token. Vào trang Kết nối > TTS Dropship > Sửa."
    return None


# ============================================================
# Lớp HTTP
# ============================================================
async def _nhip_do():
    """Giãn các request cho đủ thưa. Không dùng Lock để không dính chuyện lock buộc vào một
    event loop khác với loop đang chạy; sai lệch vài mili giây ở đây không đổi điều gì."""
    import asyncio
    cho = _nhip["lan_cuoi"] + _MIN_INTERVAL - time.monotonic()
    if cho > 0:
        await asyncio.sleep(cho)
    _nhip["lan_cuoi"] = time.monotonic()


def _che(s: str) -> str:
    """Bỏ token ra khỏi một câu lỗi rồi cắt ngắn. Che trước, cắt sau: cắt trước thì một token
    bị cắt đôi vẫn lộ nửa đầu."""
    s = _JWT_RE.sub("<token>", str(s or ""))
    return s[:400]


def _gql_401(d) -> bool:
    """GraphQL của sàn báo token hỏng bằng câu lỗi "401" trong thân, HTTP vẫn là 200."""
    if not isinstance(d, dict) or not isinstance(d.get("errors"), list):
        return False
    return any(isinstance(e, dict) and str(e.get("message")) in ("401", "403")
               for e in d["errors"])


async def _api(method, path, *, params=None, body=None, multipart=None, dropship=True,
               timeout=45, tra_loi_json=False, an_toan_lap=None):
    """Gọi api.thitruongsi.com. Trả (dữ_liệu, lỗi) - đúng một vế khác None.

    `an_toan_lap`: lệnh này gửi hai lần có sao không. Mặc định chỉ GET là an toàn. Lệnh ghi mà
    sàn trả 5xx hay đứt mạng SAU khi đã gửi thì KHÔNG thử lại, vì có thể sàn đã làm rồi."""
    import asyncio

    if an_toan_lap is None:
        an_toan_lap = method.upper() in ("GET", "HEAD")
    tok, loi = await _token()
    if loi:
        return None, loi
    p = dict(params or {})
    if dropship:
        p.setdefault("dropship", "true")
    url = API + "/" + str(path).lstrip("/")
    try:
        import httpx
    except Exception as e:
        return None, f"thiếu thư viện httpx trong máy chủ Naota ({type(e).__name__})"

    # Đường khiếu nại của sàn nhận multipart/form-data. httpx chỉ dựng multipart khi `files`
    # KHÁC RỖNG, nên trường chữ phải đi bằng dạng `(None, giá_trị)`.
    tep = None
    if multipart:
        tep = {str(k): (None, "" if v is None else str(v)) for k, v in multipart.items()}

    cho = 1.0
    da_gia_han = False
    lan = 0
    while True:
        headers = {"authorization": f"Bearer {tok}", "accept": "application/json",
                   "origin": WEB, "referer": WEB + "/"}
        await _nhip_do()
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
                r = await c.request(method.upper(), url, params=p, json=body, files=tep,
                                    headers=headers)
        except Exception as e:
            # Không nối được tới sàn thì request chưa đi, lặp lại vô hại kể cả với lệnh ghi.
            chua_gui = type(e).__name__ in ("ConnectError", "ConnectTimeout")
            if lan < _MAX_RETRY and (an_toan_lap or chua_gui):
                lan += 1
                await asyncio.sleep(cho)
                cho *= 2
                continue
            if not an_toan_lap and not chua_gui:
                return None, (f"mất kết nối với sàn TTS giữa chừng ({type(e).__name__}). KHÔNG "
                              "BIẾT sàn đã nhận lệnh hay chưa: kiểm tra lại trên sàn trước khi "
                              "gọi lại, đừng gửi lại ngay.")
            return None, f"không gọi được sàn TTS ({type(e).__name__}: {_che(e)})"
        if r.status_code in _RETRY_STATUS and lan < _MAX_RETRY \
                and (an_toan_lap or r.status_code == 429):
            lan += 1
            await asyncio.sleep(cho)
            cho *= 2
            continue
        try:
            d = r.json() if r.content else {}
        except Exception:
            d = None
        if (r.status_code in (401, 403) or _gql_401(d)) and not da_gia_han:
            # Web sàn làm đúng thế này: gặp 401 là đi gia hạn rồi gửi lại. Gửi lại an toàn vì
            # một lệnh bị từ chối vì token thì chưa làm gì cả.
            da_gia_han = True
            tok, loi = await _token(ep_gia_han=True)
            if loi:
                return None, loi
            continue
        if r.status_code in (401, 403) or _gql_401(d):
            return None, ("Sàn TTS vẫn từ chối token sau khi đã gia hạn. "
                          + _het_han_noi_gi(_con_lai(tok)))
        if r.status_code >= 400:
            # GraphQL báo lỗi TRUY VẤN bằng mã 4xx kèm thân JSON hợp lệ. Trả thân về cho lớp
            # GraphQL đọc, đừng nuốt thành một dòng "HTTP 422".
            if tra_loi_json and isinstance(d, dict) and d.get("errors"):
                return d, None
            if r.status_code in _RETRY_STATUS and not an_toan_lap:
                return None, (f"sàn TTS lỗi HTTP {r.status_code} khi đang ghi. KHÔNG BIẾT sàn "
                              "đã nhận lệnh hay chưa: kiểm tra lại trên sàn trước khi gọi lại.")
            chi_tiet = _che(json.dumps(d, ensure_ascii=False) if d is not None else r.text)
            return None, f"sàn TTS trả HTTP {r.status_code}: {chi_tiet}"
        return d, None


# ============================================================
# GraphQL
# ============================================================
def _qs_gt(v) -> str:
    """Mã hoá ĐẦY ĐỦ một giá trị trong chuỗi query, như `qs.stringify` của web sàn.

    Đã thử thật ngày 27/09/2026: `keyword=áo` hay `keyword=ao thun` (chữ có dấu, dấu cách để
    thô) làm sàn chết với câu lỗi rỗng; `keyword=%C3%A1o%20thun` chạy. Bản 1.0.x cố ý để thô vì
    tin một bản khảo sát, và đó là lý do tìm hàng bằng tiếng Việt không bao giờ ra kết quả."""
    if isinstance(v, bool):
        return "true" if v else "false"
    return quote(str(v), safe="")


def _build_qs(cap: dict) -> str:
    """Dựng chuỗi `?a=1&b=2` mà GraphQL của TTS nhận làm biến $query. Bỏ khoá rỗng."""
    phan = [f"{k}={_qs_gt(v)}" for k, v in cap.items() if v is not None and v != ""]
    return "?" + "&".join(phan)


def _goc_docs():
    try:
        return json.loads((Path(__file__).parent / "graphql.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ghi_doc(ctx, ten_op, patch):
    """Ghi bản sửa của MỘT operation ra thư mục state. Trả lý do thất bại, hoặc rỗng.

    Ghi NGOÀI gói có chủ ý: bản cập nhật gói thay cả thư mục `plugins/`, nên một bản sửa nằm
    trong đó sẽ bị xoá đúng vào lúc người dùng bấm Cập nhật. Bản sửa mang `_ban` của gói hiện
    tại, để gói mới hơn biết mà bỏ qua nó."""
    de = ctx.data_dir / "graphql.json"
    try:
        hien = json.loads(de.read_text(encoding="utf-8"))
        if not isinstance(hien, dict):
            hien = {}
    except Exception:
        hien = {}
    hien[ten_op] = {**(hien.get(ten_op) or {}), **patch, "_ban": _goc_docs().get("_ban", "")}
    try:
        de.write_text(json.dumps(hien, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return ""


def _gql_docs(ctx, bo_qua=None):
    """Tài liệu truy vấn: bản trong gói, đè bởi bản sửa trong thư mục state CÙNG ĐỜI gói.

    Bản sửa ghi dưới gói cũ bị bỏ qua: nếu không, một bản vá tự động của 1.0.x (đúng vào lúc
    sàn còn hình dạng khác) sẽ đè mãi lên truy vấn đã viết lại của bản mới."""
    goc = _goc_docs()
    ban = goc.get("_ban", "")
    try:
        de = json.loads((ctx.data_dir / "graphql.json").read_text(encoding="utf-8"))
        if isinstance(de, dict):
            for k, v in de.items():
                if not isinstance(v, dict):
                    continue
                if v.get("_ban") != ban:
                    if bo_qua is not None:
                        bo_qua.append(k)
                    continue
                goc[k] = {**(goc.get(k) or {}), **v}
    except Exception:
        pass
    return goc


# ---- Soi lược đồ ----
_KIND_CO_CON = ("OBJECT", "INTERFACE", "UNION")
_luoc_do = {}


async def _kieu(ten_type):
    """Các trường của một type GraphQL: {tên: (type_gốc, kind_gốc, là_danh_sách)}.

    Hỏi thẳng sàn thay vì đoán: đây là API nội bộ không tài liệu, và người duy nhất biết chắc
    hình dạng hiện tại là chính máy chủ. Nhớ trong phiên chạy để một lần tự sửa không bắn cả
    chục request soi lược đồ."""
    if ten_type in _luoc_do:
        return _luoc_do[ten_type], None
    doc = ("query NaotaIntrospect($n: String!) { __type(name: $n) { name kind fields { name "
           "type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } "
           "} } }")
    d, loi = await _api("POST", "/graphql", dropship=False, tra_loi_json=True, an_toan_lap=True,
                        body={"operationName": "NaotaIntrospect",
                              "variables": {"n": ten_type}, "query": doc})
    if loi:
        return None, loi
    if isinstance(d, dict) and d.get("errors"):
        return None, ("sàn không cho soi lược đồ GraphQL: "
                      + json.dumps(d["errors"], ensure_ascii=False)[:200])
    t = ((d or {}).get("data") or {}).get("__type")
    if not isinstance(t, dict) or not t.get("fields"):
        return None, f"sàn không biết type '{ten_type}'"
    ra = {}
    for f in t["fields"]:
        k, la_list = f.get("type") or {}, False
        while isinstance(k, dict) and k.get("kind") in ("NON_NULL", "LIST") and k.get("ofType"):
            la_list = la_list or k.get("kind") == "LIST"
            k = k["ofType"]
        ra[f.get("name")] = ((k or {}).get("name"), (k or {}).get("kind"), la_list)
    _luoc_do[ten_type] = ra
    return ra, None


# ---- Đọc và viết lại phần chọn trường ----
_TEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _doc_khoi(s, i):
    """Đọc một khối `{ ... }` bắt đầu ở s[i]. Trả (danh_sách_nút, vị_trí_sau) hoặc (None, _).

    Mỗi nút là [tên, đối_số_thô, con|None]. Cố ý KHÔNG viết một trình phân tích GraphQL đủ bộ:
    mọi tài liệu của gói là truy vấn phẳng không alias, không fragment. Gặp thứ lạ hơn thì trả
    None để phần tự sửa đứng ngoài, thay vì hiểu sai rồi viết hỏng một truy vấn đang chạy."""
    i, n, nut = i + 1, len(s), []
    while i < n:
        if s[i] in " \t\r\n,":
            i += 1
            continue
        if s[i] == "}":
            return nut, i + 1
        m = _TEN.match(s, i)
        if not m:
            return None, i
        ten, i = m.group(0), m.end()
        while i < n and s[i] in " \t\r\n,":
            i += 1
        if i < n and s[i] == ":":
            return None, i
        doi_so = ""
        if i < n and s[i] == "(":
            sau, do = i + 1, 1
            while sau < n and do:
                do += {"(": 1, ")": -1}.get(s[sau], 0)
                sau += 1
            if do:
                return None, i
            doi_so, i = s[i:sau], sau
            while i < n and s[i] in " \t\r\n,":
                i += 1
        con = None
        if i < n and s[i] == "{":
            con, i = _doc_khoi(s, i)
            if con is None:
                return None, i
        nut.append([ten, doi_so, con])
    return None, i


def _tach_doc(doc):
    """(đầu `query X($q: String!)`, [nút]) hoặc None."""
    j = doc.find("{")
    if j < 0:
        return None
    nut, k = _doc_khoi(doc, j)
    if nut is None or doc[k:].strip():
        return None
    return doc[:j].strip(), nut


def _viet(nut):
    return " ".join(t + a + ((" { " + _viet(c) + " }") if c is not None else "")
                    for t, a, c in nut)


async def _loc(nut, ten_type, bo):
    """Giữ lại những trường type này THẬT SỰ có; bỏ trường không còn, bỏ trường đối tượng thiếu
    khối con. Trả (nút_đã_lọc, lỗi)."""
    truong, loi = await _kieu(ten_type)
    if loi:
        return None, loi
    ra = []
    for ten, doi_so, con in nut:
        if ten.startswith("__"):
            ra.append([ten, doi_so, con])
            continue
        if ten not in truong:
            bo.append(f"{ten_type}.{ten}")
            continue
        goc, kind, _ = truong[ten]
        if kind in _KIND_CO_CON:
            if con is None:
                bo.append(f"{ten_type}.{ten} (thiếu khối con)")
                continue
            con2, loi = await _loc(con, goc, bo)
            if loi:
                return None, loi
            if not con2:
                bo.append(f"{ten_type}.{ten} (không còn trường con nào)")
                continue
            ra.append([ten, doi_so, con2])
        else:
            ra.append([ten, doi_so, None])
    return ra, None


_LOI_HINH_DANG = re.compile(r'Cannot query field|must have a selection of subfields|'
                            r'must not have a selection')


def _la_loi_hinh_dang(loi_json) -> bool:
    for e in (loi_json or []):
        if not isinstance(e, dict):
            continue
        if ((e.get("extensions") or {}).get("code") == "GRAPHQL_VALIDATION_FAILED"
                or _LOI_HINH_DANG.search(str(e.get("message") or ""))):
            return True
    return False


async def _tu_sua(ctx, ten_op, spec, loi_json):
    """Viết lại tài liệu truy vấn cho khớp lược đồ hiện tại. Trả (doc_mới, ghi_chú, lý_do_hỏng).

    Hai việc, đúng thứ tự:
    1. Lớp bọc: không trường nào được chọn còn nằm trên type gốc, mà type gốc có một danh sách
       đối tượng. Đây là dạng hỏng ngày 05/09/2026 (`products`, `items`). Nếu tài liệu đang
       dùng một lớp bọc SAI TÊN thì THAY tên, không lồng thêm tầng.
    2. Bỏ trường: mọi trường sàn không còn, và mọi trường đối tượng thiếu khối con. Đây là dạng
       hỏng ngày 27/09/2026, và là thứ phần tự sửa của 1.0.x không làm được.

    Chỉ BỎ, không bao giờ tự thêm trường: một truy vấn ít trường vẫn chạy, còn một trường đoán
    bừa thì lại hỏng."""
    if not _la_loi_hinh_dang(loi_json):
        return None, "", "lỗi không thuộc dạng 'truy vấn chọn sai trường'"
    tach = _tach_doc(spec.get("doc") or "")
    if not tach:
        return None, "", "không đọc được tài liệu truy vấn hiện tại"
    dau, nut = tach
    if len(nut) != 1:
        return None, "", "tài liệu truy vấn có nhiều hơn một trường gốc"
    goc_ten, goc_doi_so, con = nut[0]
    q, loi = await _kieu("Query")
    if loi:
        return None, "", loi
    if goc_ten not in q:
        return None, "", (f"sàn không còn trường gốc '{goc_ten}'. Các trường gốc sàn khai: "
                          + ", ".join(sorted(q)))
    kieu_goc = q[goc_ten][0]
    truong_goc, loi = await _kieu(kieu_goc)
    if loi:
        return None, "", loi
    ghi = []
    con = con or []
    if con and not any(t in truong_goc for t, _, _ in con):
        ung = [t for t, (_, k, la_list) in truong_goc.items() if la_list and k in _KIND_CO_CON]
        for uu in ("products", "items", "shops", "orders", "data", "nodes", "results"):
            if uu in ung:
                ung = [uu] + [x for x in ung if x != uu]
                break
        if ung:
            if len(con) == 1 and con[0][2] is not None:
                ghi.append(f"đổi lớp bọc '{con[0][0]}' thành '{ung[0]}'")
                con = [[ung[0], "", con[0][2]]]
            else:
                ghi.append(f"lồng kết quả vào lớp '{ung[0]}'")
                con = [[ung[0], "", con]]
    bo = []
    con2, loi = await _loc(con, kieu_goc, bo)
    if loi:
        return None, "", loi
    if not con2:
        return None, "", "bỏ hết trường sai thì không còn trường nào để hỏi"
    if bo:
        ghi.append("bỏ trường sàn không còn: " + ", ".join(bo[:15]))
    moi = dau + " { " + goc_ten + goc_doi_so + " { " + _viet(con2) + " } }"
    if moi == spec.get("doc"):
        return None, "", "lược đồ không chỉ ra được chỗ nào để sửa"
    return moi, "; ".join(ghi), ""


async def _gql(ctx, ten_op, bien, cho_tu_sua=True):
    """Gọi POST /graphql. Trả (dữ_liệu_đã_bóc_lớp, lỗi).

    Gặp lỗi 'truy vấn chọn sai trường' thì tự soi lược đồ, viết lại, thử LẠI MỘT LẦN, và nếu
    chạy thì ghi bản sửa ra ngoài gói. Một lần thôi, có chủ ý."""
    docs = _gql_docs(ctx)
    spec = docs.get(ten_op) or {}
    doc = (spec.get("doc") or "").strip()
    if not doc:
        return None, (f"không có tài liệu truy vấn cho '{ten_op}'. Xem bằng tool tts_graphql "
                      "(action=show) rồi sửa bằng action=set.")
    d, loi = await _api("POST", "/graphql", dropship=False, tra_loi_json=True, an_toan_lap=True,
                        body={"operationName": ten_op, "variables": bien, "query": doc})
    if loi:
        return None, loi

    ghi_chu = ""
    if isinstance(d, dict) and d.get("errors") and not d.get("data"):
        if not _la_loi_hinh_dang(d["errors"]):
            return None, (
                "sàn TTS báo lỗi khi CHẠY truy vấn '%s': %s. Đây không phải sai tên trường. Hay "
                "gặp nhất là tham số lọc không hợp lệ (mã sản phẩm, mã shop sai) hoặc sàn đang "
                "trục trặc; thử lại với ít bộ lọc hơn."
                % (ten_op, json.dumps(d["errors"], ensure_ascii=False)[:300]))
        moi, ghi, vi_sao = (None, "", "đã thử tự sửa một lần rồi")
        if cho_tu_sua:
            moi, ghi, vi_sao = await _tu_sua(ctx, ten_op, spec, d["errors"])
        if not moi:
            return None, (
                "sàn TTS từ chối truy vấn GraphQL '%s': %s\n\nĐây là tên trường trong "
                "graphql.json không còn khớp sàn, KHÔNG phải token hay mạng. Naota đã thử tự "
                "sửa nhưng không xong (%s). Soi hình dạng thật bằng tts_graphql "
                "action=introspect rồi ghi lại bằng action=set. Không phải cài lại gói."
                % (ten_op, json.dumps(d["errors"], ensure_ascii=False)[:400], vi_sao))
        d2, loi2 = await _api("POST", "/graphql", dropship=False, tra_loi_json=True,
                              an_toan_lap=True,
                              body={"operationName": ten_op, "variables": bien, "query": moi})
        if loi2 or (isinstance(d2, dict) and d2.get("errors") and not d2.get("data")):
            chi_tiet = loi2 or json.dumps(d2.get("errors"), ensure_ascii=False)[:300]
            return None, (
                "sàn TTS từ chối truy vấn GraphQL '%s'. Naota đã tự sửa (%s) rồi thử lại, vẫn "
                "không được: %s. Soi bằng tts_graphql action=introspect rồi ghi lại bằng "
                "action=set." % (ten_op, ghi, chi_tiet))
        _ghi_doc(ctx, ten_op, {"doc": moi})
        d = d2
        ghi_chu = ("Sàn đã đổi hình dạng dữ liệu. Naota tự sửa truy vấn (%s), thử lại thành "
                   "công và ĐÃ LƯU bản sửa ngoài gói, nên lần sau chạy thẳng." % ghi)

    than = (d or {}).get("data") if isinstance(d, dict) else None
    goc = spec.get("root") or ""
    if isinstance(than, dict) and goc and goc in than:
        ra = {goc: than[goc]}
    elif isinstance(than, dict) and len(than) == 1:
        ra = dict(than)
    else:
        ra = d
    if ghi_chu and isinstance(ra, dict):
        ra["_naota_tu_sua"] = ghi_chu
    return ra, None


# ============================================================
# Định dạng câu trả lời
# ============================================================
def _ra(d, ghi_chu=""):
    """Đóng gói kết quả cho model. Cắt ở trần ký tự để một danh sách dài không nuốt ngữ cảnh."""
    canh = _canh_bao_han()
    goi = {"ok": True, "data": d}
    if ghi_chu:
        goi["ghi_chu"] = ghi_chu
    if canh:
        goi["canh_bao"] = canh
    s = json.dumps(goi, ensure_ascii=False, default=str)
    if len(s) > _TRAN_KY_TU:
        s = s[:_TRAN_KY_TU] + ('... [CẮT BỚT: kết quả quá dài. Thu hẹp bằng limit nhỏ hơn, hoặc '
                               'hỏi đúng một mục thay vì cả danh sách.]')
    return s


def _loi(msg):
    return "ERROR: " + str(msg)


def _int(args, ten, mac_dinh, nho_nhat=1, lon_nhat=200):
    try:
        v = int(args.get(ten) if args.get(ten) is not None else mac_dinh)
    except (TypeError, ValueError):
        return mac_dinh
    return max(nho_nhat, min(lon_nhat, v))


def _str(args, ten, mac_dinh=""):
    v = args.get(ten)
    return str(mac_dinh if v is None or v == "" else v).strip()


def _obj(args, ten):
    """Đọc một tham số object. Model nhiều khi đưa vào chuỗi JSON, nhận cả hai."""
    v = args.get(ten)
    if isinstance(v, str) and v.strip():
        try:
            v = json.loads(v)
        except Exception:
            return None
    return v if isinstance(v, (dict, list)) else None


def _so(x, mac_dinh=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return mac_dinh


def _tien(x):
    try:
        return f"{float(x):,.0f}"
    except (TypeError, ValueError):
        return str(x)


def _sdt(s) -> str:
    """Chuẩn số điện thoại như web sàn: bỏ ký tự thừa, +84/84 đổi thành 0."""
    so = re.sub(r"\D", "", str(s or ""))
    if so.startswith("84") and len(so) == 11:
        so = "0" + so[2:]
    return so


# ============================================================
# Địa giới: đối chiếu với danh mục của CHÍNH SÀN
# ============================================================
# Sàn so địa chỉ theo đúng chuỗi trong danh mục của nó (vd "TP Hồ Chí Minh", "Q. 1",
# "Phường Bến Nghé"). Và nhớ: trên sàn này `city` = TỈNH, `province` = QUẬN.
_dia_gioi = {"m": None, "luc": 0.0}

_BI_DANH_TINH = {
    "hcm": "ho chi minh", "tphcm": "ho chi minh", "tp hcm": "ho chi minh",
    "sai gon": "ho chi minh", "saigon": "ho chi minh", "sg": "ho chi minh",
    "hn": "ha noi", "hue": "thua thien hue", "vung tau": "ba ria vung tau",
    "brvt": "ba ria vung tau", "daklak": "dak lak", "daknong": "dak nong",
    "dn": "da nang", "hp": "hai phong", "ct": "can tho",
}
_LOAI = {"thanh pho": "tp", "tp": "tp", "tinh": "tinh",
         "quan": "q", "q": "q", "huyen": "h", "h": "h", "thi xa": "tx", "tx": "tx",
         "phuong": "p", "p": "p", "xa": "x", "x": "x", "thi tran": "tt", "tt": "tt"}
_TIEN_TO = sorted(_LOAI, key=len, reverse=True)


def _bo_dau(s) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    # "Q1", "P12", "quan1" -> "q 1": số dính liền tiền tố là cách gõ tin nhắn rất hay gặp.
    s = re.sub(r"\b(quan|phuong|huyen|q|p|h|f)(\d+)\b", r"\1 \2", s)
    s = re.sub(r"\bf (\d+)\b", r"p \1", s)
    return " ".join(s.split())


def _loai_loi(ten) -> tuple:
    """("q", "1") cho "Q. 1"; ("tp", "ho chi minh") cho "TP Hồ Chí Minh"."""
    n = _bo_dau(ten)
    for t in _TIEN_TO:
        if n.startswith(t + " "):
            return _LOAI[t], n[len(t) + 1:].strip()
    return "", n


async def _danh_muc():
    """{tỉnh: {quận: [phường]}} của sàn, nhớ 12 giờ. (dữ_liệu, lỗi)."""
    if _dia_gioi["m"] and time.time() - _dia_gioi["luc"] < 12 * 3600:
        return _dia_gioi["m"], None
    d, loi = await _api("GET", "/v1/user/api/vi/locations.json")
    if loi:
        return None, loi
    ds = d.get("locations") if isinstance(d, dict) else d
    m = {}
    for x in ds or []:
        if isinstance(x, dict):
            m.update({k: v for k, v in x.items() if isinstance(v, dict)})
    if not m:
        return None, "danh mục địa giới của sàn trả về rỗng"
    _dia_gioi.update(m=m, luc=time.time())
    return m, None


def _chon(nhap, ds, bi_danh=None):
    """Tìm `nhap` trong danh sách tên của sàn. Trả (tên_khớp|None, [ứng_viên])."""
    n = _bo_dau(nhap)
    if not n:
        return None, []
    if bi_danh:
        n = bi_danh.get(n, n)
    loai, loi = _loai_loi(n)
    if bi_danh:
        loi = bi_danh.get(loi, loi)
    dung = [x for x in ds if _bo_dau(x) == n]
    if len(dung) == 1:
        return dung[0], dung
    ung = [x for x in ds if _loai_loi(x)[1] == loi and (not loai or _loai_loi(x)[0] == loai)]
    if len(ung) == 1:
        return ung[0], ung
    if ung:
        return None, ung
    # Không khớp nguyên văn: đưa ra vài tên gần giống để người dùng chọn. Không bao giờ tự
    # chọn hộ ở bước này, vì "gần giống" giữa hai phường là giao nhầm hàng.
    if not loi.isdigit():
        gan = [x for x in ds if loi and (loi in _loai_loi(x)[1] or _loai_loi(x)[1] in loi)]
        return None, gan[:8]
    return None, []


async def _khop_dia_chi(tinh, quan, phuong):
    """Đối chiếu tỉnh/quận/phường với danh mục sàn. Trả dict có `ok`."""
    m, loi = await _danh_muc()
    if loi:
        return {"ok": False, "loi": f"không tải được danh mục địa giới của sàn: {loi}"}
    ra = {"ok": False}
    t, ung = _chon(tinh, list(m), _BI_DANH_TINH)
    if not t:
        ra["can_hoi_lai"] = "tỉnh/thành"
        ra["ung_vien_tinh"] = ung or "không có tên nào gần giống, hỏi lại khách"
        return ra
    ra["tinh"] = t
    q, ung = _chon(quan, list(m[t]))
    if not q:
        ra["can_hoi_lai"] = "quận/huyện"
        ra["ung_vien_quan"] = ung or list(m[t])
        return ra
    ra["quan"] = q
    p, ung = _chon(phuong, list(m[t][q]))
    if not p:
        ra["can_hoi_lai"] = "phường/xã"
        ra["ung_vien_phuong"] = ung or list(m[t][q])
        return ra
    ra.update(ok=True, phuong=p)
    return ra


_CHU_DUONG = {"duong", "pho", "ngo", "ngach", "hem", "kiet", "so", "d", "dg"}


def _vi_tri(t, cum):
    """Vị trí cuối cùng của CỤM TỪ nguyên vẹn `cum` trong `t` (đã chuẩn hoá), -1 nếu không có."""
    return t.rfind(" " + cum + " ")


def _xoa(t, vt, cum):
    """Xoá một cụm đã dùng khỏi văn bản, giữ nguyên độ dài để vị trí khác không lệch.

    Chữ đã dùng cho tỉnh hay quận thì không được dùng lại cho cấp dưới: "Hải Châu, Đà Nẵng"
    là QUẬN Hải Châu, không phải thêm cả PHƯỜNG Hải Châu chỉ vì hai tên trùng chữ."""
    if vt < 0:
        return t
    n = len(cum) + 2
    return t[:vt] + " " * n + t[vt + n:]


def _tim_cap(t, ten):
    """Tìm một đơn vị hành chính trong văn bản. Trả (điểm, vị_trí, cụm_khớp) hoặc None.

    Tên chỉ là số ("Q. 1", "Phường 12") thì BẮT BUỘC có tiền tố đi kèm, vì một con số trần
    trong tin nhắn có thể là số nhà. Tìm theo cụm từ nguyên vẹn nên "q 1" không khớp "q 12"."""
    loai, loi = _loai_loi(ten)
    ten_tien_to = [k for k, v in _LOAI.items() if v == loai] if loai else []
    tot = (-1, "")
    for tt in ten_tien_to:
        vt = _vi_tri(t, tt + " " + loi)
        if vt > tot[0]:
            tot = (vt, tt + " " + loi)
    if tot[0] >= 0:
        return 2, tot[0], tot[1]
    if loi.isdigit() or len(loi) < 3:
        return None
    vt = _vi_tri(t, loi)
    if vt < 0:
        return None
    # Tên trần đứng ngay sau số nhà hay sau chữ "đường/ngõ/hẻm" là TÊN ĐƯỜNG: "15 Trần Phú" không
    # phải phường Trần Phú. Việt Nam đặt tên đường và tên phường trùng nhau rất nhiều.
    truoc = t[:vt].split()[-1:]
    if truoc and (truoc[0][0].isdigit() or truoc[0] in _CHU_DUONG):
        return None
    return 1, vt, loi


async def _tim_dia_chi(van_ban):
    """Tự tìm tỉnh/quận/phường trong nguyên đoạn tin nhắn, dựa trên danh mục của sàn."""
    m, loi = await _danh_muc()
    if loi:
        return {"loi": loi}
    t = " " + _bo_dau(van_ban) + " "
    tinh = {}
    for ten in m:
        _, loi_t = _loai_loi(ten)
        tot = (-1, "")
        for cum in [loi_t] + [k for k, v in _BI_DANH_TINH.items() if v == loi_t]:
            vt = _vi_tri(t, cum)
            if vt > tot[0]:
                tot = (vt, cum)
        if tot[0] >= 0:
            tinh[ten] = _xoa(t, *tot)
    # Không nêu tỉnh thì dò quận trên cả nước. Tên trần ("Củ Chi") chỉ nhận khi cả nước có
    # đúng một quận khớp; "Tân Bình", "Phú Nhuận" có ở nhiều tỉnh nên phải hỏi lại.
    pham_vi = tinh or {ten: t for ten in m}
    ket = []
    for ti, t_ti in pham_vi.items():
        for q, ds_p in m[ti].items():
            kq = _tim_cap(t_ti, q)
            if not kq:
                continue
            t_q = _xoa(t_ti, kq[1], kq[2])
            phuong = [(p, _tim_cap(t_q, p)) for p in ds_p]
            phuong = [(p, k) for p, k in phuong if k]
            ket.append((ti, q, kq[0], phuong))
    if not ket:
        return {"tinh": next(iter(tinh)) if len(tinh) == 1 else None,
                "ung_vien_tinh": list(tinh) if len(tinh) > 1 else None,
                "quan": None, "phuong": None, "chac_chan": False}
    diem_q = max(k[2] for k in ket)
    ket = [k for k in ket if k[2] == diem_q]
    # Quận có phường khớp được ưu tiên hơn quận không có phường nào khớp; quận có phường khớp
    # KÈM chữ phường/xã lại ưu tiên hơn nữa.
    for dk in (lambda k: any(x[1][0] >= 2 for x in k[3]), lambda k: bool(k[3])):
        loc = [k for k in ket if dk(k)]
        if loc:
            ket = loc
            break
    if not tinh and diem_q < 2 and len(ket) > 1:
        return {"tinh": None, "quan": None, "phuong": None, "chac_chan": False,
                "ung_vien_quan": [f"{q}, {ti}" for ti, q, _, _ in ket][:12]}
    ra = {"chac_chan": False}
    if len(ket) > 1:
        ra["ung_vien_quan"] = [f"{q}, {ti}" for ti, q, _, _ in ket]
        return ra
    ti, q, _, phuong = ket[0]
    ra.update(tinh=ti, quan=q)
    diem_p = 0
    if phuong:
        diem_p = max(k[0] for _, k in phuong)
        phuong = [p for p, k in phuong if k[0] == diem_p]
    if len(phuong) == 1:
        # Chỉ "chắc chắn" khi tin nhắn ghi rõ chữ phường/xã. Tên trần thì vẫn điền, nhưng đánh
        # dấu để hỏi lại khách một câu.
        ra.update(phuong=phuong[0], chac_chan=diem_p >= 2)
        if diem_p < 2:
            ra["can_xac_nhan"] = (f"'{phuong[0]}' đoán từ tên không có chữ phường/xã đi kèm, "
                                  "hỏi lại khách cho chắc")
    else:
        ra["phuong"] = None
        ra["ung_vien_phuong"] = phuong or list(m[ti][q])
    return ra


# ============================================================
# Sản phẩm (dùng chung cho giỏ và đơn)
# ============================================================
async def _san_pham(ctx, pid, nho):
    """Chi tiết một sản phẩm qua GraphQL, nhớ trong một lượt gọi tool. (sp, lỗi)."""
    pid = str(pid or "").strip()
    if not pid:
        return None, "thiếu product_id"
    if pid in nho:
        return nho[pid], None
    d, loi = await _gql(ctx, "ProductById", {"id": pid})
    if loi:
        return None, loi
    sp = (d or {}).get("product") if isinstance(d, dict) else None
    if not isinstance(sp, dict):
        return None, f"sàn không trả về sản phẩm {pid}"
    nho[pid] = sp
    return sp, None


def _bien_the(sp, vid):
    for v in (sp or {}).get("variants") or []:
        if str(v.get("id")) == str(vid):
            return v
    return None


def _cac_bien_the(sp):
    return [{"variant_id": v.get("id"), "ten": v.get("title"),
             "gia_nhap": v.get("dropship_price"), "gia_ban_goi_y": v.get("market_price"),
             "ton_kho": v.get("inventory_quantity")} for v in (sp or {}).get("variants") or []]


# ============================================================
# NHÓM A + F: sản phẩm, nhà cung cấp, bài đăng bán, sản phẩm đã lưu
# ============================================================
_SORT = {"_score", "created_at", "total_sales", "dropship_profit", "price"}
_GIA = ("Ba con số giá: dropship_price là giá BẠN trả sàn cho một món (giá nhập dropship), "
        "market_price là giá bán gợi ý cho khách, dropship_profit = market_price - "
        "dropship_price là lãi gợi ý. Lãi THẬT còn phụ thuộc phí ship và khuyến mãi của shop.")


async def _products(args, ctx):
    args = args or {}
    act = _str(args, "action", "search").lower()

    if act == "search":
        sort = _str(args, "sort_by", "_score")
        if sort not in _SORT:
            return _loi(f"sort_by phải là một trong: {', '.join(sorted(_SORT))}")
        qs = _build_qs({
            "filter_only_dropship": "true",
            "keyword": _str(args, "keyword"),
            "limit": _int(args, "limit", 20, 1, 100),
            "offset": _int(args, "offset", 0, 0, 100000),
            "sort_by": sort,
            "ascending": "true" if args.get("ascending") else None,
            "filter_category_lv1": _str(args, "category_lv1"),
            "filter_category_lv2": _str(args, "category_lv2"),
            "filter_province": _str(args, "province"),
            "filter_shop_id": _str(args, "shop_id"),
        })
        d, loi = await _gql(ctx, "searchProductsQuery", {"query": qs})
        return _loi(loi) if loi else _ra(d, _GIA + " Chọn xong thì gọi action=get với "
                                            "product_id để lấy đúng variant_id của màu/size.")

    if act == "get":
        pid = _str(args, "product_id")
        if not pid:
            return _loi("thiếu 'product_id' (nhận cả mã số lẫn id dài của sàn).")
        d, loi = await _gql(ctx, "ProductById", {"id": pid})
        return _loi(loi) if loi else _ra(d, _GIA + " Mỗi màu/size là một variant: lấy đúng "
                                            "variants[].id để thêm vào giỏ, đừng đoán.")

    if act == "reviews":
        p = {"limit": _int(args, "limit", 20, 1, 100), "offset": _int(args, "offset", 0, 0, 10000)}
        if _str(args, "product_id"):
            p["product_id"] = _str(args, "product_id")
        if _str(args, "shop_id"):
            p["shop_id"] = _str(args, "shop_id")
        d, loi = await _api("GET", "/v1/review/reviews", params=p)
        return _loi(loi) if loi else _ra(d)

    if act == "recent":
        d, loi = await _api("GET", "/v1/analytics/user/recent_products")
        return _loi(loi) if loi else _ra(d)

    if act == "collections":
        cid = _str(args, "collection_id")
        if cid:
            d, loi = await _api("GET", f"/v2/order/api/smart_collections/{cid}.json",
                                params={"limit": _int(args, "limit", 20, 1, 100),
                                        "offset": _int(args, "offset", 0, 0, 10000)})
        else:
            d, loi = await _api("GET", "/v2/order/api/collection_screens/home.json")
        return _loi(loi) if loi else _ra(d)

    return _loi("action phải là: search | get | reviews | recent | collections")


async def _suppliers(args, ctx):
    args = args or {}
    act = _str(args, "action", "search").lower()
    sid = _str(args, "shop_id")

    if act == "search":
        qs = _build_qs({"keyword": _str(args, "keyword"),
                        "limit": _int(args, "limit", 20, 1, 100),
                        "offset": _int(args, "offset", 0, 0, 10000),
                        "filter_province": _str(args, "province")})
        d, loi = await _gql(ctx, "searchShopQuery", {"query": qs})
        return _loi(loi) if loi else _ra(d)

    if act == "get":
        if not sid:
            return _loi("thiếu 'shop_id'.")
        d, loi = await _api("GET", f"/v1/user/api/shop/{sid}")
        return _loi(loi) if loi else _ra(d)

    if act == "promotions":
        if not sid:
            return _loi("thiếu 'shop_id'.")
        d, loi = await _api("GET", "/v2/order/api/price_rules.json", params={"shop_id": sid})
        return _loi(loi) if loi else _ra(d, "price_rules là các chương trình freeship và thưởng "
                                            "theo đơn của shop. Phải cộng vào mới ra lợi nhuận "
                                            "thật của một đơn. Dùng id của nó trong "
                                            "'price_rule_ids' khi lên đơn.")

    if act == "following":
        d, loi = await _api("GET", "/v1/user/api/v4/me/shops/following")
        return _loi(loi) if loi else _ra(d)

    if act == "check":
        if not sid:
            return _loi("thiếu 'shop_id'.")
        d, loi = await _api("GET", f"/v1/user/api/shops/{sid}/is-following")
        return _loi(loi) if loi else _ra(d)

    return _loi("action phải là: search | get | promotions | following | check")


async def _listings(args, ctx):
    pid = _str(args or {}, "product_id")
    if not pid:
        return _loi("thiếu 'product_id'.")
    d, loi = await _api("GET", f"/v2/order/api/products/{pid}/posts.json")
    return _loi(loi) if loi else _ra(d)


async def _listing_write(args, ctx):
    args = args or {}
    act = _str(args, "action", "create").lower()
    than = _obj(args, "raw_body") or _obj(args, "post") or {}
    if act == "create":
        pid = _str(args, "product_id")
        if not pid:
            return _loi("thiếu 'product_id'.")
        if not than:
            return _loi("thiếu nội dung bài đăng: đưa vào 'post' (object) hoặc 'raw_body'.")
        d, loi = await _api("POST", f"/v2/order/api/products/{pid}/posts.json",
                            body=than if _obj(args, "raw_body") else {"post": than})
        return _loi(loi) if loi else _ra(d)
    if act == "update":
        post_id = _str(args, "post_id")
        if not post_id:
            return _loi("thiếu 'post_id'.")
        if not than:
            return _loi("thiếu nội dung sửa: đưa vào 'post' (object) hoặc 'raw_body'.")
        d, loi = await _api("PUT", f"/v2/order/api/product-posts/{post_id}.json",
                            body=than if _obj(args, "raw_body") else {"post": than})
        return _loi(loi) if loi else _ra(d)
    return _loi("action phải là: create | update. Xoá dùng tool tts_listing_delete.")


async def _listing_delete(args, ctx):
    args = args or {}
    post_id = _str(args, "post_id")
    if not post_id:
        return _loi("thiếu 'post_id'.")
    if not args.get("confirm"):
        return _ra({"se_xoa_bai_dang": post_id, "da_thuc_thi": False},
                   "Đây mới là bản xem trước. Bài đăng xoá rồi không lấy lại được. Gọi lại tool "
                   "này với confirm=true nếu chắc chắn.")
    d, loi = await _api("DELETE", f"/v2/order/api/product-posts/{post_id}.json")
    return _loi(loi) if loi else _ra(d, "Đã xoá bài đăng.")


async def _wishlist(args, ctx):
    args = args or {}
    act = _str(args, "action", "list").lower()
    if act == "list":
        d, loi = await _api("GET", "/v1/marketing/wishlists/products",
                            params={"limit": _int(args, "limit", 50, 1, 200),
                                    "offset": _int(args, "offset", 0, 0, 10000)})
        return _loi(loi) if loi else _ra(d)
    if act == "check":
        pid = _str(args, "product_id")
        if not pid:
            return _loi("thiếu 'product_id'.")
        d, loi = await _api("GET", f"/v1/marketing/wishlists/{pid}/is_added")
        return _loi(loi) if loi else _ra(d)
    return _loi("action phải là: list | check")


async def _wishlist_write(args, ctx):
    args = args or {}
    act = _str(args, "action", "add").lower()
    pid = _str(args, "product_id")
    if not pid:
        return _loi("thiếu 'product_id'.")
    if act == "add":
        d, loi = await _api("POST", "/v1/marketing/wishlists",
                            body={"product_id": pid, "dropship": True})
        return _loi(loi) if loi else _ra(d)
    if act == "remove":
        d, loi = await _api("DELETE", f"/v1/marketing/wishlists/{pid}")
        return _loi(loi) if loi else _ra(d)
    return _loi("action phải là: add | remove")


async def _supplier_follow(args, ctx):
    args = args or {}
    sid = _str(args, "shop_id")
    if not sid:
        return _loi("thiếu 'shop_id'.")
    d, loi = await _api("POST", f"/v1/user/api/shops/{sid}/follow")
    return _loi(loi) if loi else _ra(d, "Sàn dùng chung một đường cho theo dõi và bỏ theo dõi, "
                                        "gọi lại lần nữa là đảo trạng thái. Kiểm bằng "
                                        "tts_suppliers action=check.")


# ============================================================
# NHÓM B: giỏ hàng
# ============================================================
_TRUONG_GIO = ("variant_id", "product_id", "shop_id", "vendor", "product_title", "variant_title",
               "quantity", "dropship_selling_price", "dropship_price", "market_price",
               "properties", "note", "image_src", "inventory_quantity")


def _gon_gio(cart):
    """Giỏ gọn theo nhà cung cấp, kèm `token` để lên đơn."""
    if not isinstance(cart, dict):
        return cart
    theo_shop = {}
    for it in cart.get("items") or cart.get("line_items") or []:
        if not isinstance(it, dict):
            continue
        gon = {k: it[k] for k in _TRUONG_GIO if k in it}
        theo_shop.setdefault(str(it.get("shop_id") or "?"), []).append(gon)
    return {"cart_token": cart.get("token"), "so_nha_cung_cap": len(theo_shop),
            "theo_nha_cung_cap": theo_shop}


async def _doc_gio():
    d, loi = await _api("GET", "/v2/order/api/carts.json")
    if loi:
        return None, loi
    cart = d.get("carts") if isinstance(d, dict) and "carts" in d else d
    return cart if isinstance(cart, dict) else {}, None


async def _cart(args, ctx):
    cart, loi = await _doc_gio()
    return _loi(loi) if loi else _ra(_gon_gio(cart),
                                     "Mỗi nhà cung cấp lên MỘT đơn riêng, nên giỏ có 3 shop là 3 "
                                     "đơn, 3 phí ship. Lên đơn thì truyền đúng các dòng của một "
                                     "shop vào tts_create_order.")


async def _cart_update(args, ctx):
    args = args or {}
    raw = _obj(args, "raw_body")
    ghi = []
    if raw is not None:
        than = dict(raw) if isinstance(raw, dict) else {"items": raw}
    else:
        dong = _obj(args, "items")
        if not isinstance(dong, list) or not dong:
            return _loi("thiếu 'items': mảng các dòng {product_id, variant_id, quantity, "
                        "dropship_selling_price}. Đặt quantity=0 để xoá một dòng.")
        nho, sach = {}, []
        for it in dong:
            if not isinstance(it, dict):
                return _loi("mỗi mục trong 'items' phải là object.")
            vid = str(it.get("variant_id") or "").strip()
            if not vid:
                return _loi("mỗi dòng phải có 'variant_id' (lấy từ tts_products action=get).")
            try:
                sl = int(it.get("quantity") if it.get("quantity") is not None else 1)
            except (TypeError, ValueError):
                return _loi(f"quantity của variant {vid} không phải số.")
            gia = it.get("dropship_selling_price")
            # Có product_id thì soi sản phẩm: kiểm variant có thật, giá bán không dưới giá nhập
            # (web sàn chặn đúng điều này), và điền giá bán gợi ý khi model không đưa giá.
            if sl > 0 and it.get("product_id"):
                sp, loi = await _san_pham(ctx, it["product_id"], nho)
                if loi:
                    return _loi(loi)
                v = _bien_the(sp, vid)
                if not v:
                    return _loi(f"sản phẩm {it['product_id']} không có variant {vid}. Các "
                                "variant đang có: " + json.dumps(_cac_bien_the(sp),
                                                                ensure_ascii=False))
                if gia in (None, ""):
                    gia = v.get("market_price")
                    ghi.append(f"{v.get('title')}: chưa có giá bán, dùng giá gợi ý {_tien(gia)}")
                if _so(gia) < _so(v.get("dropship_price")):
                    return _loi(f"giá bán {_tien(gia)} thấp hơn giá nhập "
                                f"{_tien(v.get('dropship_price'))} của '{v.get('title')}'. "
                                "Sàn không cho bán lỗ.")
                if v.get("inventory_quantity") is not None \
                        and sl > _so(v.get("inventory_quantity")):
                    ghi.append(f"{v.get('title')}: đặt {sl} nhưng kho chỉ còn "
                               f"{v.get('inventory_quantity')}")
            if sl > 0 and gia in (None, ""):
                return _loi(f"variant {vid} thiếu 'dropship_selling_price' (giá bán cho khách). "
                            "Truyền kèm product_id để Naota tự lấy giá gợi ý.")
            dong_sach = {"variant_id": vid, "quantity": sl,
                         "dropship_selling_price": _so(gia) if gia not in (None, "") else 0,
                         "note": str(it.get("note") or "")}
            if it.get("properties"):
                dong_sach["properties"] = it["properties"]
            sach.append(dong_sach)
        than = {"items": sach}
    than.setdefault("dropship", True)
    d, loi = await _api("POST", "/v2/order/api/carts/update.json", body=than)
    if loi:
        return _loi(loi)
    cart = d.get("cart") if isinstance(d, dict) and "cart" in d else d
    return _ra(_gon_gio(cart) if isinstance(cart, dict) else cart,
               "; ".join(ghi + ["Cùng một đường dùng cho thêm mới, đổi số lượng, đổi giá bán và "
                                "xoá dòng (quantity=0). Đọc lại giỏ ở trên để chắc số lượng "
                                "đúng như ý, vì sàn có thể cộng dồn khi variant đã có sẵn."]))


# ============================================================
# NHÓM C: khách hàng và địa chỉ
# ============================================================
async def _tim_khach(q, limit=20):
    d, loi = await _api("GET", "/v2/order/api/customers/search.json",
                        params={"query": q, "limit": limit})
    if loi:
        return None, loi
    ds = d.get("customers") if isinstance(d, dict) else d
    return ds if isinstance(ds, list) else [], None


def _gon_dia_chi(a):
    if not isinstance(a, dict):
        return a
    return {"address_id": a.get("id"), "customer_id": a.get("customer_id"),
            "ten": a.get("name"), "sdt": a.get("phone"), "so_nha_duong": a.get("address1"),
            "phuong_xa": a.get("ward"), "quan_huyen": a.get("province"),
            "tinh_thanh": a.get("city"), "mac_dinh": a.get("default")}


def _gon_khach(c):
    if not isinstance(c, dict):
        return c
    return {"customer_id": c.get("id"), "ten": c.get("name") or " ".join(
        x for x in (c.get("first_name"), c.get("last_name")) if x), "sdt": c.get("phone"),
        "dia_chi_mac_dinh": _gon_dia_chi(c.get("default_address")),
        "cac_dia_chi": [_gon_dia_chi(a) for a in c.get("addresses") or []]}


async def _customers(args, ctx):
    args = args or {}
    act = _str(args, "action", "search").lower()

    if act == "list":
        d, loi = await _api("GET", "/v2/order/api/customers.json",
                            params={"limit": _int(args, "limit", 20, 1, 100),
                                    "page": _int(args, "page", 1, 1, 10000)})
        if loi:
            return _loi(loi)
        ds = d.get("customers") if isinstance(d, dict) else None
        return _ra({"total": (d or {}).get("total"), "customers": [_gon_khach(c) for c in ds]}
                   if isinstance(ds, list) else d)

    if act == "search":
        q = _str(args, "query")
        if not q:
            return _loi("thiếu 'query' (tên hoặc số điện thoại).")
        if len(re.sub(r"\D", "", q)) >= 9:
            q = _sdt(q)
        ds, loi = await _tim_khach(q, _int(args, "limit", 20, 1, 100))
        return _loi(loi) if loi else _ra(
            {"so_khach": len(ds), "customers": [_gon_khach(c) for c in ds]},
            "Tìm TRƯỚC khi tạo khách mới: sàn không có đường sửa hay xoá khách hàng. Lên đơn "
            "cần address_id của địa chỉ giao hàng, lấy ở dia_chi_mac_dinh hoặc cac_dia_chi.")

    if act == "parse_address":
        dc = _str(args, "address")
        if not dc:
            return _loi("thiếu 'address' (dán nguyên đoạn tin nhắn của khách).")
        cua_naota = await _tim_dia_chi(dc)
        cua_san, loi_san = await _api("PUT", "/v2/order/api/address_parse.json",
                                      params={"address": dc})
        ra = {"naota_tim_thay": cua_naota,
              "san_tach_duoc": cua_san if not loi_san else f"lỗi: {loi_san}",
              "sdt_trong_tin": [_sdt(x) for x in re.findall(r"(?:\+?84|0)[\d .]{8,12}\d", dc)]}
        if isinstance(cua_san, dict) and isinstance(cua_naota, dict) and cua_naota.get("quan") \
                and cua_san.get("province") and cua_san.get("province") != cua_naota.get("quan"):
            ra["CANH_BAO"] = (f"Hai bộ tách ra hai quận khác nhau: Naota đọc "
                              f"'{cua_naota.get('quan')}', sàn đọc '{cua_san.get('province')}'. "
                              "Hỏi lại khách.")
        return _ra(ra, "Ưu tiên 'naota_tim_thay' vì nó so với danh mục của sàn theo cụm từ "
                       "nguyên vẹn; bộ tách của sàn từng đọc 'Quận 1' thành 'Q. 12'. Trên sàn "
                       "này tinh_thanh đi vào trường city, quan_huyen đi vào trường province. "
                       "chac_chan=false hoặc có ung_vien thì HỎI LẠI khách, đừng tự chọn. Số "
                       "nhà và tên đường tự đọc từ tin nhắn. Luôn đọc lại địa chỉ cho khách "
                       "xác nhận: đơn đã tạo thì không sửa được.")

    if act == "check_address":
        kq = await _khop_dia_chi(_str(args, "province"), _str(args, "district"),
                                 _str(args, "ward"))
        return _ra(kq, "ok=true là địa chỉ đã khớp đúng tên trong danh mục của sàn, dùng nguyên "
                       "văn các tên đó. ok=false thì chọn trong ung_vien cùng khách.")

    if act == "locations":
        m, loi = await _danh_muc()
        if loi:
            return _loi(loi)
        tinh = _str(args, "province")
        if not tinh:
            return _ra({"tinh_thanh": sorted(m)}, "Truyền province (tên tỉnh) để xem quận và "
                                                  "phường của tỉnh đó.")
        t, ung = _chon(tinh, list(m), _BI_DANH_TINH)
        return _ra({t: m[t]} if t else {"ung_vien_tinh": ung})

    return _loi("action phải là: search | list | parse_address | check_address | locations")


async def _customer_write(args, ctx):
    args = args or {}
    act = _str(args, "action", "create").lower()
    raw = _obj(args, "raw_body")

    if act in ("create", "add_address") and raw is None:
        kq = await _khop_dia_chi(_str(args, "province"), _str(args, "district"),
                                 _str(args, "ward"))
        if not kq.get("ok"):
            return _loi("địa chỉ chưa khớp danh mục của sàn, CHƯA tạo gì cả. Chọn lại cùng "
                        "khách rồi gọi lại: " + json.dumps(kq, ensure_ascii=False)[:1500])
        if not _str(args, "address1"):
            return _loi("thiếu 'address1' (số nhà, tên đường, thôn/xóm).")
        dia_chi = {"address1": _str(args, "address1"),
                   # Trên sàn TTS: city = TỈNH/THÀNH, province = QUẬN/HUYỆN.
                   "city": kq["tinh"], "province": kq["quan"], "ward": kq["phuong"]}

    if act == "create":
        if raw is not None:
            than = raw
        else:
            ten, sdt = _str(args, "name"), _sdt(_str(args, "phone"))
            if not ten or len(sdt) < 9:
                return _loi("thiếu 'name' hoặc 'phone' hợp lệ. Có đoạn tin nhắn thô thì chạy "
                            "tts_customers action=parse_address trước.")
            # Sàn không cho xoá khách, nên chốt chống trùng nằm trong mã chứ không chỉ trong
            # lời dặn model: số điện thoại đã có thì dừng, trừ khi người dùng nói rõ là muốn.
            if not args.get("allow_duplicate"):
                ds, loi = await _tim_khach(sdt)
                if loi:
                    return _loi(f"không kiểm được khách trùng nên CHƯA tạo: {loi}")
                trung = [c for c in ds if _sdt(c.get("phone")) == sdt]
                if trung:
                    return _ra({"da_tao": False, "khach_da_co": [_gon_khach(c) for c in trung]},
                               "Số điện thoại này đã có khách, KHÔNG tạo mới. Dùng customer_id "
                               "và address_id sẵn có. Địa chỉ khác thì action=add_address. "
                               "Chắc chắn muốn khách thứ hai thì gọi lại với "
                               "allow_duplicate=true.")
            ho_ten = ten.split()
            than = {"customer": {
                "name": ten, "phone": sdt,
                "first_name": ho_ten[0], "last_name": " ".join(ho_ten[1:]),
                # Ghi rõ tên và số điện thoại vào địa chỉ: thiếu hai trường này thì sàn tự điền
                # tên người nhận từ last_name, tức "Hoàng Ngọc Vương" thay vì "Hoàng Ngọc Vương".
                "addresses": [{**dia_chi, "name": ten, "phone": sdt}], "dropship": True,
            }}
        d, loi = await _api("POST", "/v2/order/api/customers.json", body=than)
        if loi:
            return _loi(loi)
        kh = d.get("customer") if isinstance(d, dict) else None
        return _ra({"da_tao": True, "khach": _gon_khach(kh) if kh else d},
                   "Đã tạo khách. Lên đơn dùng address_id trong dia_chi_mac_dinh. Sàn KHÔNG có "
                   "đường sửa hay xoá khách: sai địa chỉ thì add_address rồi set_default.")

    if act == "add_address":
        cid = _str(args, "customer_id")
        if not cid:
            return _loi("thiếu 'customer_id'.")
        if raw is not None:
            than = raw
        else:
            than = {"address": {**dia_chi, "customer_id": cid, "name": _str(args, "name"),
                                "phone": _sdt(_str(args, "phone")), "dropship": True}}
        d, loi = await _api("POST", f"/v2/order/api/customers/{cid}/addresses.json", body=than)
        if loi:
            return _loi(loi)
        a = d.get("customer_address") if isinstance(d, dict) else None
        return _ra(_gon_dia_chi(a) if a else d, "Muốn dùng làm địa chỉ giao mặc định thì "
                                               "action=set_default với address_id này.")

    if act == "set_default":
        cid, aid = _str(args, "customer_id"), _str(args, "address_id")
        if not cid or not aid:
            return _loi("thiếu 'customer_id' hoặc 'address_id'.")
        d, loi = await _api(
            "PUT", f"/v2/order/api/customers/{cid}/addresses/{aid}/default.json", body={})
        if loi:
            return _loi(loi)
        a = d.get("customer_address") if isinstance(d, dict) else None
        return _ra(_gon_dia_chi(a) if a else d)

    return _loi("action phải là: create | add_address | set_default")


# ============================================================
# NHÓM D: vận chuyển và tạo đơn
# ============================================================
def _rate_sang_line(rate, sdt, ncc_tra=False):
    """Một mục báo giá ship -> một dòng `shipping_lines` của đơn.

    Chép đúng hàm shippingRateToShippingLine của web sàn. Bản 1.0.x bảo model đưa NGUYÊN mục
    báo giá vào đơn, trong khi sàn cần hình dạng khác hẳn (code, title, price, source...)."""
    if not isinstance(rate, dict):
        return None
    if "service_code" not in rate and "code" in rate:
        return rate
    ten = str(rate.get("service_name") or "")
    gia = rate.get("total_price")
    return {"carrier_identifier": None, "code": rate.get("service_code"),
            "delivery_category": None, "discounted_price": 0, "id": "", "phone": sdt,
            "price": gia, "requested_fulfillment_service_id": None,
            "source": ten.split(" - ")[0], "title": ten,
            "pay_by": "dropshipper" if ncc_tra else None,
            "__pay_amount": gia if ncc_tra else None}


async def _shipping_rates(args, ctx):
    args = args or {}
    if _obj(args, "raw_body") is not None:
        than = _obj(args, "raw_body")
    else:
        aid = _str(args, "customer_address_id")
        items = _obj(args, "items")
        sid = _str(args, "shop_id")
        if not aid:
            return _loi("thiếu 'customer_address_id': address_id của địa chỉ giao hàng, lấy từ "
                        "tts_customers (dia_chi_mac_dinh.address_id).")
        if not isinstance(items, list) or not items:
            return _loi("thiếu 'items': mảng {product_id, variant_id, quantity, "
                        "dropship_selling_price}.")
        if not sid:
            return _loi("thiếu 'shop_id' (kho gửi hàng, tức nhà cung cấp).")
        than = {"rate": {
            "destination": {"customer_address_id": aid},
            "items": [{"product_id": i.get("product_id"), "variant_id": i.get("variant_id"),
                       "quantity": i.get("quantity") or 1,
                       "dropship_selling_price": i.get("dropship_selling_price"),
                       "dropship": True} for i in items if isinstance(i, dict)],
            "origin": {"shop_id": sid},
            "cod": _str(args, "payment_method", "cod").lower() == "cod"}}
    # Báo giá không ghi gì lên sàn, gửi lại vô hại.
    d, loi = await _api("POST", "/v2/order/api/shipping_rates.json", body=than, an_toan_lap=True)
    if loi:
        return _loi(loi)
    rates = d.get("rates") if isinstance(d, dict) else None
    if rates is None and isinstance(d, dict) and isinstance(d.get("data"), dict):
        rates = d["data"].get("rates")
    if not isinstance(rates, list):
        return _ra(d)
    gon = [{"stt": i, "hang_van_chuyen": r.get("service_name"), "phi": r.get("total_price"),
            "service_code": r.get("service_code")} for i, r in enumerate(rates)]
    return _ra({"lua_chon": gon, "rates": rates},
               "Đưa NGUYÊN một mục trong 'rates' vào tham số 'shipping_rate' của "
               "tts_create_order. Naota tự đổi sang dạng shipping_lines mà sàn cần. Web sàn "
               "mặc định chọn mục đầu tiên.")


_vua_tao = {}   # dấu vân tay đơn -> (thời điểm, mã đơn)


def _van_tay(don):
    return hashlib.sha256(json.dumps(
        {k: don.get(k) for k in ("shop_id", "customer", "line_items", "shipping_address")},
        sort_keys=True, default=str).encode()).hexdigest()


async def _chuan_don(ctx, o, cart_token, nho):
    """Dựng thân một đơn giống hệt web sàn. Trả (đơn, xem_trước, lỗi)."""
    if not isinstance(o, dict):
        return None, None, "mỗi đơn phải là object"
    if isinstance(o.get("raw_body"), dict):
        don = dict(o["raw_body"])
        return don, {"raw_body": True, "shop_id": don.get("shop_id"),
                     "canh_bao": "thân đơn tự dựng, Naota không kiểm được gì"}, None
    sid = str(o.get("shop_id") or "").strip()
    if not sid:
        return None, None, ("mỗi đơn phải có 'shop_id'. Một nhà cung cấp là MỘT đơn riêng, giỏ "
                            "nhiều shop thì truyền mảng 'orders'.")
    dong = [i for i in (o.get("line_items") or []) if isinstance(i, dict)]
    if not dong:
        return None, None, f"đơn của shop {sid} chưa có 'line_items'."

    # Soi từng dòng với sàn: variant có thật, đúng shop, giá bán không dưới giá nhập.
    hang, tong_ban, tong_von, canh = [], 0.0, 0.0, []
    line_items = []
    for i in dong:
        pid, vid = str(i.get("product_id") or ""), str(i.get("variant_id") or "")
        if not pid or not vid:
            return None, None, "mỗi dòng hàng phải có product_id và variant_id."
        sp, loi = await _san_pham(ctx, pid, nho)
        if loi:
            return None, None, loi
        v = _bien_the(sp, vid)
        if not v:
            return None, None, (f"sản phẩm {pid} không có variant {vid}. Variant đang có: "
                                + json.dumps(_cac_bien_the(sp), ensure_ascii=False))
        if str(sp.get("shop_id") or sid) != sid:
            return None, None, (f"'{sp.get('title')}' thuộc shop {sp.get('shop_id')}, không "
                                f"phải shop {sid}. Mỗi shop là một đơn riêng.")
        sl = int(_so(i.get("quantity"), 1)) or 1
        gia = i.get("dropship_selling_price")
        if gia in (None, ""):
            return None, None, f"dòng '{v.get('title')}' thiếu dropship_selling_price."
        if _so(gia) < _so(v.get("dropship_price")):
            return None, None, (f"giá bán {_tien(gia)} thấp hơn giá nhập "
                                f"{_tien(v.get('dropship_price'))} của '{sp.get('title')} - "
                                f"{v.get('title')}'.")
        if v.get("inventory_quantity") is not None and sl > _so(v.get("inventory_quantity")):
            canh.append(f"'{v.get('title')}' đặt {sl} nhưng kho còn {v.get('inventory_quantity')}")
        tong_ban += sl * _so(gia)
        tong_von += sl * _so(v.get("dropship_price"))
        hang.append({"san_pham": sp.get("title"), "phan_loai": v.get("title"), "so_luong": sl,
                     "gia_ban": _tien(gia), "gia_nhap": _tien(v.get("dropship_price"))})
        line_items.append({"quantity": sl, "variant_id": vid, "product_id": pid,
                           "dropship_selling_price": _so(gia), "dropship": True,
                           "properties": i.get("properties")})

    tt = str(o.get("payment_method") or "cod").lower()
    don = {"dropship": True, "note": str(o.get("note") or ""), "shop_id": sid,
           "line_items": line_items, "payment_method": tt,
           "discount_codes": [{"price_rule": x} for x in (o.get("price_rule_ids") or [])]
           or [x for x in (o.get("discount_codes") or []) if isinstance(x, dict)]}
    if o.get("cart_token") or cart_token:
        don["cart_token"] = o.get("cart_token") or cart_token
    if o.get("source_name"):
        don["source_name"] = o["source_name"]

    xem = {"shop_id": sid, "nha_cung_cap": ((nho.get(line_items[0]["product_id"]) or {})
                                            .get("shop") or {}).get("name"),
           "hang": hang, "thanh_toan": tt, "ghi_chu": don["note"]}

    if o.get("marketplace") or o.get("source_identifier"):
        # Đơn từ sàn khác (TikTok Shop...): sàn nhận customer=null kèm source_identifier.
        don.update(customer=None, source_identifier=str(o.get("source_identifier") or ""),
                   shipping={"method": "marketplace", "pay_by": "buyer", "price": 0,
                             "carrier": str(o.get("marketplace") or "marketplace")})
        xem.update(nguoi_nhan="đơn từ sàn khác", ma_don_san_kia=don["source_identifier"],
                   tien_hang=_tien(tong_ban), lai_uoc_tinh=_tien(tong_ban - tong_von))
        if canh:
            xem["canh_bao"] = canh
        return don, xem, None

    sa = o.get("shipping_address") if isinstance(o.get("shipping_address"), dict) else None
    if not sa:
        sdt, aid = _sdt(o.get("customer_phone")), str(o.get("customer_address_id") or "")
        if not sdt:
            return None, None, ("chưa có người nhận. Truyền 'customer_phone' (kèm "
                                "'customer_address_id' nếu khách có nhiều địa chỉ), hoặc "
                                "nguyên object 'shipping_address' lấy từ tts_customers.")
        ds, loi = await _tim_khach(sdt)
        if loi:
            return None, None, loi
        kh = [c for c in ds if _sdt(c.get("phone")) == sdt]
        if o.get("customer_id"):
            kh = [c for c in kh if str(c.get("id")) == str(o["customer_id"])] or kh
        if not kh:
            return None, None, (f"không có khách nào số {sdt}. Tạo bằng tts_customer_write "
                                "action=create trước.")
        if len(kh) > 1 and not o.get("customer_id"):
            return None, None, ("có nhiều khách cùng số này, truyền thêm 'customer_id': "
                                + json.dumps([_gon_khach(c) for c in kh], ensure_ascii=False))
        c = kh[0]
        ds_dc = list(c.get("addresses") or [])
        if isinstance(c.get("default_address"), dict):
            ds_dc.insert(0, c["default_address"])
        sa = next((a for a in ds_dc if not aid or str(a.get("id")) == aid), None)
        if not sa:
            return None, None, (f"khách {sdt} không có địa chỉ {aid}. Địa chỉ đang có: "
                                + json.dumps([_gon_dia_chi(a) for a in ds_dc],
                                             ensure_ascii=False))
        sa = dict(sa)
        sa.setdefault("customer_id", c.get("id"))
    cid = str(o.get("customer_id") or sa.get("customer_id") or "")
    if not cid or not sa.get("id"):
        return None, None, ("địa chỉ giao hàng phải là địa chỉ ĐÃ LƯU của khách (có id và "
                            "customer_id). Lấy nguyên từ tts_customers.")
    ten_nhan = str(o.get("recipient_name") or "").strip()
    if ten_nhan:
        # Địa chỉ đã lưu mang tên sai (khách tạo trước bản 1.1.1 hay tạo trên web sàn) thì sửa
        # đúng tên người nhận của ĐƠN NÀY, không phải tạo lại khách.
        sa = {**sa, "name": ten_nhan}
    don.update(customer={"id": cid}, shipping_address=sa)

    ncc_tra = bool(o.get("dropshipper_pays_shipping"))
    lines = []
    if isinstance(o.get("shipping_rate"), dict):
        lines = [_rate_sang_line(o["shipping_rate"], sa.get("phone"), ncc_tra)]
    elif isinstance(o.get("shipping_lines"), list):
        lines = [_rate_sang_line(x, sa.get("phone"), ncc_tra) for x in o["shipping_lines"]]
    lines = [x for x in lines if x]
    if not lines:
        return None, None, (f"đơn của shop {sid} chưa có phí ship. Gọi tts_shipping_rates rồi "
                            "đưa một mục trong 'rates' vào 'shipping_rate'.")
    don["shipping_lines"] = lines
    ship = sum(_so(x.get("price")) for x in lines)
    khach_tra = tong_ban + (0 if ncc_tra else ship)
    xem.update(
        nguoi_nhan=sa.get("name"), sdt=sa.get("phone"),
        dia_chi=", ".join(str(x) for x in (sa.get("address1"), sa.get("ward"),
                                           sa.get("province"), sa.get("city")) if x),
        van_chuyen=lines[0].get("title"), phi_ship=_tien(ship),
        ai_tra_ship="bạn (trừ vào lãi)" if ncc_tra else "khách (cộng vào tiền thu hộ)",
        tien_hang=_tien(tong_ban), khach_tra_uoc_tinh=_tien(khach_tra),
        tien_nhap=_tien(tong_von),
        lai_uoc_tinh=_tien(tong_ban - tong_von - (ship if ncc_tra else 0)))
    if canh:
        xem["canh_bao"] = canh
    return don, xem, None


async def _create_order(args, ctx):
    args = args or {}
    nhieu = _obj(args, "orders")
    danh_sach = nhieu if isinstance(nhieu, list) else [args]
    cart_token = ""
    if not all(isinstance(o, dict) and (o.get("cart_token") or o.get("raw_body"))
               for o in danh_sach):
        # Web sàn luôn gửi token của giỏ. Lấy sẵn ở đây để model không phải nhớ.
        cart, loi = await _doc_gio()
        if not loi and isinstance(cart, dict):
            cart_token = cart.get("token") or ""
    nho, don_list, xem_list = {}, [], []
    for o in danh_sach:
        don, xem, loi = await _chuan_don(ctx, o, cart_token, nho)
        if loi:
            return _loi(loi + " CHƯA tạo đơn nào.")
        don_list.append(don)
        xem_list.append(xem)

    if not args.get("confirm"):
        return _ra({"so_don_se_tao": len(don_list), "cac_don": xem_list, "da_thuc_thi": False},
                   "ĐÂY MỚI LÀ BẢN XEM TRƯỚC, chưa có đơn nào được tạo. Đọc lại cho người dùng: "
                   "tên, số điện thoại, địa chỉ đầy đủ, từng món, phí ship, tổng khách trả và "
                   "lãi. Đơn đã tạo thì sàn KHÔNG cho sửa, chỉ có huỷ rồi lên lại. Đồng ý rồi "
                   "thì gọi lại ĐÚNG các tham số này kèm confirm=true.")

    ket_qua = []
    for don in don_list:
        vt = _van_tay(don)
        cu = _vua_tao.get(vt)
        if cu and time.time() - cu[0] < 1800 and not args.get("allow_repeat"):
            ket_qua.append({"shop_id": don.get("shop_id"), "ok": False,
                            "loi": f"đơn y hệt vừa tạo lúc nãy (mã {cu[1]}), bỏ qua để khỏi "
                                   "trùng. Khách đặt thêm thật thì gọi lại với allow_repeat=true."})
            continue
        d, loi = await _api("POST", "/v2/order/api/orders.json", body={"order": don})
        if loi:
            ket_qua.append({"shop_id": don.get("shop_id"), "ok": False, "loi": loi})
            continue
        # Web sàn đọc `.data.order` của axios, tức khoá `order` ở GỐC thân trả về. Bản 1.0.x đọc
        # `data.order` nên luôn báo mã đơn rỗng dù đơn đã tạo.
        tao = None
        if isinstance(d, dict):
            tao = d.get("order")
            if not isinstance(tao, dict) and isinstance(d.get("data"), dict):
                tao = d["data"].get("order")
            if not isinstance(tao, dict):
                tao = None
        ma =(tao or {}).get("name") or (tao or {}).get("id")
        _vua_tao[vt] = (time.time(), ma)
        ket_qua.append({"shop_id": don.get("shop_id"), "ok": True, "ma_don": ma,
                        "order_id": (tao or {}).get("id"),
                        "trang_thai": (tao or {}).get("status_label"),
                        "tong_tien": (tao or {}).get("total_price"),
                        "order": tao if tao else d})
    xong = sum(1 for k in ket_qua if k["ok"])
    return _ra({"da_thuc_thi": True, "thanh_cong": xong, "that_bai": len(ket_qua) - xong,
                "chi_tiet": ket_qua},
               ("Tất cả các đơn đã tạo. Xem lãi thật bằng tts_orders action=get." if xong == len(
                   ket_qua) else
                "MỘT SỐ ĐƠN LỖI. Các đơn đã tạo là THẬT và không tự huỷ, đừng gọi lại cả lượt: "
                "xem lỗi từng shop, kiểm tts_orders action=list trước khi lên lại đúng shop báo "
                "ok=false."))


async def _cancel_order(args, ctx):
    args = args or {}
    oid = _str(args, "order_id")
    ly_do = _str(args, "reason")
    if not oid:
        return _loi("thiếu 'order_id'.")
    if not ly_do:
        return _loi("thiếu 'reason' (lý do huỷ, sàn bắt buộc).")
    if not args.get("confirm"):
        return _ra({"se_huy_don": oid, "ly_do": ly_do, "da_thuc_thi": False},
                   "Đây mới là bản xem trước. Huỷ đơn là dứt điểm, không khôi phục lại được, và "
                   "huỷ nhiều lần ảnh hưởng uy tín tài khoản bán. Gọi lại với confirm=true nếu "
                   "chắc chắn.")
    d, loi = await _api("POST", f"/v2/order/api/orders/{oid}/confirmed_cancelled.json",
                        body={"order": {"id": oid, "confirm_status": "cancelled",
                                        "confirm_cancelled_reason": ly_do}})
    return _loi(loi) if loi else _ra(d, "Đã gửi yêu cầu huỷ.")


# ============================================================
# NHÓM E: đơn hàng
# ============================================================
_TRANG_THAI = ("any", "wait_confirm", "wait_checkout", "wait_pickup", "in_transit",
               "delivered", "wait_rate", "rated", "cancelled")


async def _orders(args, ctx):
    args = args or {}
    act = _str(args, "action", "list").lower()

    if act == "list":
        tt = _str(args, "buyer_status", "any")
        if tt not in _TRANG_THAI:
            return _loi("buyer_status phải là một trong: " + ", ".join(_TRANG_THAI))
        qs = _build_qs({"buyer_status": tt, "query": _str(args, "query"),
                        "page": _int(args, "page", 1, 1, 10000),
                        "limit": _int(args, "limit", 20, 1, 100), "dropship": "true"})
        d, loi = await _gql(ctx, "OrderListQuery", {"query": qs})
        return _loi(loi) if loi else _ra(d, "total_price là tiền khách trả. dropship_profit là "
                                            "lãi của đơn. Chi tiết và hoa hồng: action=get.")

    oid = _str(args, "order_id")
    if act == "get":
        if not oid:
            return _loi("thiếu 'order_id'.")
        d, loi = await _api("GET", f"/v2/order/api/orders/{oid}.json")
        return _loi(loi) if loi else _ra(d, "Trong đây có khối hoa hồng: tổng giá bán, tổng giá "
                                            "NCC, lợi nhuận bán hàng, tổng thưởng, phí vận "
                                            "chuyển bạn tài trợ và tổng lợi nhuận. Đây mới là "
                                            "lãi THẬT của đơn.")
    if act == "tracking":
        if not oid:
            return _loi("thiếu 'order_id'.")
        d, loi = await _api("GET", f"/v2/order/api/orders/{oid}/fulfillment_events.json")
        return _loi(loi) if loi else _ra(d)

    return _loi("action phải là: list | get | tracking")


async def _order_action(args, ctx):
    args = args or {}
    act = _str(args, "action").lower()
    oid = _str(args, "order_id")
    if not oid:
        return _loi("thiếu 'order_id'.")

    if act == "rate":
        diem = _int(args, "rating", 5, 1, 5)
        noi_dung = _str(args, "content")
        if not args.get("confirm"):
            return _ra({"se_danh_gia_don": oid, "so_sao": diem, "noi_dung": noi_dung,
                        "da_thuc_thi": False},
                       "Đây mới là bản xem trước. Đánh giá chỉ gửi được MỘT LẦN, không sửa được, "
                       "và nó mở khoá tiền đối soát của đơn. Gọi lại với confirm=true nếu chắc "
                       "chắn.")
        than = _obj(args, "raw_body") or {"order_id": oid, "rating": diem, "content": noi_dung}
        d, loi = await _api("POST", "/v1/review/ratings", body=than)
        return _loi(loi) if loi else _ra(d, "Đã gửi đánh giá.")

    if act == "ticket":
        mo_ta = _str(args, "description")
        loai = _str(args, "type", "other")
        if not mo_ta:
            return _loi("thiếu 'description' (mô tả vấn đề của đơn).")
        if not args.get("confirm"):
            return _ra({"se_mo_khieu_nai_cho_don": oid, "loai": loai, "mo_ta": mo_ta,
                        "da_thuc_thi": False},
                       "Đây mới là bản xem trước. Khiếu nại gửi đi là sàn và nhà cung cấp đều "
                       "thấy. Gọi lại với confirm=true nếu chắc chắn. Gói này chưa gửi kèm được "
                       "ảnh, cần ảnh thì mở khiếu nại thẳng trên web của sàn.")
        d, loi = await _api("POST", "/v2/order/api/orders-tickets.json",
                            multipart={"order_id": oid, "type": loai, "description": mo_ta})
        return _loi(loi) if loi else _ra(d, "Đã mở khiếu nại.")

    return _loi("action phải là: rate | ticket. Huỷ đơn dùng tool tts_cancel_order.")


# ============================================================
# NHÓM G: tài chính và tài khoản
# ============================================================
_TAI_CHINH = {
    "income": ("GET", "/v1/pay/api/finance/income_summary"),
    "wallet": ("GET", "/v1/pay/api/finance/wallet_transactions"),
    "wallet_types": ("GET", "/v1/pay/api/finance/transaction_types"),
    "escrow": ("GET", "/v1/pay/api/finance/escrow/transactions"),
    "escrow_statuses": ("GET", "/v1/pay/api/finance/escrow/transaction_statuses"),
    "tax": ("GET", "/v1/pay/api/finance/tax_payments"),
    "banks": ("GET", "/v1/pay/api/banks/my_accounts"),
    "withdraw_fee": ("GET", "/v1/pay/api/wallet/withdrawal_fee"),
    "affiliate": ("GET", "/v1/marketing/api/affiliate/statistic"),
    "profile": ("GET", "/v1/user/dropship-profile/me"),
    "streak": ("GET", "/v2/order/api/user/streak/stats.json"),
    "notifications": ("GET", "/v3/notification/notifications/count_unseen"),
}


async def _finance(args, ctx):
    args = args or {}
    act = _str(args, "action", "income").lower()
    if act not in _TAI_CHINH:
        return _loi("action phải là một trong: " + " | ".join(sorted(_TAI_CHINH)))
    method, path = _TAI_CHINH[act]
    p = {}
    for k in ("limit", "page", "offset", "from", "to", "status", "month", "year"):
        if _str(args, k):
            p[k] = _str(args, k)
    d, loi = await _api(method, path, params=p or None)
    if loi:
        return _loi(loi)
    ghi = ""
    if act == "withdraw_fee":
        ghi = ("Gói này CỐ Ý không có tool rút tiền. Muốn rút thì vào ví trên web của sàn, "
               "Naota chỉ đọc biểu phí.")
    elif act == "escrow":
        ghi = "Tiền theo từng đơn kèm ngày giải ngân. Đơn chưa đánh giá thì tiền còn bị giữ."
    return _ra(d, ghi)


# ============================================================
# Chẩn đoán
# ============================================================
_SOI = [
    ("hồ sơ tài khoản", "GET", "/v1/user/dropship-profile/me"),
    ("tiền chờ đối soát", "GET", "/v1/pay/api/finance/income_summary"),
    ("giỏ hàng", "GET", "/v2/order/api/carts.json"),
    ("danh sách khách", "GET", "/v2/order/api/customers.json"),
    ("danh mục tỉnh/quận/phường", "GET", "/v1/user/api/vi/locations.json"),
]


async def _health(args, ctx):
    conn = _conn()
    if not conn:
        return _loi(_check())
    sec = _secrets(conn)
    tok = (sec.get("access_token") or "").strip()
    con_lai = _con_lai(tok)
    bo_qua = []
    _gql_docs(ctx, bo_qua)
    bao = {
        "ket_noi": conn.get("label") or conn.get("id"),
        "muc_quyen_ket_noi": conn.get("perm"),
        # `_con_lai` trả -1 cho token KHÔNG ĐỌC ĐƯỢC HẠN, mà -1 cũng thoả `<= 0`. Hỏi "không
        # đọc được" trước để không báo nhầm một token dán thiếu thành "hết hạn".
        "token_con_lai": ("không đọc được hạn" if con_lai == -1 else
                          "hết hạn" if con_lai <= 0 else f"khoảng {con_lai // 3600} giờ"),
        "tu_gia_han": ("có (đã dán @refreshToken)" if (sec.get("refresh_token") or "").strip()
                       else "KHÔNG: chưa dán @refreshToken, token chết sau khoảng 3 ngày"),
        "rest": {},
        "graphql": {},
    }
    if bo_qua:
        bao["ban_sua_cu_bi_bo_qua"] = bo_qua
    for ten, method, path in _SOI:
        d, loi = await _api(method, path, params={"limit": 1} if "customers" in path else None)
        bao["rest"][ten] = "ok" if not loi else f"LỖI: {loi[:180]}"
    thu = {
        "searchProductsQuery": {"query": _build_qs(
            {"filter_only_dropship": "true", "keyword": "áo thun", "limit": 1, "offset": 0,
             "sort_by": "_score"})},
        "searchShopQuery": {"query": _build_qs({"keyword": "thời trang", "limit": 1,
                                                "offset": 0})},
        "OrderListQuery": {"query": _build_qs({"page": 1, "limit": 1, "dropship": "true"})},
    }
    for op, bien in thu.items():
        d, loi = await _gql(ctx, op, bien)
        bao["graphql"][op] = "ok" if not loi else f"LỖI: {loi[:220]}"
        if op == "searchProductsQuery" and not loi:
            sp = (((d or {}).get("searchProducts") or {}).get("products") or [{}])[0]
            if sp.get("id"):
                d2, loi2 = await _gql(ctx, "ProductById", {"id": str(sp["id"])})
                bao["graphql"]["ProductById"] = "ok" if not loi2 else f"LỖI: {loi2[:220]}"
    hong = [k for k, v in {**bao["rest"], **bao["graphql"]}.items() if str(v).startswith("LỖI")]
    return _ra(bao, ("Mọi đường đều sống: tìm hàng, giỏ hàng, khách hàng và đơn hàng dùng "
                     "được." if not hong else
                     "Đường hỏng: " + ", ".join(hong) + ". Lỗi GraphQL về tên trường thường tự "
                     "sửa ở lần gọi sau; còn lỗi thì dùng tts_graphql. Lỗi token thì lấy lại "
                     "@publicToken và @refreshToken. Đây là API nội bộ của sàn, không có tài "
                     "liệu chính thức và sàn có thể đổi bất cứ lúc nào."))


async def _graphql_doc(args, ctx):
    args = args or {}
    act = _str(args, "action", "show").lower()
    de = ctx.data_dir / "graphql.json"

    if act == "show":
        bo_qua = []
        return _ra({"dang_dung": _gql_docs(ctx, bo_qua),
                    "co_ban_sua_rieng": de.exists(),
                    "ban_sua_cu_bi_bo_qua": bo_qua,
                    "duong_dan_ban_sua": str(de)},
                   "Sửa bằng action=set (truyền 'operation' và 'doc', kèm 'root' nếu tên trường "
                   "gốc đổi). Quay về mặc định của gói bằng action=reset.")

    if act == "introspect":
        ten_type = _str(args, "type", "Query")
        truong, loi = await _kieu(ten_type)
        if loi:
            return _loi(loi)
        return _ra({"type": ten_type,
                    "truong": {k: (f"[{g}]" if l else g) + (" (đối tượng, cần khối con)"
                                                              if kind in _KIND_CO_CON else "")
                               for k, (g, kind, l) in truong.items()}},
                   "Đây là hình dạng THẬT sàn đang khai. Không truyền 'type' là xem các trường "
                   "gốc (Query). Ghi lại truy vấn bằng action=set.")

    if act == "set":
        op = _str(args, "operation")
        doc = _str(args, "doc")
        if not op or not doc:
            return _loi("thiếu 'operation' hoặc 'doc'.")
        if "query" not in doc and "mutation" not in doc:
            return _loi("'doc' phải là một tài liệu GraphQL (bắt đầu bằng query hoặc mutation).")
        patch = {"doc": doc}
        if _str(args, "root"):
            patch["root"] = _str(args, "root")
        vi_sao = _ghi_doc(ctx, op, patch)
        if vi_sao:
            return _loi(f"không ghi được bản sửa: {vi_sao}")
        return _ra({"da_luu": op, "duong_dan": str(de)},
                   "Bản sửa này nằm ngoài gói nên bản cập nhật gói sau đó không xoá mất (nhưng "
                   "gói mới hơn sẽ bỏ qua nó). Chạy tts_health_check để xem truy vấn đã chạy "
                   "chưa.")

    if act == "reset":
        try:
            if de.exists():
                de.unlink()
        except Exception as e:
            return _loi(f"không xoá được bản sửa: {type(e).__name__}: {e}")
        return _ra({"da_quay_ve_mac_dinh": True})

    return _loi("action phải là: show | introspect | set | reset")


# ============================================================
# Đăng ký
# ============================================================
def _t(ctx, name, desc, handler, min_mode, emoji, props, required=None):
    ctx.register_tool(name=name, description=desc, handler=handler, min_mode=min_mode,
                      emoji=emoji,
                      schema={"type": "object", "properties": props,
                              "required": list(required or [])},
                      check_fn=_check)


def register(ctx):
    _t(ctx, "tts_products",
       "TTS Dropship: tìm và đọc sản phẩm để bán dropship. action=search (từ khoá tiếng Việt có "
       "dấu được, lọc, sắp xếp theo dropship_profit để ra hàng lãi cao) | get (chi tiết 1 sản "
       "phẩm kèm từng variant màu/size, giá nhập, giá gợi ý, tồn kho) | reviews | recent | "
       "collections. dropship_price là giá nhập, market_price là giá bán gợi ý.",
       _products, "readonly", "🔎", {
           "action": {"type": "string", "enum": ["search", "get", "reviews", "recent", "collections"],
                      "description": "Mặc định search"},
           "keyword": {"type": "string", "description": "Từ khoá tìm (action=search)"},
           "product_id": {"type": "string",
                          "description": "Bắt buộc với action=get. Nhận id hoặc mã số"},
           "shop_id": {"type": "string", "description": "Lọc theo nhà cung cấp"},
           "collection_id": {"type": "string", "description": "Bỏ trống thì lấy trang chủ"},
           "sort_by": {"type": "string",
                       "enum": ["_score", "created_at", "total_sales", "dropship_profit", "price"],
                       "description": "Mặc định _score. dropship_profit = lãi cao nhất trước"},
           "ascending": {"type": "boolean", "description": "Sắp xếp tăng dần"},
           "category_lv1": {"type": "string"}, "category_lv2": {"type": "string"},
           "province": {"type": "string", "description": "Lọc theo tỉnh của kho hàng"},
           "limit": {"type": "integer", "description": "Mặc định 20, tối đa 100"},
           "offset": {"type": "integer"},
       })

    _t(ctx, "tts_suppliers",
       "TTS Dropship: nhà cung cấp. action=search | get (hồ sơ shop) | promotions (freeship và "
       "thưởng theo đơn, PHẢI cộng vào mới ra lợi nhuận thật) | following | check (đang theo dõi "
       "shop này chưa).",
       _suppliers, "readonly", "🏪", {
           "action": {"type": "string",
                      "enum": ["search", "get", "promotions", "following", "check"]},
           "shop_id": {"type": "string"}, "keyword": {"type": "string"},
           "province": {"type": "string"},
           "limit": {"type": "integer"}, "offset": {"type": "integer"},
       })

    _t(ctx, "tts_cart",
       "TTS Dropship: xem giỏ hàng, đã nhóm sẵn theo nhà cung cấp, kèm cart_token. Mỗi nhà cung "
       "cấp sẽ thành một đơn riêng khi lên đơn.",
       _cart, "readonly", "🧺", {})

    _t(ctx, "tts_customers",
       "TTS Dropship: khách hàng và địa chỉ (chỉ đọc). action=search (theo số điện thoại hoặc "
       "tên, LUÔN chạy trước khi tạo khách mới, trả về customer_id và address_id) | list | "
       "parse_address (dán nguyên tin nhắn của khách, tự tìm tỉnh, quận, phường theo danh mục "
       "của sàn) | check_address (kiểm tỉnh/quận/phường có đúng tên sàn dùng không) | locations.",
       _customers, "readonly", "👤", {
           "action": {"type": "string",
                      "enum": ["search", "list", "parse_address", "check_address", "locations"]},
           "query": {"type": "string", "description": "Số điện thoại hoặc tên (action=search)"},
           "address": {"type": "string",
                       "description": "Nguyên đoạn tin nhắn của khách (action=parse_address)"},
           "province": {"type": "string", "description": "Tỉnh/thành (check_address, locations)"},
           "district": {"type": "string", "description": "Quận/huyện (check_address)"},
           "ward": {"type": "string", "description": "Phường/xã (check_address)"},
           "limit": {"type": "integer"}, "page": {"type": "integer"},
       })

    _t(ctx, "tts_shipping_rates",
       "TTS Dropship: báo giá vận chuyển cho một đơn dự kiến, tới một địa chỉ đã lưu của khách. "
       "Trả về các hãng kèm phí. Đưa nguyên một mục trong 'rates' vào 'shipping_rate' của "
       "tts_create_order.",
       _shipping_rates, "readonly", "🚚", {
           "customer_address_id": {"type": "string",
                                   "description": "address_id của địa chỉ giao, từ tts_customers"},
           "items": {"type": "array", "items": {"type": "object"},
                     "description": "[{product_id, variant_id, quantity, dropship_selling_price}]"},
           "shop_id": {"type": "string", "description": "Kho gửi hàng, tức nhà cung cấp"},
           "payment_method": {"type": "string", "description": "Mặc định cod"},
           "raw_body": {"type": "object", "description": "Đè nguyên thân request khi sàn đổi hình dạng"},
       })

    _t(ctx, "tts_orders",
       "TTS Dropship: đọc đơn hàng. action=list (lọc theo buyer_status: wait_confirm, wait_pickup, "
       "in_transit, delivered, wait_rate, cancelled; tìm theo mã đơn hoặc tên khách) | get (chi "
       "tiết 1 đơn KÈM khối hoa hồng, đây mới là lãi thật) | tracking (hành trình và mã vận "
       "đơn). Chỉ đọc, không đổi gì.",
       _orders, "readonly", "📦", {
           "action": {"type": "string", "enum": ["list", "get", "tracking"]},
           "order_id": {"type": "string"},
           "buyer_status": {"type": "string", "enum": list(_TRANG_THAI),
                            "description": "Mặc định any"},
           "query": {"type": "string", "description": "Từ khoá: mã đơn hoặc tên khách"},
           "page": {"type": "integer"}, "limit": {"type": "integer"},
       })

    _t(ctx, "tts_finance",
       "TTS Dropship: tiền và tài khoản. action=income (tiền chờ đối soát, thuế tạm giữ, tiền rút "
       "được) | escrow (tiền theo từng đơn kèm ngày giải ngân) | wallet | tax | banks | "
       "withdraw_fee | affiliate | profile | streak | notifications. Không có đường rút tiền.",
       _finance, "readonly", "💰", {
           "action": {"type": "string", "enum": sorted(_TAI_CHINH)},
           "limit": {"type": "string"}, "page": {"type": "string"},
           "from": {"type": "string"}, "to": {"type": "string"},
           "month": {"type": "string"}, "year": {"type": "string"},
       })

    _t(ctx, "tts_listings",
       "TTS Dropship: xem các bài đăng bán (nội dung 'Đăng bán' của sàn) đã soạn cho một sản "
       "phẩm. Đọc trước khi viết bài mới để khỏi trùng nội dung. Soạn bài mới bằng "
       "tts_listing_write.",
       _listings, "readonly", "📝", {"product_id": {"type": "string"}}, ["product_id"])

    _t(ctx, "tts_wishlist",
       "TTS Dropship: sản phẩm đã lưu. action=list | check (sản phẩm này đã lưu chưa).",
       _wishlist, "readonly", "⭐", {
           "action": {"type": "string", "enum": ["list", "check"]},
           "product_id": {"type": "string"},
           "limit": {"type": "integer"}, "offset": {"type": "integer"},
       })

    _t(ctx, "tts_health_check",
       "TTS Dropship: kiểm tra kết nối còn sống không. Gọi thử các đường đọc chính (hồ sơ, giỏ, "
       "khách, tìm hàng, đơn hàng), báo đường nào hỏng, kèm hạn token và việc tự gia hạn. Chạy "
       "tool này trước khi kết luận là sàn đổi API.",
       _health, "readonly", "🩺", {})

    _t(ctx, "tts_cart_update",
       "TTS Dropship: thêm hàng vào giỏ, đổi số lượng, đổi giá bán, hoặc xoá dòng (quantity=0). "
       "Truyền kèm product_id để Naota kiểm variant có thật và giá bán không dưới giá nhập.",
       _cart_update, "safe", "🧺", {
           "items": {"type": "array", "items": {"type": "object"},
                     "description": "[{product_id, variant_id, quantity, dropship_selling_price, note}]"},
           "raw_body": {"type": "object", "description": "Đè nguyên thân request khi sàn đổi hình dạng"},
       })

    _t(ctx, "tts_customer_write",
       "TTS Dropship: tạo khách hàng và địa chỉ. action=create | add_address | set_default. "
       "Naota tự kiểm số điện thoại đã có khách chưa và tự đối chiếu tỉnh, quận, phường với "
       "danh mục của sàn trước khi tạo. Sàn KHÔNG có đường sửa hay xoá khách hàng.",
       _customer_write, "safe", "👤", {
           "action": {"type": "string", "enum": ["create", "add_address", "set_default"]},
           "name": {"type": "string", "description": "Tên người nhận"},
           "phone": {"type": "string"},
           "address1": {"type": "string", "description": "Số nhà, tên đường, thôn/xóm"},
           "province": {"type": "string", "description": "Tỉnh/thành"},
           "district": {"type": "string", "description": "Quận/huyện"},
           "ward": {"type": "string", "description": "Phường/xã"},
           "customer_id": {"type": "string"}, "address_id": {"type": "string"},
           "allow_duplicate": {"type": "boolean",
                               "description": "true = vẫn tạo dù số điện thoại đã có khách"},
           "raw_body": {"type": "object"},
       })

    _t(ctx, "tts_listing_write",
       "TTS Dropship: soạn bài đăng bán cho một sản phẩm. action=create (cần product_id) | "
       "update (cần post_id). Nội dung đưa vào tham số 'post'.",
       _listing_write, "safe", "📝", {
           "action": {"type": "string", "enum": ["create", "update"]},
           "product_id": {"type": "string"}, "post_id": {"type": "string"},
           "post": {"type": "object", "description": "Nội dung bài đăng"},
           "raw_body": {"type": "object"},
       })

    _t(ctx, "tts_wishlist_write",
       "TTS Dropship: lưu hoặc bỏ lưu một sản phẩm. action=add | remove.",
       _wishlist_write, "safe", "⭐", {
           "action": {"type": "string", "enum": ["add", "remove"]},
           "product_id": {"type": "string"},
       }, ["product_id"])

    _t(ctx, "tts_supplier_follow",
       "TTS Dropship: theo dõi một nhà cung cấp. Sàn dùng chung một đường cho theo dõi và bỏ "
       "theo dõi, gọi lại lần nữa là đảo trạng thái.",
       _supplier_follow, "safe", "🏪", {"shop_id": {"type": "string"}}, ["shop_id"])

    _t(ctx, "tts_graphql",
       "TTS Dropship: xem, SOI LƯỢC ĐỒ và sửa tài liệu truy vấn GraphQL của gói. Thường không cần "
       "vì gói tự sửa khi sàn đổi trường. action=show | introspect (xem type có trường gì THẬT) "
       "| set (cần operation và doc) | reset.",
       _graphql_doc, "safe", "🛠️", {
           "action": {"type": "string", "enum": ["show", "introspect", "set", "reset"]},
           "type": {"type": "string",
                    "description": "Tên type GraphQL cần soi, bỏ trống là Query"},
           "operation": {"type": "string",
                         "enum": ["searchProductsQuery", "ProductById", "searchShopQuery",
                                  "OrderListQuery"]},
           "doc": {"type": "string", "description": "Tài liệu GraphQL đầy đủ"},
           "root": {"type": "string", "description": "Tên trường gốc trong kết quả"},
       })

    _t(ctx, "tts_create_order",
       "TTS Dropship: TẠO ĐƠN HÀNG THẬT trên sàn. Hai bước bắt buộc: gọi lần đầu KHÔNG có confirm "
       "để lấy bản xem trước (người nhận, địa chỉ, từng món, phí ship, tổng khách trả, lãi), đọc "
       "lại cho người dùng xác nhận, rồi gọi lại đúng tham số đó với confirm=true. Sàn KHÔNG cho "
       "sửa đơn đã tạo. Mỗi nhà cung cấp là một đơn riêng: nhiều shop thì truyền mảng 'orders'.",
       _create_order, "full", "🧾", {
           "shop_id": {"type": "string", "description": "Nhà cung cấp của đơn này"},
           "customer_phone": {"type": "string",
                              "description": "SĐT khách đã lưu, Naota tự lấy địa chỉ giao"},
           "customer_address_id": {"type": "string",
                                   "description": "Chọn địa chỉ khi khách có nhiều địa chỉ"},
           "customer_id": {"type": "string"},
           "recipient_name": {"type": "string",
                              "description": "Tên người nhận đầy đủ, dùng khi tên trên địa chỉ đã lưu bị thiếu"},
           "shipping_address": {"type": "object",
                                "description": "Hoặc nguyên object địa chỉ đã lưu của khách"},
           "line_items": {"type": "array", "items": {"type": "object"},
                          "description": "[{product_id, variant_id, quantity, dropship_selling_price}]"},
           "shipping_rate": {"type": "object",
                             "description": "Nguyên một mục trong 'rates' của tts_shipping_rates"},
           "dropshipper_pays_shipping": {"type": "boolean",
                                         "description": "true = bạn trả ship (trừ vào lãi). "
                                                        "Mặc định khách trả"},
           "payment_method": {"type": "string", "description": "Mặc định cod"},
           "note": {"type": "string", "description": "Ghi chú cho nhà cung cấp"},
           "price_rule_ids": {"type": "array", "items": {"type": "string"},
                              "description": "id khuyến mãi của shop, từ tts_suppliers promotions"},
           "cart_token": {"type": "string", "description": "Bỏ trống, Naota tự lấy"},
           "source_name": {"type": "string"},
           "marketplace": {"type": "string",
                           "description": "Đơn từ sàn khác, ví dụ TikTok Shop"},
           "source_identifier": {"type": "string", "description": "Mã đơn bên sàn kia"},
           "orders": {"type": "array", "items": {"type": "object"},
                      "description": "Nhiều đơn một lượt, mỗi mục là một shop, cùng tham số như trên"},
           "confirm": {"type": "boolean",
                       "description": "Để trống hoặc false = chỉ xem trước. true = tạo đơn THẬT"},
           "allow_repeat": {"type": "boolean",
                            "description": "true = cho tạo lại một đơn y hệt đơn vừa tạo"},
           "raw_body": {"type": "object"},
       })

    _t(ctx, "tts_cancel_order",
       "TTS Dropship: HUỶ một đơn. Hai bước: gọi lần đầu không có confirm để xem trước, rồi gọi "
       "lại với confirm=true. Huỷ là dứt điểm, không khôi phục lại được.",
       _cancel_order, "full", "🚫", {
           "order_id": {"type": "string"},
           "reason": {"type": "string", "description": "Lý do huỷ, sàn bắt buộc"},
           "confirm": {"type": "boolean"},
       }, ["order_id", "reason"])

    _t(ctx, "tts_order_action",
       "TTS Dropship: hành động trên một đơn đã giao. action=rate (đánh giá, chỉ gửi được một "
       "lần và nó mở khoá tiền đối soát) | ticket (mở khiếu nại với sàn). Cả hai đều bắt "
       "confirm=true ở lần gọi thứ hai.",
       _order_action, "full", "⭐", {
           "action": {"type": "string", "enum": ["rate", "ticket"]},
           "order_id": {"type": "string"},
           "rating": {"type": "integer", "description": "1 tới 5 sao (action=rate)"},
           "content": {"type": "string", "description": "Nội dung đánh giá"},
           "description": {"type": "string", "description": "Mô tả vấn đề (action=ticket)"},
           "type": {"type": "string", "description": "Loại khiếu nại"},
           "confirm": {"type": "boolean"},
           "raw_body": {"type": "object"},
       }, ["action", "order_id"])

    _t(ctx, "tts_listing_delete",
       "TTS Dropship: xoá một bài đăng bán. Bắt confirm=true ở lần gọi thứ hai.",
       _listing_delete, "full", "🗑️", {
           "post_id": {"type": "string"}, "confirm": {"type": "boolean"},
       }, ["post_id"])
