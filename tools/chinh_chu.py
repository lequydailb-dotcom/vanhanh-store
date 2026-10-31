"""Nối gói với MCP CHÍNH CHỦ chạy từ xa, để kho biết khi bên đó ra bản mới.

Dùng bởi `soi-ban-moi.py` (cần mạng) và `kiem-tra.py` (chỉ kiểm cấu trúc, không chạm mạng).

Vì sao cần
----------
`soi-ban-moi.py` soi được MCP chạy qua `npx`/`uvx` bằng cách chạy thử nó. MCP chính chủ chạy từ
xa (`transport: http`, ví dụ `https://api.githubcopilot.com/mcp/x/all`) thì không: muốn liệt kê
tool phải đăng nhập thật, mà CI không có tài khoản. Thế là trước tệp này, GitHub ra bản mới (2.0.0
ngày 2026-10-06, bốn ngày sau khi gói GitHub vào kho) mà kho không hề hay.

Nhưng vài bên công bố DANH SÁCH TOOL ngay trong mã nguồn của từng bản phát hành. GitHub để mỗi
tool một tệp `pkg/github/__toolsnaps__/<tên>.snap`, gồm tên, mô tả, schema và các nhãn
`readOnlyHint` / `destructiveHint` do chính GitHub gắn. Đọc ở THẺ PHÁT HÀNH mới nhất là biết bản
đang chạy trên máy chủ của họ có những tool gì, không cần đăng nhập.

Mỗi tệp `chinh-chu/<id>.json` nối một khuôn connector với nguồn đó và ghi lại bộ tool ĐÃ SOÁT.
Mỗi ngày CI so bản mới nhất với bộ đã soát:

- Thêm, bớt tool hay đổi nhãn: ĐỎ, kèm đúng danh sách khác biệt và đường tới ghi chú phát hành.
  Đọc xong, sửa `tool_meta` nếu cần (ra bản gói mới), rồi ghi lại bộ đã soát bằng
  `python tools/soi-ban-moi.py --chi-chinh-chu --ghi-da-soat`. Ghi lại không cần ra bản gói:
  tệp này nằm ngoài `packs/`, không vào `.zip`.
- Bản mới chỉ là bản vá, bộ tool y nguyên: xanh, chỉ in một dòng cho biết.

Nhãn của bên chính chủ được tin theo đúng chữ họ GHI TƯỜNG MINH. Spec MCP coi `destructiveHint`
vắng mặt là "có thể phá huỷ", nhưng GitHub để trống nó ở nhiều tool ghi bình thường, nên đọc theo
mặc định của spec sẽ báo oan hàng loạt. Nhãn vắng thì chỉ còn luật tên (`luat_ten_tool.py`) canh.
"""
import io
import json
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC = GOC / "chinh-chu"
_UA = {"User-Agent": "naota-store-soi"}
TRAN_GIAY = 60

# Thứ tự nặng dần, để gộp các biến thể của cùng một tool (GitHub có tệp snapshot riêng cho bản
# trả kết quả có kiểu, bản sau cờ tính năng...). "?" là bên chính chủ không gắn nhãn.
NHAN = ("?", "read", "write", "destructive")


def cac_tep():
    return sorted(THU_MUC.glob("*.json")) if THU_MUC.is_dir() else []


def doc(tep):
    return json.loads(Path(tep).read_text(encoding="utf-8"))


def ghi(tep, d):
    Path(tep).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                         newline="\n")


def nhan_tu_chu_thich(ann):
    """Nhãn của một tool theo annotations bên chính chủ GHI TƯỜNG MINH (xem docstring module)."""
    if not isinstance(ann, dict) or "readOnlyHint" not in ann:
        return "?"
    if ann.get("readOnlyHint"):
        return "read"
    return "destructive" if ann.get("destructiveHint") is True else "write"


def ban_moi_nhat(repo):
    """Thẻ của bản phát hành mới nhất. Đi theo chuyển hướng của trang `releases/latest` thay vì gọi
    API: API giới hạn 60 lượt một giờ cho mỗi IP, mà máy CI dùng chung IP với cả nghìn repo khác."""
    req = urllib.request.Request(f"https://github.com/{repo}/releases/latest", headers=_UA)
    with urllib.request.urlopen(req, timeout=TRAN_GIAY) as r:
        url = r.geturl()
    if "/releases/tag/" not in url:
        raise RuntimeError(f"{repo} chưa có bản phát hành nào ({url})")
    return urllib.parse.unquote(url.rsplit("/releases/tag/", 1)[1])


def lenh_can_theo_doi(con):
    """{tên tool: tham số chọn lệnh} cho các tool khuôn phân loại theo TỪNG LỆNH (`call_rules` không
    có `items`, ví dụ GitHub `label_write` chọn lệnh bằng `method`). Bên chính chủ thêm một lệnh
    vào những tool này thì Naota xếp lệnh đó về mức `else` của luật: an toàn, nhưng kho phải biết."""
    return {t: str(r.get("key")) for t, r in ((con or {}).get("call_rules") or {}).items()
            if isinstance(r, dict) and r.get("key") and not r.get("items")}


def bo_tool(repo, the, snapshots, lenh_can=None):
    """({tên tool: nhãn}, {tên tool: [lệnh]}) đọc từ snapshot trong mã nguồn của đúng thẻ phát
    hành `the`. Phần lệnh chỉ có cho các tool trong `lenh_can` ({tool: tham số}), lấy từ `enum`
    của tham số đó trong schema."""
    lenh_can = lenh_can or {}
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/tags/{urllib.parse.quote(the)}"
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=TRAN_GIAY * 3) as r:
        du_lieu = r.read()
    goc = snapshots.strip("/") + "/"
    kq, lenh = {}, {}
    with tarfile.open(fileobj=io.BytesIO(du_lieu), mode="r:gz") as tar:
        for m in tar:
            # Tệp trong tarball của GitHub nằm dưới một thư mục `<repo>-<sha>/`.
            duong = m.name.split("/", 1)[1] if "/" in m.name else m.name
            if not (m.isfile() and duong.startswith(goc) and duong.endswith(".snap")):
                continue
            j = json.load(tar.extractfile(m))
            ten = str(j.get("name") or "").strip()
            if not ten:
                continue
            n = nhan_tu_chu_thich(j.get("annotations"))
            if NHAN.index(n) > NHAN.index(kq.get(ten, "?")):
                kq[ten] = n
            else:
                kq.setdefault(ten, n)
            if ten in lenh_can:
                tham = (((j.get("inputSchema") or {}).get("properties") or {})
                        .get(lenh_can[ten]) or {})
                lenh[ten] = sorted(set(lenh.get(ten, [])) | {str(v) for v in tham.get("enum") or []})
    if not kq:
        raise RuntimeError(f"không thấy snapshot tool nào ở {repo}@{the}/{goc}")
    return kq, lenh


def khac_biet_lenh(cu, moi):
    """Danh sách mô tả lệnh thêm/bớt trong các tool theo dõi lệnh, rỗng nếu không đổi."""
    ra = []
    for t in sorted(set(cu) | set(moi)):
        them = sorted(set(moi.get(t, [])) - set(cu.get(t, [])))
        bot = sorted(set(cu.get(t, [])) - set(moi.get(t, [])))
        if them:
            ra.append(f"{t} thêm lệnh " + ", ".join(them))
        if bot:
            ra.append(f"{t} bớt lệnh " + ", ".join(bot))
    return ra


def khac_biet(cu, moi):
    """(thêm, bớt, đổi nhãn) giữa hai bộ {tên: nhãn}."""
    them = sorted(set(moi) - set(cu))
    bot = sorted(set(cu) - set(moi))
    doi = sorted(t for t in set(cu) & set(moi) if cu[t] != moi[t])
    return them, bot, doi


def loi_cau_truc(d, goc=GOC):
    """Lỗi cấu trúc của một tệp `chinh-chu/*.json`, không chạm mạng. Rỗng = đạt."""
    loi = []
    for truong in ("connector", "repo", "snapshots", "da_soat"):
        if not d.get(truong):
            loi.append(f"thiếu trường `{truong}`")
    if d.get("tools") is None:
        loi.append("thiếu trường `tools` (tệp mới thì để {} rồi chạy --ghi-da-soat)")
    rel = str(d.get("connector") or "")
    tep = goc / rel
    if rel and not tep.is_file():
        loi.append(f"`connector` trỏ tới tệp không có: {rel}")
    elif rel:
        try:
            con = json.loads(tep.read_text(encoding="utf-8"))
            if str(con.get("transport") or "") != "http":
                loi.append(f"{rel} không phải MCP chạy từ xa (transport: http): MCP npx/uvx thì "
                           f"`soi-ban-moi.py` đã chạy thử thật, không cần tệp này")
        except ValueError as e:
            loi.append(f"{rel} không phải JSON hợp lệ: {e}")
    repo = str(d.get("repo") or "")
    if repo and (repo.count("/") != 1 or repo.startswith(("http:", "https:"))):
        loi.append(f"`repo` phải ở dạng chủ/tên trên GitHub, không phải '{repo}'")
    tools = d.get("tools")
    if tools is not None and not (isinstance(tools, dict) and all(v in NHAN for v in tools.values())):
        loi.append(f"`tools` phải là {{tên: nhãn}} với nhãn thuộc {list(NHAN)}")
    lenh = d.get("lenh")
    if lenh is not None and not (isinstance(lenh, dict) and all(
            isinstance(v, list) and all(isinstance(x, str) for x in v) for v in lenh.values())):
        loi.append("`lenh` phải là {tên tool: [lệnh]}")
    them = d.get("tool_chi_o_ban_tu_xa")
    if them is not None and not (isinstance(them, list) and all(isinstance(x, str) for x in them)):
        loi.append("`tool_chi_o_ban_tu_xa` phải là danh sách tên tool")
    return loi
