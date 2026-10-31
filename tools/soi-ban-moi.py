"""Chạy thử BẢN MỚI NHẤT của từng MCP bên thứ 3 và soi tên tool thật nó trả về.

    NAOTA_OS_DIR=../naota python tools/soi-ban-moi.py

Cần mạng, `npx` và `uvx`. CI chạy mỗi ngày (xem `.github/workflows/kiem-tra.yml`).

Vì sao có script này
--------------------
Từ 2026-10-05 connector chạy MCP bên thứ 3 đi theo bản chính thức mới nhất (`@latest`, xem
`ban_chinh_thuc.py`). Cái giá: bên thứ 3 ra bản mới là mọi máy chạy bản đó ngay, kể cả khi bản
đó thêm tool mới mà khuôn chưa phân loại. Và `mcp_catalog.classify` của Naota xếp một tool
KHÔNG khai, tên không chứa từ gợi ý ghi nào, vào nhóm ĐỌC, tức chạy được ở mức Chỉ đọc. Vụ có
thật lúc viết script: `workspace-mcp` 2.x thêm `run_script_function` (chạy Apps Script) và Naota
xếp nó vào nhóm đọc.

`kiem-tra.py` chỉ soi được tên tool mà khuôn KHAI. Script này soi tên tool mà bản mới nhất THẬT
SỰ có, phân loại bằng đúng hàm `classify` của Naota, rồi áp cùng bộ luật tên (`luat_ten_tool.py`):

- ĐỎ: tool nghe như đụng tiền, hoặc phá huỷ / tác động ra ngoài, mà Naota không xếp vào nhóm
  nguy hiểm (trừ khi khuôn liệt kê nó trong `ghi_da_can_nhac`). Sửa bằng cách khai nó trong
  `tool_meta` của khuôn rồi ra bản gói mới.
- Cảnh báo: MCP không khởi động được khi thiếu tài khoản đăng nhập (vài server đòi credential
  ngay lúc mở), và tool chưa khai nằm ở nhóm đọc nhờ đoán theo tên, để người review liếc qua.

MCP CHÍNH CHỦ chạy từ xa (GitHub) không chạy thử được vì cần đăng nhập. Với chúng script đọc
danh sách tool bên đó công bố trong mã nguồn của bản phát hành mới nhất, áp cùng luật trên cộng
nhãn đọc/ghi/phá huỷ của chính bên đó, và đỏ khi bộ tool khác bộ kho đã soát. Chi tiết và cách
ghi lại bộ đã soát ở `chinh_chu.py`.

    python tools/soi-ban-moi.py --chi-chinh-chu                 # chỉ soi phần chính chủ, khỏi npx/uvx
    python tools/soi-ban-moi.py --chi-chinh-chu --ghi-da-soat   # soát xong thì ghi lại
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chinh_chu  # noqa: E402
import mcp_dong_goi  # noqa: E402
from ban_chinh_thuc import LENH  # noqa: E402
from luat_ten_tool import PHA, TIEN, _khop  # noqa: E402

GOC = Path(__file__).resolve().parent.parent
TRAN_GIAY = 180   # lần đầu npx/uvx phải tải gói, nên rộng tay


def _nap_classify():
    os_dir = Path(os.environ.get("NAOTA_OS_DIR") or GOC.parent / "naota").resolve()
    server = os_dir / "server"
    if not (server / "mcp_catalog.py").is_file():
        sys.exit(f"không thấy NAOTA ở {os_dir}: đặt NAOTA_OS_DIR trỏ tới bản checkout naota")
    os.environ.setdefault("NAOTA_STATE_DIR", tempfile.mkdtemp(prefix="naota-soi-"))
    sys.path.insert(0, str(server))
    import mcp_catalog
    return mcp_catalog.classify


# Service account GIẢ, đúng hình dạng nhưng khoá rỗng: đủ để vài server chịu khởi động và liệt
# kê tool, không bao giờ đăng nhập được vào đâu.
_SA_GIA = ('{"type": "service_account", "project_id": "naota-soi", "private_key_id": "x", '
           '"private_key": "-----BEGIN PRIVATE KEY-----\\nMIIB\\n-----END PRIVATE KEY-----\\n", '
           '"client_email": "soi@naota-soi.iam.gserviceaccount.com", "client_id": "1", '
           '"token_uri": "https://oauth2.googleapis.com/token"}')


def _env_gia(con, thu_muc):
    """Biến môi trường GIẢ cho mọi ô đăng nhập của khuôn. Vài server đòi credential ngay lúc mở
    (Search Console, Lark), dù chỉ để liệt kê tool. Giá trị giả nên không gọi được API nào."""
    env = dict(os.environ)
    for f in ((con.get("auth") or {}).get("fields") or []):
        ten = f.get("env")
        if not ten:
            continue
        if f.get("file"):
            tep = Path(thu_muc) / f"{ten}.json"
            tep.write_text(_SA_GIA, encoding="utf-8")
            env[ten] = str(tep)
        elif ten.upper().endswith("_URL"):
            # Vài server kiểm định dạng URL ngay lúc mở (Sapo: SAPO_STORE_URL).
            env[ten] = "https://naota-soi-gia.invalid"
        else:
            env[ten] = "naota-soi-gia"
    return env


def liet_ke_tool(con):
    """(danh sách tên tool, lỗi). Chạy lệnh của khuôn với credential giả, xem `_env_gia`."""
    cmd = shutil.which(con["command"]) or con["command"]
    # MCP kho tự build (`mcp/`): chạy tệp trong bản checkout này thay vì URL trên nhánh main, để
    # Pull Request thêm tệp mới soi được chính tệp đó trước khi trộn.
    args = [str(a).replace(mcp_dong_goi.URL_GOC, str(mcp_dong_goi.THU_MUC) + os.sep)
            for a in con.get("args") or []]
    p = subprocess.Popen([cmd] + args, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         env=_env_gia(con, tempfile.mkdtemp(prefix="naota-soi-env-")))
    loi = []
    threading.Thread(target=lambda: loi.append(p.stderr.read()), daemon=True).start()
    hen = threading.Timer(TRAN_GIAY, p.kill)
    hen.start()
    try:
        def gui(o):
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()

        def nhan(mid):
            while True:
                dong = p.stdout.readline()
                if not dong:
                    p.wait()
                    duoi = (loi[0] if loi else "").strip().splitlines()[-1:] or [""]
                    return None, f"thoát mã {p.returncode}: {duoi[0][:300]}"
                try:
                    m = json.loads(dong)
                except ValueError:
                    continue
                if m.get("id") == mid:
                    return m, ""

        gui({"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "naota-store-soi", "version": "1"}}})
        m, e = nhan(1)
        if not m:
            return None, e
        gui({"jsonrpc": "2.0", "method": "notifications/initialized"})
        ten, con_tro = [], None
        for lan in range(50):
            gui({"jsonrpc": "2.0", "id": 2 + lan, "method": "tools/list",
                 "params": {"cursor": con_tro} if con_tro else {}})
            m, e = nhan(2 + lan)
            if not m:
                return None, e
            kq = m.get("result") or {}
            ten += [t["name"] for t in kq.get("tools") or []]
            con_tro = kq.get("nextCursor")
            if not con_tro:
                break
        return sorted(set(ten)), ""
    except (BrokenPipeError, OSError) as e:
        return None, str(e)
    finally:
        hen.cancel()
        p.kill()


def soi_ten(classify, con, nhan_goi, ten, nhan=None):
    """(lỗi đỏ, tool chưa khai đang được đoán là đọc) cho bộ tên tool THẬT của một MCP.

    `nhan`: {tên: nhãn} do bên chính chủ gắn (xem `chinh_chu.py`), nếu có. Nhãn đó mạnh hơn mọi
    luật tên: vụ có thật lúc viết là `hide_issue_comment` của GitHub, tên không chứa từ ghi nào
    nên Naota xếp vào nhóm đọc, trong khi chính GitHub ghi rõ nó không chỉ đọc."""
    meta = con.get("tool_meta") or {}
    da_can_nhac = {str(x) for x in (con.get("ghi_da_can_nhac") or [])}
    khai = [str(p).lower() for k in ("read", "write", "danger") for p in (meta.get(k) or [])]
    do, chua_khai_doc = [], []
    for t in ten:
        # args={} chứ không phải None: phân loại như LÚC GỌI THẬT. Với args=None, tool cổng
        # (`call_rules`) và tool đa hành động (`arg_rules`) tạm coi là đọc để còn liệt kê
        # được; lúc gọi, args thiếu tên lệnh con thì chúng rơi về mức fail-closed.
        nhom = classify(con, t, {})
        if nhom == "danger":
            continue
        cua_ho = (nhan or {}).get(t, "?")
        if _khop(t, TIEN):
            do.append(f"{nhan_goi}: tool '{t}' đụng tới TIỀN mà Naota xếp vào nhóm {nhom}")
        elif cua_ho in ("write", "destructive") and nhom == "read":
            do.append(f"{nhan_goi}: tool '{t}' được bên chính chủ ghi là KHÔNG chỉ đọc mà Naota xếp "
                      f"vào nhóm đọc, tức chạy được ở mức Chỉ đọc. Khai nó trong tool_meta")
        elif (cua_ho == "destructive" or _khop(t, PHA)) and t not in da_can_nhac:
            ly_do = ("được bên chính chủ ghi là có thể PHÁ HUỶ" if cua_ho == "destructive"
                     else "nghe như phá huỷ hay tác động ra ngoài")
            do.append(f"{nhan_goi}: tool '{t}' {ly_do} mà Naota xếp vào nhóm {nhom}. Khai nó là "
                      f"danger trong tool_meta, hoặc thêm vào `ghi_da_can_nhac` nếu đã cân nhắc "
                      f"và thấy nó nhẹ")
        elif nhom == "read" and not any(fnmatch(t.lower(), p) for p in khai):
            chua_khai_doc.append(t)
    return do, chua_khai_doc


def soi_chinh_chu(classify, ghi_da_soat=False):
    """(lỗi đỏ, cảnh báo, số MCP đã soi) cho các MCP chính chủ chạy từ xa, xem `chinh_chu.py`."""
    do, canh, so = [], [], 0
    for tep in chinh_chu.cac_tep():
        d = chinh_chu.doc(tep)
        loi_ct = chinh_chu.loi_cau_truc(d)
        if loi_ct:
            do += [f"{tep.name}: {l}" for l in loi_ct]
            continue
        so += 1
        con = json.loads((GOC / d["connector"]).read_text(encoding="utf-8"))
        nhan_goi = f"{Path(d['connector']).parts[1]}/{con.get('id')} (chính chủ {d['repo']})"
        try:
            the = chinh_chu.ban_moi_nhat(d["repo"])
            moi, moi_lenh = chinh_chu.bo_tool(d["repo"], the, d["snapshots"],
                                              chinh_chu.lenh_can_theo_doi(con))
        except Exception as e:  # mạng, GitHub đổi cấu trúc thư mục...
            canh.append(f"{nhan_goi}: không đọc được bản mới nhất ({e})")
            print(f"?? {nhan_goi}: {e}")
            continue
        ten = sorted(set(moi) | set(d.get("tool_chi_o_ban_tu_xa") or []))
        do_ten, chua_khai_doc = soi_ten(classify, con, nhan_goi, ten, moi)
        do += do_ten
        if chua_khai_doc:
            canh.append(f"{nhan_goi}: {len(chua_khai_doc)} tool chưa khai, đang được ĐOÁN là đọc: "
                        + ", ".join(chua_khai_doc))

        for t, ds in sorted(moi_lenh.items()):
            luat = (con.get("call_rules") or {}).get(t) or {}
            khai = {str(x).lower() for k in ("read_values", "write_values", "danger_values")
                    for x in luat.get(k) or []}
            chua = [v for v in ds if v.lower() not in khai]
            if chua:
                canh.append(f"{nhan_goi}: {t} có lệnh chưa khai trong call_rules, đang rơi về mức "
                            f"{luat.get('else') or 'danger'}: " + ", ".join(chua))

        them, bot, doi = chinh_chu.khac_biet(d["tools"], moi)
        doi_lenh =chinh_chu.khac_biet_lenh(d.get("lenh") or {}, moi_lenh)
        if ghi_da_soat:
            if do_ten:
                print(f"!! {nhan_goi}: KHÔNG ghi bộ đã soát vì còn lỗi phân loại, sửa tool_meta trước")
            elif (them or bot or doi or doi_lenh or d["da_soat"] != the):
                d["da_soat"], d["tools"] = the, dict(sorted(moi.items()))
                if moi_lenh:
                    d["lenh"] = dict(sorted(moi_lenh.items()))
                else:
                    d.pop("lenh", None)
                chinh_chu.ghi(tep, d)
                print(f"ghi {tep.name}: đã soát {the}, {len(moi)} tool")
                them = bot = doi = doi_lenh = []
        if them or bot or doi or doi_lenh:
            phan = list(doi_lenh)
            if them:
                phan.append("thêm " + ", ".join(f"{t} ({moi[t]})" for t in them))
            if bot:
                phan.append("bớt " + ", ".join(bot))
            if doi:
                phan.append("đổi nhãn " + ", ".join(f"{t} ({d['tools'][t]} -> {moi[t]})" for t in doi))
            do.append(f"{nhan_goi}: bản chính chủ {the} (kho mới soát tới {d['da_soat']}) đổi bộ tool: "
                      + "; ".join(phan) + f". Đọc ghi chú phát hành https://github.com/{d['repo']}"
                      f"/releases/tag/{the}, sửa tool_meta hay call_rules nếu cần (ra bản gói mới), rồi ghi lại "
                      f"bộ đã soát: python tools/soi-ban-moi.py --chi-chinh-chu --ghi-da-soat")
        elif d["da_soat"] != the:
            print(f"ok {nhan_goi}: bản mới {the} không đổi tool so với {d['da_soat']} đã soát")
        print(f"ok {nhan_goi}: {the}, {len(ten)} tool")
    return do, canh, so


def main():
    classify = _nap_classify()
    chi_chinh_chu = "--chi-chinh-chu" in sys.argv[1:]
    do, canh = [], []
    so = 0
    for f in sorted((GOC / "packs").glob("*/connectors/*.json")):
        if chi_chinh_chu:
            break
        con = json.loads(f.read_text(encoding="utf-8"))
        if str(con.get("command") or "").lower() not in LENH:
            continue
        so += 1
        nhan_goi = f"{f.parent.parent.name}/{con.get('id')}"
        ten, e = liet_ke_tool(con)
        if ten is None:
            canh.append(f"{nhan_goi}: không mở được để soi ({e})")
            print(f"?? {nhan_goi}: {e}")
            continue
        do_ten, chua_khai_doc = soi_ten(classify, con, nhan_goi, ten)
        do += do_ten
        if chua_khai_doc:
            canh.append(f"{nhan_goi}: {len(chua_khai_doc)} tool chưa khai, đang được ĐOÁN là đọc: "
                        + ", ".join(chua_khai_doc))
        print(f"ok {nhan_goi}: {len(ten)} tool")

    do_cc, canh_cc, so_cc = soi_chinh_chu(classify, "--ghi-da-soat" in sys.argv[1:])
    do += do_cc
    canh += canh_cc
    so += so_cc

    print()
    for c in canh:
        print("canh bao: " + c)
    if do:
        print(f"ĐỎ {len(do)} lỗi:")
        for l in do:
            print("  - " + l)
        sys.exit(1)
    print(f"XANH - soi {so} MCP bên thứ 3 ở bản mới nhất, không tool nguy hiểm nào lọt nhóm, "
          f"bộ tool chính chủ khớp bản đã soát")


if __name__ == "__main__":
    main()
