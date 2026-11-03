"""Nối gói GitHub với MCP chính chủ (`chinh-chu/github.json`, `tools/chinh_chu.py`).

    VANHANH_OS_DIR=../vanhanh python tests/vanhanh.github/test_chinh_chu_github.py   (KHÔNG mạng)

Canh bốn thứ:
  1. Bộ tool ĐÃ SOÁT trong kho luôn được `tool_meta` của khuôn phân loại sạch: sửa khuôn mà làm
     một tool đã soát lọt nhóm thì đỏ ngay ở Pull Request, không đợi lần soi hằng ngày.
  2. Nhãn của bên chính chủ thắng luật tên: `hide_issue_comment` (tên không có từ ghi nào) mà GitHub
     ghi là không chỉ đọc thì đỏ khi Vanhanh xếp nó vào nhóm đọc. Đây là vụ thật lúc viết.
  3. Gộp các biến thể snapshot của cùng một tool theo nhãn NẶNG NHẤT, không để bản không gắn nhãn
     (`list_branches_output.snap`) đè lên bản có nhãn.
  4. Bản mới thêm, bớt tool hay đổi nhãn thì phát hiện đúng từng cái.
"""
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STORE = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("VANHANH_OS_DIR") or (STORE.parent / "vanhanh")).resolve()
if not (ROOT / "server" / "mcp_catalog.py").is_file():
    raise SystemExit(f"VANHANH checkout not found at {ROOT} (set VANHANH_OS_DIR)")
os.environ["VANHANH_OS_DIR"] = str(ROOT)
os.environ.setdefault("VANHANH_STATE_DIR", tempfile.mkdtemp(prefix="vanhanh-test-chinh-chu-"))
sys.path.insert(0, str(STORE / "tools"))

import chinh_chu  # noqa: E402

spec = importlib.util.spec_from_file_location("soi_ban_moi", STORE / "tools" / "soi-ban-moi.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
classify = S._nap_classify()

fails = []


def check(name, cond, them=""):
    print(("ok   " if cond else "FAIL ") + name + (("  [" + str(them) + "]") if them and not cond else ""))
    if not cond:
        fails.append(name)


TEP = STORE / "chinh-chu" / "github.json"
d = chinh_chu.doc(TEP)
con = json.loads((STORE / d["connector"]).read_text(encoding="utf-8"))

# 1. Bộ đã soát được khuôn phân loại sạch.
check("chinh-chu/github.json đúng cấu trúc", chinh_chu.loi_cau_truc(d) == [], chinh_chu.loi_cau_truc(d))
ten = sorted(set(d["tools"]) | set(d.get("tool_chi_o_ban_tu_xa") or []))
do, doan = S.soi_ten(classify, con, "github", ten, d["tools"])
check("mọi tool đã soát qua luật phân loại", do == [], do)
check("không tool đã soát nào còn phải đoán là đọc", doan == [], doan)
for t, nhan in d["tools"].items():
    if nhan in ("write", "destructive"):
        check(f"{t}: GitHub ghi là {nhan} thì Vanhanh không xếp vào nhóm đọc", classify(con, t, {}) != "read")

# 2. Nhãn chính chủ thắng luật tên.
trong = {"id": "x", "tool_meta": {}}
do, _ = S.soi_ten(classify, trong, "x", ["hide_issue_comment"], {"hide_issue_comment": "write"})
check("tool ghi tên lạ mà Vanhanh xếp đọc thì đỏ", len(do) == 1 and "KHÔNG chỉ đọc" in do[0], do)
do, _ = S.soi_ten(classify, trong, "x", ["hide_issue_comment"], {})
check("không có nhãn thì chỉ còn luật tên (không đỏ oan)", do == [], do)
co_meta = {"id": "x", "tool_meta": {"write": ["label_write"]}}
do, _ = S.soi_ten(classify, co_meta, "x", ["label_write"], {"label_write": "destructive"})
check("tool phá huỷ mà Vanhanh xếp ghi thì đỏ", len(do) == 1 and "PHÁ HUỶ" in do[0], do)
co_meta["ghi_da_can_nhac"] = ["label_write"]
do, _ = S.soi_ten(classify, co_meta, "x", ["label_write"], {"label_write": "destructive"})
check("`ghi_da_can_nhac` gỡ được chặn phá huỷ", do == [], do)
do, _ = S.soi_ten(classify, co_meta, "x", ["remove_reaction"], {})
check("luật tên cũ vẫn chạy khi không có nhãn", len(do) == 1, do)

check("nhãn: readOnlyHint true là đọc", chinh_chu.nhan_tu_chu_thich({"readOnlyHint": True}) == "read")
check("nhãn: destructiveHint vắng là ghi, không theo mặc định của spec",
      chinh_chu.nhan_tu_chu_thich({"readOnlyHint": False}) == "write")
check("nhãn: destructiveHint true là phá huỷ",
      chinh_chu.nhan_tu_chu_thich({"readOnlyHint": False, "destructiveHint": True}) == "destructive")
check("nhãn: không gắn gì là ?", chinh_chu.nhan_tu_chu_thich(None) == "?")


# 3. Đọc tarball và gộp biến thể (thay urlopen bằng tarball dựng trong bộ nhớ).
def _tarball(tep):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for ten_tep, j in tep.items():
            b = json.dumps(j).encode()
            ti = tarfile.TarInfo(f"github-github-mcp-server-abc1234/{ten_tep}")
            ti.size = len(b)
            tar.addfile(ti, io.BytesIO(b))
    return buf.getvalue()


class _Tra:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


SNAP = "pkg/github/__toolsnaps__/"
goc_urlopen = chinh_chu.urllib.request.urlopen
chinh_chu.urllib.request.urlopen = lambda req, timeout=None: _Tra(_tarball({
    SNAP + "list_branches.snap": {"name": "list_branches", "annotations": {"readOnlyHint": True}},
    SNAP + "list_branches_output.snap": {"name": "list_branches"},
    SNAP + "x_ff_flag.snap": {"name": "x", "annotations": {"readOnlyHint": False, "destructiveHint": True}},
    SNAP + "x.snap": {"name": "x", "annotations": {"readOnlyHint": False},
                      "inputSchema": {"properties": {"method": {"enum": ["create", "delete"]}}}},
    SNAP + "x_output.snap": {"name": "x",
                             "inputSchema": {"properties": {"method": {"enum": ["create", "archive"]}}}},
    "README.md": {"name": "khong_phai_tool"},
}))
try:
    bo, lenh = chinh_chu.bo_tool("github/github-mcp-server", "v9.9.9", "pkg/github/__toolsnaps__",
                                 {"x": "method"})
finally:
    chinh_chu.urllib.request.urlopen = goc_urlopen
check("bản không gắn nhãn không đè bản có nhãn", bo.get("list_branches") == "read", bo)
check("gộp biến thể lấy nhãn nặng nhất", bo.get("x") == "destructive", bo)
check("chỉ đọc tệp trong thư mục snapshot", "khong_phai_tool" not in bo, bo)
check("đọc danh sách lệnh, gộp mọi biến thể", lenh == {"x": ["archive", "create", "delete"]}, lenh)
check("tool không theo dõi lệnh thì không ghi lệnh", "list_branches" not in lenh, lenh)

# Lệnh của tool gộp.
check("khuôn GitHub theo dõi lệnh của đúng ba tool gộp",
      chinh_chu.lenh_can_theo_doi(con) == {"label_write": "method", "projects_write": "method",
                                           "discussion_comment_write": "method"},
      chinh_chu.lenh_can_theo_doi(con))
check("bộ đã soát có lệnh của ba tool gộp", set(d.get("lenh") or {}) == set(chinh_chu.lenh_can_theo_doi(con)),
      d.get("lenh"))
for t, ds in (d.get("lenh") or {}).items():
    luat = con["call_rules"][t]
    khai = {x for k in ("read_values", "write_values", "danger_values") for x in luat.get(k) or []}
    check(f"{t}: mọi lệnh đã soát đều được khai trong call_rules", set(ds) <= khai, set(ds) - khai)
    check(f"{t}: lệnh có chữ delete là danger",
          all(classify(con, t, {"method": v}) == "danger" for v in ds if "delete" in v))
check("lệnh thêm và bớt được nêu đúng",
      chinh_chu.khac_biet_lenh({"x": ["create", "delete"]}, {"x": ["create", "archive"]})
      == ["x thêm lệnh archive", "x bớt lệnh delete"])
check("lệnh không đổi thì không có khác biệt", chinh_chu.khac_biet_lenh(d.get("lenh") or {}, d.get("lenh") or {}) == [])

# 4. Khác biệt giữa bản đã soát và bản mới.
them, bot, doi = chinh_chu.khac_biet({"a": "read", "b": "write", "c": "read"},
                                     {"a": "read", "b": "destructive", "d": "write"})
check("phát hiện tool thêm", them == ["d"], them)
check("phát hiện tool bớt", bot == ["c"], bot)
check("phát hiện tool đổi nhãn", doi == ["b"], doi)
check("bản vá không đổi tool thì không có khác biệt",
      chinh_chu.khac_biet(d["tools"], dict(d["tools"])) == ([], [], []))

sai = dict(d, repo="https://github.com/github/github-mcp-server")
check("repo phải ở dạng chủ/tên", any("repo" in l for l in chinh_chu.loi_cau_truc(sai)))
sai = dict(d, connector="packs/vanhanh.github/connectors/khong-co.json")
check("connector phải trỏ tới tệp có thật", any("không có" in l for l in chinh_chu.loi_cau_truc(sai)))

print()
if fails:
    print(f"ĐỎ {len(fails)} lỗi")
    sys.exit(1)
print("XANH")
