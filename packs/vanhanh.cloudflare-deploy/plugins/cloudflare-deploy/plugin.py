"""Cloudflare Deploy (Wrangler): deploy Worker và trang web tĩnh, dùng chung token với kết nối
Cloudflare.

Vì sao là plugin chứ không chỉ là skill
--------------------------------------
MCP chính chủ của Cloudflare gọi được mọi API nhưng KHÔNG đóng gói code: đưa một dự án Worker
lên bằng nó là tự bundle bằng tay. Việc đó là của Wrangler. Còn Wrangler thì cần lệnh shell và
một API token trong biến môi trường, tức chỉ bộ não CLI chạy được, và token phải dán thêm một
lần nữa vào `.env` (nơi MỌI lệnh shell của bộ não đều đọc được nó).

Plugin này đi đường giữa: token lấy thẳng từ kết nối "cloudflare" (đã mã hoá trong kho kết
nối), chỉ đưa cho đúng tiến trình Wrangler của lần deploy đó, và bộ não nào cũng gọi được.

Rào an toàn (cố ý hẹp)
---------------------
- CHỈ ba việc: kiểm tra, deploy Worker, deploy trang tĩnh. KHÔNG có cửa chạy lệnh Wrangler bất
  kỳ: xoá Worker, xoá D1, đặt biến bí mật... vẫn đi qua MCP Cloudflare, nơi có phân loại quyền.
- Deploy thật chỉ chạy khi kết nối Cloudflare đang ở mức Toàn quyền. Kết nối mặc định Chỉ đọc,
  nên cài gói xong chưa deploy được gì cho tới khi chủ tự nâng quyền ở trang Kết nối.
- Chỉ nhận thư mục nằm trong bộ não đang dùng hoặc trong thư mục làm việc đã khai ở trang
  Coding. Không chạy được trên một đường dẫn tuỳ ý của máy.
- Không qua shell. Tham số do model đưa (tên dự án, nhánh, môi trường) đi qua regex chặt trước
  khi vào argv, vì trên Windows `npx` là tệp .cmd và cmd.exe tự diễn giải lại dòng lệnh.
- Env lọc trắng như `run_command` của lõi: tiến trình con KHÔNG thấy khoá trong `.env` của
  Vanhanh, chỉ thấy token Cloudflare và vài biến hệ thống cần để Node chạy.
- Token bị che khỏi mọi output trả về model.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

CONNECTOR_ID = "cloudflare"
WRANGLER = "wrangler@4"          # ghim bản chính: wrangler 5 đổi cờ thì gói không vỡ âm thầm
TIMEOUT_MAC_DINH = 600           # lần đầu npx phải tải Wrangler về, mất vài phút trên VPS yếu
TIMEOUT_TOI_DA = 900
OUTPUT_TOI_DA = 8000
OUTPUT_DAU = 2000
CONFIG_TEN = ("wrangler.jsonc", "wrangler.json", "wrangler.toml")

# Biến hệ thống tiến trình Node cần. So khớp không phân biệt hoa thường vì Windows.
_ENV_TRANG = {
    "PATH", "PATHEXT", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT",
    "COMSPEC", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "HTTPS_PROXY", "HTTP_PROXY",
    "NO_PROXY", "NPM_CONFIG_CACHE",
}

_RE_TEN_DU_AN = re.compile(r"^[a-z0-9][a-z0-9-]{0,57}$")
_RE_NHANH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")
_RE_MOI_TRUONG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_RE_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_RE_URL = re.compile(r"https://[A-Za-z0-9.-]+\.(?:workers|pages)\.dev[^\s\"'<>)]*")


# ============================================================
# Kết nối và token
# ============================================================
def _ket_noi(ten: str = ""):
    """(kết nối, lỗi). Chọn theo tên khi chủ có nhiều tài khoản Cloudflare."""
    try:
        import mcp_store
    except Exception:
        return None, "Không đọc được kho kết nối của Vanhanh."
    co = [c for c in mcp_store.list_connections()
          if c.get("connector_id") == CONNECTOR_ID and c.get("enabled", True)]
    if not co:
        return None, ("Chưa kết nối Cloudflare. Cài gói 'Cloudflare' trong Kho cài đặt rồi dán "
                      "API token ở trang Kết nối.")
    ten = str(ten or "").strip().lower()
    if ten:
        khop = [c for c in co if ten in {str(c.get(k) or "").strip().lower()
                                         for k in ("label", "slug", "id")}]
        if not khop:
            ds = ", ".join(str(c.get("label") or c.get("id")) for c in co)
            return None, f"Không có kết nối Cloudflare tên '{ten}'. Đang có: {ds}."
        return khop[0], ""
    for c in co:
        if c.get("is_default"):
            return c, ""
    return co[0], ""


def _bi_mat(conn) -> dict:
    try:
        import mcp_store
        return mcp_store.connection_secrets(conn["id"]) or {}
    except Exception:
        return {}


def _can_toan_quyen(conn) -> str:
    """'' nếu kết nối cho phép deploy thật, ngược lại là câu giải thích."""
    if (conn.get("perm") or "full") == "full":
        return ""
    return ("Kết nối Cloudflare đang ở mức "
            f"'{conn.get('perm')}', chưa cho deploy thật. Nâng kết nối đó lên Toàn quyền ở trang "
            "Kết nối rồi thử lại. Muốn xem trước mà không đổi gì thì gọi lại với dry_run=true.")


# ============================================================
# Thư mục được phép
# ============================================================
def _goc_cho_phep(ctx) -> list:
    goc = []
    if getattr(ctx, "vault_root", None):
        try:
            goc.append(Path(ctx.vault_root).resolve())
        except Exception:
            pass
    try:
        import coding_store
        for r in coding_store.danh_sach_thu_muc():
            try:
                goc.append(Path(r["duong_dan"]).resolve())
            except Exception:
                continue
    except Exception:
        pass
    return goc


def _thu_muc(ctx, raw):
    """(Path, lỗi). Đường dẫn tương đối tính từ gốc bộ não."""
    raw = str(raw or "").strip()
    if not raw:
        return None, "Thiếu 'path': thư mục dự án cần deploy."
    goc = _goc_cho_phep(ctx)
    if not goc:
        return None, "Không xác định được bộ não đang dùng."
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = goc[0] / p
    try:
        p = p.resolve()
    except Exception:
        return None, f"Đường dẫn không đọc được: {raw}"
    if not any(p == g or g in p.parents for g in goc):
        return None, ("Chỉ deploy được thư mục nằm trong bộ não đang dùng hoặc trong thư mục làm "
                      f"việc đã khai ở trang Coding. '{raw}' nằm ngoài các chỗ đó.")
    if not p.is_dir():
        return None, f"Không có thư mục {p}"
    return p, ""


def _tim_config(thu_muc: Path):
    for ten in CONFIG_TEN:
        f = thu_muc / ten
        if f.is_file():
            return f
    return None


def _doc_config(f: Path) -> dict:
    """Bóc vài trường để báo lại cho người dùng. Đọc hỏng thì trả rỗng, không chặn deploy:
    Wrangler mới là thứ phán cấu hình đúng hay sai."""
    try:
        s = f.read_text(encoding="utf-8")
    except Exception:
        return {}
    if f.suffix == ".toml":
        ra = {}
        for k in ("name", "main", "compatibility_date"):
            m = re.search(rf'^\s*{k}\s*=\s*"([^"]*)"', s, re.M)
            if m:
                ra[k] = m.group(1)
        return ra
    s = re.sub(r"(?m)^\s*//.*$", "", s)                 # jsonc: bỏ dòng chú thích
    try:
        d = json.loads(s)
    except Exception:
        return {}
    ra = {k: d.get(k) for k in ("name", "main", "compatibility_date") if d.get(k)}
    if isinstance(d.get("assets"), dict) and d["assets"].get("directory"):
        ra["assets"] = d["assets"]["directory"]
    return ra


# ============================================================
# Chạy tiến trình
# ============================================================
def _env(token: str, account_id: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k.upper() in _ENV_TRANG}
    env.setdefault("PATH", os.defpath)
    env.update({
        "CI": "true", "NO_COLOR": "1", "FORCE_COLOR": "0",
        "WRANGLER_SEND_METRICS": "false",
        "npm_config_yes": "true", "npm_config_update_notifier": "false",
        "npm_config_fund": "false", "npm_config_audit": "false",
    })
    if token:
        env["CLOUDFLARE_API_TOKEN"] = token
    if account_id:
        env["CLOUDFLARE_ACCOUNT_ID"] = account_id
    return env


def _giet(p):
    try:
        if os.name == "nt":
            import winproc
            winproc.kill_tree(p.pid)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def _chay_dong_bo(argv, cwd, env, timeout):
    kw = {}
    if os.name == "nt":
        try:
            import winproc
            kw.update(winproc.kwargs_no_window())
        except Exception:
            pass
    else:
        kw["start_new_session"] = True              # để giết được cả cây tiến trình khi quá giờ
    t0 = time.time()
    try:
        p = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    except OSError as e:
        return {"ma": -1, "out": f"Không chạy được {argv[0]}: {e}", "het_gio": False, "giay": 0}
    het_gio = False
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        het_gio = True
        _giet(p)
        try:
            out, _ = p.communicate(timeout=10)
        except Exception:
            out = b""
    return {"ma": p.returncode, "out": (out or b"").decode("utf-8", "replace"),
            "het_gio": het_gio, "giay": round(time.time() - t0, 1)}


async def _chay(argv, cwd, env, timeout):
    # Chạy trong thread chứ không dùng asyncio subprocess: uvicorn trên Windows có thể chạy
    # SelectorEventLoop, loại đó không mở được tiến trình con.
    return await asyncio.to_thread(_chay_dong_bo, argv, cwd, env, timeout)


def _sach(out: str, token: str) -> str:
    out = _RE_ANSI.sub("", out or "")
    if token:
        out = out.replace(token, "[đã che token]")
    if len(out) > OUTPUT_TOI_DA:
        duoi = OUTPUT_TOI_DA - OUTPUT_DAU
        out = out[:OUTPUT_DAU] + f"\n...[cắt bớt {len(out) - OUTPUT_TOI_DA} ký tự]...\n" + out[-duoi:]
    return out.strip()


def _timeout(args) -> int:
    try:
        t = int(float((args or {}).get("timeout_s") or TIMEOUT_MAC_DINH))
    except (TypeError, ValueError):
        t = TIMEOUT_MAC_DINH
    return max(30, min(t, TIMEOUT_TOI_DA))


def _npx():
    return shutil.which("npx")


def _thieu_node() -> str:
    return ("Máy chạy Vanhanh chưa có Node.js (không thấy lệnh npx). Cài Node.js 20 trở lên "
            "(nodejs.org) rồi khởi động lại Vanhanh. Bản Docker của Vanhanh đã có sẵn Node.")


def _ra(kq, token, **them):
    d = {"ok": kq["ma"] == 0 and not kq["het_gio"], "exit_code": kq["ma"],
         "seconds": kq["giay"]}
    if kq["het_gio"]:
        d["error"] = "Quá thời gian chờ, đã dừng tiến trình. Tăng timeout_s nếu dự án lớn."
    d.update(them)
    out = _sach(kq["out"], token)
    urls = sorted(set(_RE_URL.findall(out)))
    if urls:
        d["urls"] = urls
    d["output"] = out
    return d


async def _cai_goi_neu_can(thu_muc: Path, env, timeout, token):
    """npm ci / npm install khi có package.json mà chưa có node_modules. None nếu không cần."""
    if not (thu_muc / "package.json").is_file() or (thu_muc / "node_modules").is_dir():
        return None
    npm = shutil.which("npm")
    if not npm:
        return {"ok": False, "error": _thieu_node()}
    lenh = "ci" if (thu_muc / "package-lock.json").is_file() else "install"
    kq = await _chay([npm, lenh, "--no-audit", "--no-fund"], thu_muc, env, timeout)
    if kq["ma"] != 0 or kq["het_gio"]:
        return _ra(kq, token, step=f"npm {lenh}",
                   hint="Cài thư viện của dự án thất bại, chưa deploy gì.")
    return None


# ============================================================
# Tool
# ============================================================
async def _check(args, ctx):
    args = args or {}
    ra = {"node": None, "connection": None}
    node = shutil.which("node")
    if not node or not _npx():
        ra["error"] = _thieu_node()
        return ra
    v = _chay_dong_bo([node, "--version"], Path.cwd(), _env("", ""), 30)
    ra["node"] = (v["out"] or "").strip()

    conn, loi = _ket_noi(args.get("account"))
    if loi:
        ra["error"] = loi
        return ra
    sec = _bi_mat(conn)
    token = (sec.get("api_token") or "").strip()
    ra["connection"] = {"name": conn.get("label") or conn.get("id"), "perm": conn.get("perm"),
                        "deploy_allowed": not _can_toan_quyen(conn),
                        "account_id_set": bool((sec.get("account_id") or "").strip())}
    if not token:
        ra["error"] = "Kết nối Cloudflare chưa có API token. Dán lại token ở trang Kết nối."
        return ra

    if args.get("path"):
        thu_muc, loi = _thu_muc(ctx, args.get("path"))
        if loi:
            ra["project_error"] = loi
        else:
            cfg = _tim_config(thu_muc)
            ra["project"] = {"dir": str(thu_muc),
                             "config": cfg.name if cfg else None,
                             "has_package_json": (thu_muc / "package.json").is_file()}
            if cfg:
                ra["project"].update(_doc_config(cfg))

    kq = await _chay([_npx(), "--yes", WRANGLER, "whoami"], Path.cwd(),
                     _env(token, (sec.get("account_id") or "").strip()), _timeout(args))
    ra["whoami"] = _ra(kq, token)
    ra["ok"] = ra["whoami"]["ok"]
    return ra


async def _worker_deploy(args, ctx):
    args = args or {}
    if not _npx():
        return {"ok": False, "error": _thieu_node()}
    conn, loi = _ket_noi(args.get("account"))
    if loi:
        return {"ok": False, "error": loi}
    dry = bool(args.get("dry_run"))
    if not dry:
        loi = _can_toan_quyen(conn)
        if loi:
            return {"ok": False, "error": loi}
    thu_muc, loi = _thu_muc(ctx, args.get("path"))
    if loi:
        return {"ok": False, "error": loi}
    cfg = _tim_config(thu_muc)
    if not cfg:
        return {"ok": False, "error": (
            f"Thư mục {thu_muc} chưa có wrangler.jsonc, wrangler.json hay wrangler.toml. Tạo "
            "tệp cấu hình trước (xem skill deploy-cloudflare).")}
    moi_truong = str(args.get("env") or "").strip()
    if moi_truong and not _RE_MOI_TRUONG.match(moi_truong):
        return {"ok": False, "error": f"Tên môi trường không hợp lệ: {moi_truong!r}"}

    sec = _bi_mat(conn)
    token = (sec.get("api_token") or "").strip()
    if not token:
        return {"ok": False, "error": "Kết nối Cloudflare chưa có API token."}
    env = _env(token, (sec.get("account_id") or "").strip())
    timeout = _timeout(args)

    if args.get("install", True) is not False:
        hong = await _cai_goi_neu_can(thu_muc, env, timeout, token)
        if hong:
            return hong

    argv = [_npx(), "--yes", WRANGLER, "deploy"]
    if moi_truong:
        argv += ["--env", moi_truong]
    if dry:
        argv += ["--dry-run"]
    kq = await _chay(argv, thu_muc, env, timeout)
    return _ra(kq, token, dry_run=dry, dir=str(thu_muc), config=cfg.name,
               account=conn.get("label") or conn.get("id"), **_doc_config(cfg))


def _du_an_chua_co(out: str) -> bool:
    s = (out or "").lower()
    return "8000007" in s or "project not found" in s or "could not find project" in s


async def _pages_deploy(args, ctx):
    args = args or {}
    if not _npx():
        return {"ok": False, "error": _thieu_node()}
    conn, loi = _ket_noi(args.get("account"))
    if loi:
        return {"ok": False, "error": loi}
    loi = _can_toan_quyen(conn)
    if loi:
        return {"ok": False, "error": loi}
    thu_muc, loi = _thu_muc(ctx, args.get("path"))
    if loi:
        return {"ok": False, "error": loi}
    if not any(thu_muc.iterdir()):
        return {"ok": False, "error": f"Thư mục {thu_muc} trống, không có gì để đưa lên."}
    du_an = str(args.get("project_name") or "").strip().lower()
    if not _RE_TEN_DU_AN.match(du_an):
        return {"ok": False, "error": ("project_name chỉ gồm chữ thường không dấu, số và gạch "
                                       "nối, tối đa 58 ký tự, ví dụ 'trang-ban-hang'.")}
    # Bỏ trống thì ép "main" chứ không để Wrangler tự đoán: thư mục nằm trong bộ não, mà bộ não
    # thường là một repo git, nên Wrangler sẽ lấy nhánh của BỘ NÃO (vd master) và đẩy bản này
    # thành bản xem trước trong khi người dùng tưởng đã lên trang chính.
    nhanh = str(args.get("branch") or "").strip() or "main"
    if not _RE_NHANH.match(nhanh):
        return {"ok": False, "error": f"Tên nhánh không hợp lệ: {nhanh!r}"}

    sec = _bi_mat(conn)
    token = (sec.get("api_token") or "").strip()
    if not token:
        return {"ok": False, "error": "Kết nối Cloudflare chưa có API token."}
    env = _env(token, (sec.get("account_id") or "").strip())
    timeout = _timeout(args)

    argv = [_npx(), "--yes", WRANGLER, "pages", "deploy", ".", "--project-name", du_an,
            "--commit-dirty=true", "--branch", nhanh]
    kq = await _chay(argv, thu_muc, env, timeout)
    tao_moi = False
    if kq["ma"] != 0 and not kq["het_gio"] and _du_an_chua_co(kq["out"]):
        tao = await _chay([_npx(), "--yes", WRANGLER, "pages", "project", "create", du_an,
                           "--production-branch", "main"], thu_muc, env, timeout)
        if tao["ma"] != 0 or tao["het_gio"]:
            return _ra(tao, token, step="pages project create", project_name=du_an)
        tao_moi = True
        kq = await _chay(argv, thu_muc, env, timeout)
    return _ra(kq, token, project_name=du_an, branch=nhanh, project_created=tao_moi,
               dir=str(thu_muc),
               account=conn.get("label") or conn.get("id"))


_ACCOUNT = {"type": "string",
            "description": "Tên kết nối Cloudflare cần dùng khi có nhiều tài khoản. Bỏ trống = "
                           "kết nối mặc định."}
_TIMEOUT = {"type": "number", "description": "Giây chờ tối đa, mặc định 600, trần 900."}


def register(ctx):
    ctx.register_tool(
        name="cf_deploy_check",
        description=(
            "Cloudflare Deploy: kiểm tra trước khi deploy. Báo Node.js, kết nối Cloudflare nào "
            "đang dùng và đã cho deploy chưa, token đăng nhập được tài khoản nào (wrangler "
            "whoami). Truyền path để đọc thêm cấu hình wrangler của một dự án. Không đổi gì."),
        handler=_check, min_mode="readonly", emoji="🔍",
        schema={"type": "object", "properties": {
            "path": {"type": "string",
                     "description": "Thư mục dự án, tương đối với gốc bộ não. Tuỳ chọn."},
            "account": _ACCOUNT, "timeout_s": _TIMEOUT}},
    )
    ctx.register_tool(
        name="cf_worker_deploy",
        description=(
            "Cloudflare Deploy: deploy một dự án Worker (kể cả web tĩnh dùng Workers static "
            "assets) bằng 'wrangler deploy'. Thư mục phải có wrangler.jsonc/json/toml và nằm "
            "trong bộ não hoặc thư mục làm việc đã khai. Tự chạy npm install khi có "
            "package.json mà chưa có node_modules. dry_run=true chỉ đóng gói thử, không đưa "
            "lên. Deploy thật THAY bản đang chạy và cần kết nối Cloudflare ở mức Toàn quyền."),
        handler=_worker_deploy, min_mode="full", emoji="🚀",
        schema={"type": "object", "properties": {
            "path": {"type": "string", "description": "Thư mục dự án, tương đối với gốc bộ não"},
            "env": {"type": "string", "description": "Môi trường trong cấu hình (--env). Tuỳ chọn."},
            "dry_run": {"type": "boolean", "description": "true = chỉ đóng gói thử"},
            "install": {"type": "boolean",
                        "description": "false = không tự chạy npm install. Mặc định true."},
            "account": _ACCOUNT, "timeout_s": _TIMEOUT},
            "required": ["path"]},
    )
    ctx.register_tool(
        name="cf_pages_deploy",
        description=(
            "Cloudflare Deploy: đưa một thư mục web tĩnh đã dựng sẵn (HTML, CSS, ảnh) lên "
            "Cloudflare Pages bằng 'wrangler pages deploy'. Chưa có dự án Pages tên đó thì tự "
            "tạo. branch khác 'main' ra bản xem trước, không đè trang chính. Cần kết nối "
            "Cloudflare ở mức Toàn quyền."),
        handler=_pages_deploy, min_mode="full", emoji="🌐",
        schema={"type": "object", "properties": {
            "path": {"type": "string",
                     "description": "Thư mục chứa index.html, tương đối với gốc bộ não"},
            "project_name": {"type": "string",
                             "description": "Tên dự án Pages: chữ thường, số, gạch nối"},
            "branch": {"type": "string",
                       "description": "Nhánh. Bỏ trống = main, tức trang chính."},
            "account": _ACCOUNT, "timeout_s": _TIMEOUT},
            "required": ["path", "project_name"]},
    )
