"""Kiểm mọi gói trong kho trước khi trộn. Chạy tay hoặc để CI chạy trên mỗi Pull Request:

    python tools/kiem-tra.py

Không chạm mạng, không cần thư viện ngoài.

Vì sao repo này cần một trình kiểm
----------------------------------
Kho là DỮ LIỆU MÀ NGƯỜI DÙNG SẼ CÀI, và nó tới máy họ mà không qua một bản Naota mới. Nghĩa là
không có lần review nào của app đứng chắn phía sau: sửa một dòng trong `packs/` là mọi máy đang
chạy Naota thấy ngay ở lần làm mới danh mục kế tiếp.

Điều đó đặc biệt đúng với PHÂN LOẠI QUYỀN. Naota xếp một tool vào ba nhóm đọc / ghi / nguy hiểm,
và mức "Ghi nháp" tự chạy được mọi thứ trong nhóm ghi. Nhưng `mcp_catalog.classify` KHÔNG có
nhánh nào tự đoán ra "nguy hiểm": tool nào không được khuôn khai rõ thì cùng lắm rơi vào nhóm
ghi. Nên một tool xoá dữ liệu hay tiêu tiền mà khuôn quên khai `danger` sẽ tự chạy được ở mức
Ghi nháp, im lặng, cho tới lúc nó xoá thật.

Trước 1.0.0 những phép kiểm này nằm trong repo NAOTA (`test_hostinger_connector.py`,
`test_n8n_connector.py`, `test_shopify_mcp.py`, `test_webcake_env.py`). Khuôn connector dọn sang
đây thì phép kiểm dọn theo - giữ lại bên đó chỉ canh được bản chụp lúc dọn nhà, không canh được
thứ người dùng thật sự cài.

Kiểm những gì
-------------
1. Cấu trúc gói: manifest đọc được, id khớp tên thư mục, tệp khai trong `provides` có thật.
2. Khuôn connector: JSON hợp lệ, đủ trường bắt buộc, icon hợp lệ (xem `tu-catalog.py`).
3. AN TOÀN: mặc định chỉ đọc, và không tool nào có tên kiểu phá huỷ / tiêu tiền mà lại nằm ở
   nhóm đọc hay ghi.
4. Bí mật: không nhét credential vào `url` (Naota không che `url`, nó ra thẳng giao diện và log).
5. Danh mục: mọi mục trong `index.json` có gói thật, có tệp zip thật, sha256 và size khớp,
   nội dung zip khớp thư mục nguồn, và mục kết nối có `icon` trỏ vào logo thật nằm trong gói.
6. Không có ký tự em dash (luật của chủ kho, vì nó làm trình đọc màn hình vấp).
7. MCP của bên thứ 3 chạy qua npx/uvx đi theo bản chính thức mới nhất (`@latest`), không chạy code
   chưa phát hành trên GitHub. Lý do và ngoại lệ ở `ban_chinh_thuc.py`.
8. Tệp nối MCP chính chủ chạy từ xa (`chinh-chu/*.json`) đúng cấu trúc và trỏ đúng khuôn. Lý do ở
   `chinh_chu.py`.
9. MCP kho tự build trong `mcp/` khớp sha256 đã ghi, và connector chỉ trỏ vào tệp có thật. Lý do ở
   `mcp_dong_goi.py`.
10. Gói theo repo gốc: mục `upstream` trong danh mục khớp `theo-goc/<id>.json`, và gói lẻ tách ra từ
    một gói gộp (`thuoc_goi`) trỏ đúng gói gộp đó. Lý do ở `theo-goc.py`.
11. Mã gói bằng tiếng Anh (Naota dùng ở nhiều nước). Mã là đường dẫn và tên trong
    mọi máy, đổi về sau phải đi qua `replaces` (Naota 1.1.0), nên chặn ngay từ lúc thêm gói. Tên hiển
    thị vẫn có cả tiếng Việt lẫn tiếng Anh như cũ.
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
loi = []
canh = []


def sai(ten, chi_tiet=""):
    loi.append(ten + (("  [" + str(chi_tiet) + "]") if chi_tiet else ""))


def check(ten, dieu_kien, chi_tiet=""):
    if not dieu_kien:
        sai(ten, chi_tiet)
    return bool(dieu_kien)


# Luật tên tool (TIEN, PHA, THA, _khop) nằm ở `luat_ten_tool.py`, dùng chung với `soi-ban-moi.py`.
from luat_ten_tool import PHA, TIEN, _khop  # noqa: E402
from ban_chinh_thuc import loi_ban  # noqa: E402
import chinh_chu  # noqa: E402
import mcp_dong_goi  # noqa: E402


def doc_manifest(thu_muc: Path):
    """Đọc `naota-pack.yaml` mà không cần PyYAML.

    Manifest trong kho có hai kiểu viết: kiểu MỘT DÒNG do `tu-catalog.py` sinh ra
    (`name: {vi: "..."}`), và kiểu KHỐI người ta viết tay (`name:` rồi thụt vào `vi: ...`).
    Hàm này nhận cả hai, và chỉ hai - gặp cấu trúc lạ hơn thì nó báo thiếu trường chứ không âm
    thầm hiểu sai. Tự đọc để CI không phải cài thư viện, và cái giá của lựa chọn đó nằm gọn
    trong đúng hàm này.
    """
    tep = thu_muc / "naota-pack.yaml"
    if not tep.exists():
        return None
    d, khoa, khoi = {}, None, []

    def dong_khoi():
        """Gộp các dòng thụt vào của một khoá thành list hoặc map.

        Ba hình dạng gặp thật trong kho: list phẳng (`- a`), map phẳng (`vi: ...`), và map của
        list (`plugins:` rồi `- plugins/pricing`). Không đi sâu hơn hai tầng - gói nào cần thế
        thì đã vượt khỏi đặc tả spec 1.
        """
        if khoa is None or not khoi:
            return
        if all(x.lstrip().startswith("- ") or not x.strip() for x in khoi):
            d[khoa] = [x.lstrip()[2:].strip().strip('"').strip("'") for x in khoi if x.strip()]
            return
        con, con_hien = {}, None
        for x in khoi:
            if x.lstrip().startswith("- "):
                if con_hien is not None:
                    con.setdefault(con_hien, [])
                    if isinstance(con[con_hien], list):
                        con[con_hien].append(x.lstrip()[2:].strip().strip('"').strip("'"))
                continue
            m = re.match(r"\s+([a-zA-Z_]+):\s*(.*)$", x)
            if not m:
                continue
            con_hien, gt = m.group(1), m.group(2).strip()
            if gt.startswith("[") and gt.endswith("]"):
                con[con_hien] = [y.strip().strip('"').strip("'")
                                 for y in gt[1:-1].split(",") if y.strip()]
            elif gt:
                con[con_hien] = gt.strip('"').strip("'")
            else:
                con[con_hien] = []
        if con:
            d[khoa] = con

    for dong in tep.read_text(encoding="utf-8").splitlines():
        if not dong.strip() or dong.lstrip().startswith("#"):
            continue
        if dong[0] in " 	":
            khoi.append(dong)
            continue
        dong_khoi()
        khoi = []
        m = re.match(r"([a-zA-Z_]+):\s*(.*)$", dong)
        if not m:
            khoa = None
            continue
        khoa, gt = m.group(1), m.group(2).strip()
        if gt.startswith("{") and gt.endswith("}"):
            d[khoa] = {k.strip(): v.strip().strip('"').strip("'")
                       for k, v in (x.split(":", 1) for x in gt[1:-1].split(",") if ":" in x)}
        elif gt:
            d[khoa] = gt.strip('"').strip("'")
    dong_khoi()
    return d


# ============================================================
# 1-4. Từng gói
# ============================================================
thu_muc_goi = sorted(p for p in (GOC / "packs").iterdir() if p.is_dir())
if not thu_muc_goi:
    sai("thư mục packs/ rỗng")

# 11. Mã gói tiếng Anh. Không đoán được ngôn ngữ của một chuỗi không dấu, nên soi theo những âm tiết
# chỉ tiếng Việt mới có (đã gặp thật trong kho trước 02/11). Tên thương hiệu là danh từ riêng, giữ nguyên.
AM_TIET_VIET = {"tro", "khach", "noi", "dung", "quang", "lieu", "pham", "tinh", "nghien", "cuu", "kinh",
                "doanh", "trinh", "luong", "linh", "viet", "trong", "pheu", "ngay", "cham", "hoi", "thoai",
                "nguoi", "tien", "hieu", "nhan", "tuong", "chien", "dich", "giao", "nhom"}
MA_THUONG_HIEU = {"naota.nhanh", "naota.kiotviet", "naota.haravan", "naota.sapo", "naota.lemo-opuscar"}

connector_theo_goi = {}
for tm in thu_muc_goi:
    ten = tm.name
    if ten not in MA_THUONG_HIEU:
        viet = sorted(set(re.split(r"[.-]", ten)) & AM_TIET_VIET)
        check(f"{ten}: mã gói bằng tiếng Anh (đổi mã cũ thì khai `replaces` trong manifest)", not viet, viet)
    man = doc_manifest(tm)
    if not check(f"{ten}: có naota-pack.yaml đọc được", man is not None):
        continue
    check(f"{ten}: id khớp tên thư mục", man.get("id") == ten, man.get("id"))
    check(f"{ten}: có version", bool(man.get("version")))
    check(f"{ten}: có name", bool(man.get("name")))
    check(f"{ten}: format đúng", man.get("format") == "naota-pack", man.get("format"))
    check(f"{ten}: spec = 1", str(man.get("spec")) == "1", man.get("spec"))

    duong_con = (man.get("provides") or {}).get("connectors") or []
    connector_theo_goi[ten] = []
    for rel in duong_con:
        tep = tm / rel
        if not check(f"{ten}: tệp khai trong provides có thật ({rel})", tep.exists()):
            continue
        try:
            con = json.loads(tep.read_text(encoding="utf-8"))
        except Exception as e:
            sai(f"{ten}: {rel} không phải JSON hợp lệ", e)
            continue
        connector_theo_goi[ten].append(con)
        cid = con.get("id") or ""
        check(f"{ten}: connector có id", bool(cid))
        for truong in ("name", "category", "description", "transport"):
            check(f"{ten}/{cid}: có {truong}", bool(con.get(truong)))

        # Icon: đường dẫn tuyệt đối của dashboard KHÔNG dùng được trong gói, và .svg thì
        # endpoint phục vụ ảnh của gói cố ý từ chối (mở thẳng một tab là chạy script bên trong).
        icon = str(con.get("icon") or "")
        check(f"{ten}/{cid}: icon không phải đường dẫn tuyệt đối", not icon.startswith("/"), icon)
        check(f"{ten}/{cid}: icon không phải .svg", not icon.lower().endswith(".svg"), icon)
        if icon.startswith("assets/"):
            check(f"{ten}/{cid}: tệp icon có thật", (tm / icon).exists(), icon)

        # Bí mật không được nằm trong url: Naota lưu `url` KHÔNG qua secrets_store và trả
        # nguyên nó ra giao diện, nên token trong url là rơi thẳng ra dashboard và ra log.
        u = str(con.get("url") or "").lower()
        for tham in ("jwt=", "token=", "api_key=", "apikey=", "secret=", "password=", "access_token="):
            check(f"{ten}/{cid}: không nhét credential vào url", tham not in u, tham)

        # An toàn: mặc định KHÔNG được là toàn quyền. `readonly` và `safe` đều hợp lệ - vài
        # dịch vụ chỉ có nghĩa khi ghi được bản nháp (Sheets, Tasks, Docs), và bắt chúng về
        # chỉ-đọc là đẩy người dùng đi nâng quyền tay ngay lần dùng đầu, tức làm mòn chính
        # thao tác nâng quyền. Naota vẫn ép gói về chỉ đọc ở phía nó; dòng này canh chuyện gói
        # KHAI toàn quyền, vì đó là lời nói dối với người đọc gói.
        dp = con.get("default_perm", "readonly")
        check(f"{ten}/{cid}: default_perm không phải full", dp in ("readonly", "safe"), dp)

        meta = con.get("tool_meta") or {}
        da_can_nhac = {str(x) for x in (con.get("ghi_da_can_nhac") or [])}
        for nhom in ("read", "write"):
            for tool in (meta.get(nhom) or []):
                check(f"{ten}/{cid}: tool '{tool}' đụng tới TIỀN mà khai ở nhóm {nhom} - "
                      f"phải là danger", not _khop(tool, TIEN))
                check(f"{ten}/{cid}: tool '{tool}' nghe như phá huỷ mà khai ở nhóm {nhom} - "
                      f"chuyển sang danger, hoặc thêm tên nó vào `ghi_da_can_nhac` của khuôn "
                      f"nếu bạn đã cân nhắc và thấy nó nhẹ",
                      not _khop(tool, PHA) or tool in da_can_nhac)
        check(f"{ten}/{cid}: `ghi_da_can_nhac` không được liệt kê tool đụng tiền",
              not [x for x in da_can_nhac if _khop(x, TIEN)],
              [x for x in da_can_nhac if _khop(x, TIEN)])
        if meta.get("danger"):
            check(f"{ten}/{cid}: khai tool nguy hiểm thì phải có câu cảnh báo `risk`",
                  bool(str(con.get("risk") or "").strip()))

        # 7. Bản chính thức: xem `ban_chinh_thuc.py`.
        for l in loi_ban(con):
            sai(f"{ten}/{cid}: {l}")
        # `lenh_cu`: lệnh mặc định đã từng phát hành. Kết nối tạo từ bản cũ còn lưu đúng lệnh đó thì
        # Naota (từ 1.0.0) chạy lệnh hiện hành; lệnh hiện hành mà nằm trong danh sách là vô nghĩa.
        for cu in (con.get("lenh_cu") or []):
            check(f"{ten}/{cid}: mỗi mục `lenh_cu` có command và args",
                  isinstance(cu, dict) and cu.get("command") and isinstance(cu.get("args"), list), cu)
            check(f"{ten}/{cid}: `lenh_cu` không chứa chính lệnh hiện hành",
                  not (isinstance(cu, dict) and cu.get("command") == con.get("command")
                       and cu.get("args") == con.get("args")))

# ============================================================
# 5. Danh mục khớp gói và khớp zip
# ============================================================
idx = json.loads((GOC / "index.json").read_text(encoding="utf-8"))
check("index.json đúng format", idx.get("format") == "naota-pack-index", idx.get("format"))
check("index.json đúng format_version", int(idx.get("format_version") or 0) == 1)

ids = [g.get("id") for g in idx.get("packs") or []]
check("id trong danh mục không trùng nhau", len(ids) == len(set(ids)))

for g in idx.get("packs") or []:
    gid = g.get("id") or "?"
    tm = GOC / "packs" / gid
    if not check(f"danh mục: {gid} có thư mục gói", tm.is_dir()):
        continue
    tai = g.get("download") or {}
    zp = GOC / str(tai.get("url") or "")
    if not check(f"danh mục: {gid} có tệp zip ({tai.get('url')})", zp.is_file()):
        continue
    b = zp.read_bytes()
    check(f"danh mục: {gid} sha256 khớp tệp zip",
          hashlib.sha256(b).hexdigest() == tai.get("sha256"), hashlib.sha256(b).hexdigest())
    check(f"danh mục: {gid} size khớp tệp zip", len(b) == int(tai.get("size") or 0), len(b))

    # So NỘI DUNG, không so byte. Mức nén DEFLATE khác nhau giữa các bản zlib nên đóng lại
    # trên máy khác ra byte khác dù nội dung y hệt - so byte là đỏ giả trên CI.
    with zipfile.ZipFile(zp) as z:
        trong_zip = {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}
    tren_dia = {}
    for f in sorted(tm.rglob("*")):
        if f.is_file():
            tren_dia[f.relative_to(tm).as_posix()] = f.read_bytes()
    check(f"danh mục: {gid} zip có đúng bộ tệp như thư mục nguồn",
          set(trong_zip) == set(tren_dia),
          "chỉ trong zip: " + str(sorted(set(trong_zip) - set(tren_dia)))
          + " | chỉ trên đĩa: " + str(sorted(set(tren_dia) - set(trong_zip))))
    khac = [k for k in (set(trong_zip) & set(tren_dia)) if trong_zip[k] != tren_dia[k]]
    check(f"danh mục: {gid} nội dung từng tệp khớp thư mục nguồn", not khac, khac)

    # Logo trên thẻ trong Kho cài đặt. Naota đọc `icon` của mục danh mục và ghép với địa chỉ
    # của chính file index (như `download.url`), nên nó phải là đường dẫn TƯƠNG ĐỐI trỏ vào
    # một tệp ảnh có thật trong repo - và là ảnh nằm TRONG gói, để logo trong kho và logo trên
    # trang Kết nối sau khi cài là cùng một tệp, không bao giờ lệch nhau. Không nhận .svg vì
    # cùng lý do với icon trong khuôn connector ở mục 2.
    icon = str(g.get("icon") or "")
    if g.get("kind") == "connector":
        check(f"danh mục: {gid} là kết nối thì phải có `icon` (logo trên thẻ)", bool(icon))
    if icon:
        check(f"danh mục: {gid} icon là đường dẫn tương đối", not icon.startswith(("/", "http:", "https:")), icon)
        check(f"danh mục: {gid} icon nằm trong thư mục gói", icon.startswith(f"packs/{gid}/assets/"), icon)
        check(f"danh mục: {gid} icon là ảnh png/webp/jpg/gif, không svg",
              icon.lower().endswith((".png", ".webp", ".jpg", ".jpeg", ".gif")), icon)
        check(f"danh mục: {gid} tệp icon có thật", (GOC / icon).is_file(), icon)

    # Gói có mặt trên đĩa mà quên thêm vào danh mục thì không ai thấy nó - lỗi im lặng nhất
    # của cả repo này.
for tm in thu_muc_goi:
    check(f"gói {tm.name} có mặt trong index.json", tm.name in ids)

# ============================================================
# 8. Nối với MCP chính chủ chạy từ xa (`chinh-chu/*.json`, xem `chinh_chu.py`). Ở đây chỉ kiểm
#    cấu trúc; so với bản phát hành mới nhất là việc của `soi-ban-moi.py` (cần mạng).
# ============================================================
for tep in chinh_chu.cac_tep():
    try:
        d_cc = chinh_chu.doc(tep)
    except ValueError as e:
        sai(f"chinh-chu/{tep.name}: không phải JSON hợp lệ", e)
        continue
    for l in chinh_chu.loi_cau_truc(d_cc, GOC):
        sai(f"chinh-chu/{tep.name}: {l}")

# ============================================================
# 9. MCP kho tự build (`mcp/`, xem `mcp_dong_goi.py`): mọi tệp khớp sha256 ghi trong
#    `mcp/nguon.json`, và connector trỏ vào `mcp/` thì trỏ đúng một tệp có trong đó. Tệp này
#    là MÃ chạy trên máy người dùng, nên nó phải đúng thứ người review đã đối chiếu với commit gốc.
# ============================================================
for l in mcp_dong_goi.doi_chieu():
    sai(l)
_tep_mcp = {mcp_dong_goi.ten_tep(m) for m in mcp_dong_goi.doc_nguon()}
for f in sorted((GOC / "packs").glob("*/connectors/*.json")):
    try:
        con_mcp = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        continue
    for lenh_mcp in [con_mcp] + list(con_mcp.get("lenh_cu") or []):
        tep_mcp = mcp_dong_goi.tep_tu_args(lenh_mcp.get("args"))
        if tep_mcp:
            check(f"{f.relative_to(GOC).as_posix()}: trỏ vào mcp/{tep_mcp} nhưng tệp đó không có "
                  f"trong mcp/nguon.json", tep_mcp in _tep_mcp)

# ============================================================
# 10. Gói theo repo gốc (`theo-goc/*.json`, xem `theo-goc.py`). Ở đây chỉ kiểm hai bên khớp
#     nhau; so với repo gốc là việc của job `theo-goc` (cần mạng). Naota hiện mục `upstream`
#     thành nhãn "Theo repo gốc" kèm link, nên một mục khai sai repo là một link dẫn sai chỗ.
# ============================================================
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
co_cau_hinh = {p.stem: p for p in sorted((GOC / "theo-goc").glob("*.json"))}
for g in idx.get("packs") or []:
    up = g.get("upstream")
    if up is None:
        continue
    gid = g.get("id") or "?"
    if not check(f"theo gốc: {gid} có tệp theo-goc/{gid}.json", gid in co_cau_hinh):
        continue
    ch = json.loads(co_cau_hinh[gid].read_text(encoding="utf-8"))
    check(f"theo gốc: {gid} repo đúng dạng chủ/tên", bool(_REPO.match(str(up.get("repo") or ""))), up.get("repo"))
    check(f"theo gốc: {gid} repo khớp cấu hình", up.get("repo") == ch.get("repo") and up.get("ref") == ch.get("ref"),
          f"{up.get('repo')}@{up.get('ref')} khác {ch.get('repo')}@{ch.get('ref')}")
    check(f"theo gốc: {gid} có commit gốc đủ 40 ký tự", bool(re.match(r"^[0-9a-f]{40}$", str(up.get("commit") or ""))))
    check(f"theo gốc: {gid} có ngày đồng bộ", bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(up.get("synced") or ""))))
for gid in co_cau_hinh:
    check(f"theo gốc: theo-goc/{gid}.json có mục trong index.json kèm `upstream`",
          any(g.get("id") == gid and g.get("upstream") for g in idx.get("packs") or []))
# Gói lẻ (`tach`): mỗi agent của gói gộp là một mục riêng. Nó không mang `upstream` (chỉ gói gộp nằm ở
# mục Đề xuất của Store), nên chỗ duy nhất nối nó về repo gốc là `thuoc_goi`. Trỏ sai là gói lẻ đứng yên mãi.
for g in idx.get("packs") or []:
    cha = g.get("thuoc_goi")
    if cha is None:
        continue
    gid = g.get("id") or "?"
    if not check(f"gói lẻ: {gid} trỏ vào gói gộp có tệp theo-goc/{cha}.json", cha in co_cau_hinh, cha):
        continue
    tach = json.loads(co_cau_hinh[cha].read_text(encoding="utf-8")).get("tach") or ""
    check(f"gói lẻ: {gid} có id bắt đầu bằng `tach` của gói gộp", bool(tach) and gid.startswith(tach), tach)
    check(f"gói lẻ: {gid} không mang `upstream`", "upstream" not in g)
    check(f"gói lẻ: {gid} là agent", g.get("kind") == "agent", g.get("kind"))

# ============================================================
# 6. Em dash
#
# Luật của chủ kho, và lý do là kỹ thuật: trình đọc màn hình lẫn bộ đọc thành tiếng vấp ở ký
# tự này. Nhưng chỉ soi tệp DO KHO viết - manifest, khuôn connector, danh mục, tài liệu, công
# cụ. Thân các kỹ năng do người khác viết mang vào thì không: sửa chữ trong tác phẩm của họ
# không phải việc của trình kiểm này, và một luật gõ cửa 250 tệp vendor là một luật bị tắt.
# ============================================================
EM = chr(0x2014)
SOI = ["index.json", "README.md", "CONTRIBUTING.md", "mcp/nguon.json"]
for f in (sorted(GOC.rglob("naota-pack.yaml")) + sorted((GOC / "packs").rglob("connectors/*.json"))
          + sorted((GOC / "tools").glob("*.py")) + chinh_chu.cac_tep() + sorted((GOC / "theo-goc").glob("*.json"))
          + sorted((GOC / "theo-goc" / "dich").glob("*.json")) + [GOC / x for x in SOI]):
    if not f.is_file():
        continue
    try:
        s_tep = f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if EM in s_tep:
        sai(f"{f.relative_to(GOC).as_posix()}: chứa ký tự em dash (dùng gạch ngang thường)")

print()
for c in canh:
    print("canh bao: " + c)
if loi:
    print(f"ĐỎ {len(loi)} lỗi:")
    for l in loi:
        print("  - " + l)
    sys.exit(1)
print(f"XANH - {len(thu_muc_goi)} gói, {len(ids)} mục danh mục, tất cả khớp")
