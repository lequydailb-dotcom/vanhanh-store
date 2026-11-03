"""MCP của bên thứ 3 CHƯA phát hành lên npm: kho tự build từ đúng một commit và giữ tệp `.tgz`.

    python tools/mcp_dong_goi.py                 # liệt kê, và đối chiếu sha256 mọi tệp đã có
    python tools/mcp_dong_goi.py kiotviet-mcp    # build lại từ commit ghim trong mcp/nguon.json

Cần mạng, `git` và `npm`. Trình kiểm (`kiem-tra.py`) chỉ gọi phần đối chiếu, không chạm mạng.

Vì sao có thư mục `mcp/`
------------------------
Luật của kho là MCP bên thứ 3 đi theo bản chính thức trên npm (`@latest`, xem
`ban_chinh_thuc.py`). Vài MCP phần mềm bán hàng Việt Nam (KiotViet, Haravan, Nhanh.vn) chỉ có mã
trên GitHub, chưa bản phát hành nào, và đường GitHub cũng không chạy được:

- `npx -y github:chu/repo` vỡ với mọi gói cần build lúc cài (có script `prepare`): npm 10 báo
  "GitFetcher requires an Arborist constructor to pack a tarball". Hai MCP TypeScript ở đây đều
  thế, vì repo không chứa `dist/`.
- Kể cả khi chạy được, máy người dùng sẽ phải build TypeScript ở lần mở đầu tiên, và script build
  `rm -rf dist` không chạy trên Windows.

Nên kho build MỘT lần ở đây, từ một commit ghim cố định, rồi giữ tệp `npm pack` trong `mcp/`.
Connector chạy `npx -y --package=<URL tệp trong kho> <lệnh>`: npm tải tệp đó như mọi gói npm,
cài thư viện phụ thuộc từ npm như thường, và không phải build gì.

Ba điều giữ cho cách này đọc được và kiểm được:

1. `mcp/nguon.json` ghi repo gốc, commit, sha256 của tệp, và mọi chỗ kho SỬA so với bản gốc
   (`va`). Người review mở commit đó trên GitHub là đọc được đúng mã sẽ chạy.
2. Tên tệp mang số phiên bản LẪN commit, và không bao giờ ghi đè: đổi commit là ra tệp mới,
   connector đổi URL, ra bản gói mới. Như `dist/`, tệp cũ được giữ lại.
3. `kiem-tra.py` đối chiếu sha256 của từng tệp với `nguon.json`, và mọi connector trỏ vào
   `mcp/` phải trỏ đúng một tệp có trong đó.

Khi bên thứ 3 phát hành lên npm, bỏ đường này: đổi connector về `ten-goi@latest`, xoá khoá
`ngoai_le_ban_chinh_thuc`, ra bản gói mới.

MCP kho TỰ VIẾT (mục có `thu_muc` thay cho `repo` + `commit`, ví dụ `mcp-nguon/pancake-chat-mcp`)
---------------------------------------------------------------------------------------------
Khi không có MCP nào dùng được cho một dịch vụ, kho viết một cái nhỏ, mã nguồn nằm ngay trong
`mcp-nguon/<tên>/`. Nó KHÔNG được có thư viện phụ thuộc: tệp `.tgz` đóng bằng Python ở đây (không qua
npm), ghim ngày giờ và quyền tệp, nên đóng lại luôn ra đúng một sha256, và trình kiểm so được từng
tệp trong `.tgz` với thư mục nguồn. Sửa mã mà quên đóng lại là CI đỏ. Đổi mã thì tăng `phien_ban`
(tên tệp mang số bản, không bao giờ ghi đè) và ra bản gói mới. Bản cũ ghi vào `ban_cu` (phien_ban + sha256)
và tệp của nó ở lại `mcp/`: máy chưa cập nhật gói vẫn tải đúng URL cũ.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC = GOC / "mcp"
NGUON = THU_MUC / "nguon.json"
# Địa chỉ connector dùng để tải tệp. Nhánh `main`: tệp trong `mcp/` không bao giờ bị ghi đè, nên
# URL theo tên tệp đã là URL bất biến.
URL_GOC = "https://raw.githubusercontent.com/lequydailb-dotcom/vanhanh-store/main/mcp/"


def doc_nguon():
    if not NGUON.is_file():
        return []
    return json.loads(NGUON.read_text(encoding="utf-8")).get("mcp") or []


def ten_tep(m):
    if m.get("thu_muc"):
        return f"{m['ten']}-{m['phien_ban']}.tgz"
    return f"{m['ten']}-{m['phien_ban']}-{m['commit'][:7]}.tgz"


def _tep_nguon(thu_muc: Path):
    """Tệp của một MCP tự viết, theo đúng `files` của package.json (cộng package.json), sắp theo tên."""
    pj = json.loads((thu_muc / "package.json").read_text(encoding="utf-8"))
    if pj.get("dependencies"):
        raise ValueError(f"{thu_muc.name}: MCP tự viết không được có dependencies")
    ten = sorted(set(["package.json"] + list(pj.get("files") or [])))
    return [(t, thu_muc / t) for t in ten]


def _dong_tu_thu_muc(thu_muc: Path, dich: Path) -> None:
    """Đóng `.tgz` dạng npm (mọi tệp dưới `package/`) với ngày giờ, chủ sở hữu và quyền GHIM, để đóng lại
    ở đâu cũng ra cùng byte. Tệp `bin` được quyền chạy."""
    import gzip
    import io
    import tarfile
    pj = json.loads((thu_muc / "package.json").read_text(encoding="utf-8"))
    chay = set((pj.get("bin") or {}).values()) if isinstance(pj.get("bin"), dict) else set()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for ten, p in _tep_nguon(thu_muc):
            b = p.read_bytes()
            ti = tarfile.TarInfo("package/" + ten)
            ti.size, ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = len(b), 499162500, 0, 0, "", ""
            ti.mode = 0o755 if ten in chay else 0o644
            tar.addfile(ti, io.BytesIO(b))
    with open(dich, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
        gz.write(raw.getvalue())


def _lech_voi_nguon(m, tep: Path):
    """Tên các tệp trong `.tgz` của MCP tự viết KHÁC thư mục nguồn (thiếu, thừa hay khác byte)."""
    import tarfile
    goc = GOC / m["thu_muc"]
    can = {"package/" + t: p.read_bytes() for t, p in _tep_nguon(goc)}
    co = {}
    with tarfile.open(tep, "r:gz") as tar:
        for ti in tar.getmembers():
            if ti.isfile():
                co[ti.name] = tar.extractfile(ti).read()
    return sorted(k for k in set(can) | set(co) if can.get(k) != co.get(k))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def doi_chieu():
    """Danh sách lỗi: tệp thiếu, sha256 lệch, hay tệp lạ không có trong `nguon.json`. Không chạm mạng."""
    loi = []
    biet = set()
    for m in doc_nguon():
        tu_viet = bool(m.get("thu_muc"))
        for k in ("ten", "phien_ban", "sha256", "lenh") + (() if tu_viet else ("repo", "commit")):
            if not m.get(k):
                loi.append(f"mcp/nguon.json: mục {m.get('ten', '?')} thiếu `{k}`")
        if tu_viet and not (GOC / str(m["thu_muc"]) / "package.json").is_file():
            loi.append(f"mcp/nguon.json: {m.get('ten')} trỏ tới thư mục nguồn không có package.json")
            continue
        if not tu_viet and len(str(m.get("commit") or "")) != 40:
            loi.append(f"mcp/nguon.json: {m.get('ten')} phải ghim commit đủ 40 ký tự")
            continue
        tep = THU_MUC / ten_tep(m)
        biet.add(tep.name)
        if not tep.is_file():
            loi.append(f"mcp/{tep.name}: không có tệp (chạy tools/mcp_dong_goi.py {m['ten']})")
        elif sha256(tep) != m.get("sha256"):
            loi.append(f"mcp/{tep.name}: sha256 không khớp mcp/nguon.json")
        elif tu_viet:
            try:
                lech = _lech_voi_nguon(m, tep)
            except (OSError, ValueError) as e:
                lech = [str(e)]
            if lech:
                loi.append(f"mcp/{tep.name}: khác mã nguồn {m['thu_muc']} ở {', '.join(lech)} "
                           f"(sửa mã thì tăng phien_ban rồi chạy tools/mcp_dong_goi.py {m['ten']})")
        # Bản cũ đã phát hành (`ban_cu`): GIỮ tệp, vì máy còn cài bản gói cũ vẫn tải đúng URL đó. Mỗi bản ghi
        # sha256 lúc phát hành, nên tệp cũ bị sửa hay mất đều đỏ như tệp hiện hành.
        for cu in m.get("ban_cu") or []:
            tep_cu = THU_MUC / ten_tep({**m, **cu})
            biet.add(tep_cu.name)
            if not tep_cu.is_file():
                loi.append(f"mcp/{tep_cu.name}: bản cũ khai trong ban_cu nhưng không có tệp (không được xoá tệp đã phát hành)")
            elif sha256(tep_cu) != cu.get("sha256"):
                loi.append(f"mcp/{tep_cu.name}: sha256 không khớp ban_cu trong mcp/nguon.json")
    for p in THU_MUC.glob("*.tgz") if THU_MUC.is_dir() else []:
        if p.name not in biet:
            loi.append(f"mcp/{p.name}: tệp lạ, không có trong mcp/nguon.json")
    return loi


def tep_tu_args(args):
    """Tên tệp trong `mcp/` mà lệnh npx của connector trỏ tới, hoặc "" nếu không trỏ vào kho."""
    for a in args or []:
        a = str(a)
        if a.startswith("--package="):
            a = a.split("=", 1)[1]
        if a.startswith(URL_GOC):
            return a[len(URL_GOC):]
    return ""


def _chay(lenh, cwd):
    exe = shutil.which(lenh[0]) or lenh[0]
    subprocess.run([exe] + lenh[1:], cwd=cwd, check=True)


def _sua(thu_muc: Path, va):
    """Áp các chỗ sửa khai trong `va`. Chỉ hai kiểu, cố ý ít: thêm `bin` vào package.json, và
    thêm dòng shebang. Sửa gì khác thì nên gửi PR cho tác giả gốc chứ không vá ở đây."""
    for s in va or []:
        if s.get("loai") == "bin":
            pj = thu_muc / "package.json"
            d = json.loads(pj.read_text(encoding="utf-8"))
            d["bin"] = {s["ten"]: s["tep"]}
            pj.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        elif s.get("loai") == "shebang":
            f = thu_muc / s["tep"]
            noi = f.read_text(encoding="utf-8")
            if not noi.startswith("#!"):
                f.write_text("#!/usr/bin/env node\n" + noi, encoding="utf-8")
        else:
            raise SystemExit(f"không biết kiểu sửa {s.get('loai')!r}")


def dong(ten):
    ds = doc_nguon()
    m = next((x for x in ds if x["ten"] == ten), None)
    if not m:
        raise SystemExit(f"{ten} không có trong mcp/nguon.json")
    if m.get("thu_muc"):
        THU_MUC.mkdir(exist_ok=True)
        dich = THU_MUC / ten_tep(m)
        with tempfile.TemporaryDirectory(prefix="vanhanh-mcp-") as tmp:
            moi = Path(tmp) / dich.name
            _dong_tu_thu_muc(GOC / m["thu_muc"], moi)
            if dich.exists() and sha256(dich) != sha256(moi):
                raise SystemExit(f"mcp/{dich.name} đã phát hành với nội dung khác; đổi mã thì tăng phien_ban "
                                 f"trong mcp/nguon.json và package.json (không ghi đè tệp đã phát hành)")
            shutil.copyfile(moi, dich)
        return _xong(ds, m, dich)
    with tempfile.TemporaryDirectory(prefix="vanhanh-mcp-") as tmp:
        src = Path(tmp) / "src"
        _chay(["git", "clone", "-q", m["repo"], str(src)], tmp)
        _chay(["git", "checkout", "-q", m["commit"]], src)
        _sua(src, m.get("va"))
        # --ignore-scripts: không chạy script cài đặt của thư viện phụ thuộc trên máy build.
        if (src / "package-lock.json").is_file():
            _chay(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], src)
        else:
            _chay(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"], src)
        # `npm pack` tự chạy `prepare` (tức build) trước khi đóng gói.
        _chay(["npm", "pack", "--pack-destination", tmp], src)
        ra = next(Path(tmp).glob("*.tgz"))
        THU_MUC.mkdir(exist_ok=True)
        dich = THU_MUC / ten_tep(m)
        shutil.copyfile(ra, dich)
    return _xong(ds, m, dich)


def _xong(ds, m, dich):
    m["sha256"] = sha256(dich)
    NGUON.write_text(json.dumps({"_doc": json.loads(NGUON.read_text(encoding="utf-8")).get("_doc"),
                                 "mcp": ds}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"mcp/{dich.name}  ({dich.stat().st_size:,} byte)")
    print("sha256:", m["sha256"])
    print("Lệnh connector:", json.dumps(["-y", f"--package={URL_GOC}{dich.name}"] + m["lenh"],
                                         ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dong(sys.argv[1])
    else:
        for m in doc_nguon():
            nguon = m["thu_muc"] if m.get("thu_muc") else f"{m['repo']} @ {m['commit'][:7]}"
            print(f"{m['ten']:<18} {nguon}  -> mcp/{ten_tep(m)}")
        loi = doi_chieu()
        for l in loi:
            print("  - " + l)
        sys.exit(1 if loi else 0)
