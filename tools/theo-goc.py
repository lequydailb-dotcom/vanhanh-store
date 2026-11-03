"""Gói THEO REPO GỐC: skill chép NGUYÊN VĂN từ repo GitHub của tác giả, đồng bộ lại mỗi ngày.

    python tools/theo-goc.py              đồng bộ mọi gói khai trong theo-goc/
    python tools/theo-goc.py <id> [...]   chỉ những gói này
    python tools/theo-goc.py --kiem       chỉ báo gói nào có bản mới ở repo gốc, không ghi gì
    python tools/theo-goc.py --khong-ma   ghi gói chỉ đổi chữ, gói có tệp mã đổi thì để lại (CI)

Vì sao có loại gói này
----------------------
Gói skill bên thứ 3 trước đây (Hermes, Superpowers, ECC...) là BẢN CHỤP: chép một lần, sửa
frontmatter cho khớp Vanhanh, rồi đứng yên ở 1.0.0. Tác giả gốc sửa skill bao nhiêu lần thì người
dùng Vanhanh vẫn chạy bản cũ, vì không ai nhớ đi chép lại.

Một mục "repo khuyên dùng", giữ nguyên chất repo gốc mà lại được cập
nhật thường xuyên. Tệp này là nửa kho của ý đó:

- Mỗi gói khai một tệp `theo-goc/<id>.json`: repo gốc, nhánh, và thư mục nào chép vào đâu.
- Mỗi ngày job `theo-goc` trong CI chạy tệp này. Repo gốc đổi nội dung skill thì gói lên một
  bản vá (1.0.0 -> 1.0.1), zip đóng lại, `index.json` ghi commit gốc mà nội dung được lấy từ đó.
- Vanhanh đã có sẵn phần còn lại: chuông báo "Store có bản mới", nút Cập nhật qua màn hình xác
  nhận, và luật không ghi đè tệp người dùng đã sửa (`pack_vault.py` bên vanhanh).

Giữ nguyên chất nghĩa là KHÔNG sửa một byte nào của skill: không dịch, không rút gọn mô tả,
không thêm `group`. Khác hẳn gói bản chụp ở trên. Cái giá: mô tả dài hơn 150 ký tự bị router
của Vanhanh cắt, nên chỉ nhận vào đây repo có câu mở đầu mô tả đủ nghĩa.

Gói agent (`den: "agents"`, từ 2026-10-29)
------------------------------------------
Repo như agency-agents để mỗi agent là một tệp `.md` có frontmatter kiểu Claude Code (`name`,
`description`, `color`...). Vanhanh đọc agent bằng khoá khác (`name`, `role`, `tags`), nên với agent
THÂN PROMPT giữ nguyên từng byte, còn phần đầu tệp thêm vài khoá cho Vanhanh: `type`, `slug`, `name`
và `role` (tiếng Việt nếu có bản dịch), `tags`, `group`. Tên gốc chuyển sang `ten_goc`, các khoá gốc
khác giữ nguyên dòng. Mỗi mục `chep` là một nhóm agent, khai `nhan` (tên nhóm vi/en, thành tag) và
`category` (nhóm trong Store, nhãn khai ở `nhom_kho`). `tien_to` đặt trước slug để không đè agent
cùng tên người dùng đã có.

Tên và mô tả tiếng Việt nằm ở `theo-goc/dich/<id>.json` ({tên tệp gốc: [tên, mô tả]}), do người
viết. Agent mới ở repo gốc chưa có bản dịch thì dùng tên và mô tả tiếng Anh, không chặn đồng bộ.

`tach` (tiền tố id, ví dụ `vanhanh.agency.`): ngoài gói gộp, mỗi agent còn thành MỘT gói riêng trong
Store để người dùng cài lẻ từng agent. Gói lẻ dựng lại cùng lượt với gói gộp, từ đúng nội dung đó,
lên bản vá khi agent của nó đổi, và biến mất khi repo gốc bỏ agent. Gói lẻ không mang `upstream`
(chỉ gói gộp nằm ở mục Đề xuất), mà mang `thuoc_goi` trỏ về gói gộp.

Khi nào cần người duyệt
-----------------------
Kho có luật mọi gói đều được đọc trước khi trộn. Đồng bộ tự động không phá luật đó, nó chia hai:

- Chỉ đổi tệp CHỮ (`.md`, `.txt`, ảnh, dữ liệu `.json`/`.yaml`): đẩy thẳng vào `main`. Repo đã
  được chủ kho chọn là đáng tin, và chữ hướng dẫn đổi là chuyện thường ngày của repo đó.
- Có tệp MÃ đổi hay thêm (script, `.py`, `.js`, `.ts`...): mở Pull Request, chờ chủ kho đọc.
  Vanhanh không bao giờ thấy bản đó cho tới khi PR được trộn.

Job CI chạy hai lượt: `--khong-ma` ghi và đẩy thẳng các gói chỉ đổi chữ, rồi lượt thứ hai ghi các gói
có trong dòng `cho_duyet=` (tệp này ghi vào `$GITHUB_OUTPUT`) lên nhánh riêng kèm Pull Request.

Luật chép, mặc định TỪ CHỐI
---------------------------
Cùng trần với trình cài của Vanhanh (`pack_install.py`), để gói đồng bộ xong luôn cài được:
không liên kết mềm, không tên nhạy cảm (`.env`, khoá riêng), tối đa 500 tệp, 5 MB một tệp,
40 MB cả gói. Vượt trần thì job đỏ và gói đứng yên ở bản cũ, không bao giờ phát hành nửa vời.
"""
import datetime
import hashlib
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
CAU_HINH = GOC / "theo-goc"
GOI = GOC / "packs"
INDEX = GOC / "index.json"
DIST = GOC / "dist"
# Chỉ test đổi chỗ này (trỏ vào repo git trên đĩa). Vanhanh và CI luôn lấy từ GitHub.
GIT_GOC = os.environ.get("THEO_GOC_GIT_GOC") or "https://github.com/"

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_TIEN_TO_RE = re.compile(r"^[a-z0-9-]{0,16}$")
_TACH_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,30}\.$")
_KHOA_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
# Gạch dài và gạch vừa (U+2014, U+2013) trong mô tả gốc: luật của chủ kho cấm chúng trong chữ
# kho tự viết ra (danh mục, manifest). Thân agent của tác giả thì không đụng tới.
_GACH_DAI = re.compile("\\s*[\u2014\u2013]\\s*")
# Khoá frontmatter Vanhanh tự đặt cho agent. Repo gốc có khoá trùng tên thì bỏ dòng gốc, khỏi trùng khoá.
KHOA_VANHANH = ("type", "slug", "name", "role", "tags", "group", "ten_goc", "nguon")
BO_QUA = ("__pycache__", ".git", ".DS_Store", ".pytest_cache", "node_modules")
TEN_CAM = (".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")
DUOI_CAM = (".pem", ".p12", ".pfx", ".key", ".ppk")
# Đuôi coi là CHỮ: đổi chúng không cần người duyệt. Mọi đuôi khác coi là MÃ.
# HTML và CSS tính là chữ: trong skill chúng là mẫu trang để AI dựng theo, không phải thứ Vanhanh chạy.
DUOI_CHU = (".md", ".txt", ".json", ".yaml", ".yml", ".geojson", ".csv", ".png", ".jpg", ".jpeg",
            ".webp", ".gif", ".svg", ".html", ".css", ".dot", ".ttf", ".otf", ".woff", ".woff2")
TEN_CHU = ("LICENSE", "NOTICE", "README", "AUTHORS", "CHANGELOG")
TRAN_SO_TEP, TRAN_MOT_TEP, TRAN_TONG = 500, 5 * 1024 * 1024, 40 * 1024 * 1024


class LoiDongBo(Exception):
    pass


def doc_cau_hinh(pid: str) -> dict:
    """Đọc và kiểm `theo-goc/<id>.json`. Sai một trường là từ chối cả gói."""
    if not _ID_RE.match(pid):
        raise LoiDongBo(f"id lạ: {pid!r}")
    c = json.loads((CAU_HINH / f"{pid}.json").read_text(encoding="utf-8"))
    if not _REPO_RE.match(str(c.get("repo") or "")):
        raise LoiDongBo(f"{pid}: `repo` phải dạng chủ/tên")
    if not _REF_RE.match(str(c.get("ref") or "")) or ".." in c["ref"]:
        raise LoiDongBo(f"{pid}: `ref` (nhánh) không hợp lệ")
    chep = c.get("chep")
    if not isinstance(chep, list) or not chep:
        raise LoiDongBo(f"{pid}: thiếu `chep`")
    for m in chep:
        for k in ("tu", "den"):
            v = str(m.get(k) or "")
            if not v or v.startswith("/") or ".." in v.split("/"):
                raise LoiDongBo(f"{pid}: đường dẫn `{k}` không hợp lệ: {v!r}")
        for k in ("chi", "bo", "bo_tep"):
            if not isinstance(m.get(k, []), list):
                raise LoiDongBo(f"{pid}: `{k}` phải là danh sách")
        if not isinstance(m.get("doi_ten", {}), dict):
            raise LoiDongBo(f"{pid}: `doi_ten` phải là map tên gốc -> tên mới")
        if not isinstance(m.get("phang", False), bool) or (m.get("phang") and m.get("ten")):
            raise LoiDongBo(f"{pid}: `phang` phải là true/false và không đi cùng `ten`")
        for b in m.get("bo_tep") or []:
            if not b or str(b).startswith("/") or ".." in str(b).split("/"):
                raise LoiDongBo(f"{pid}: `bo_tep` không hợp lệ: {b!r}")
        if m["den"] not in ("skills", "agents"):
            raise LoiDongBo(f"{pid}: chỉ chép vào `skills` hoặc `agents` (đang khai {m['den']!r})")
        if m["den"] == "agents":
            if m.get("ten") or m.get("phang") or m.get("bo_tep"):
                raise LoiDongBo(f"{pid}: mục `agents` không nhận `ten`, `phang`, `bo_tep`")
            nhan = m.get("nhan") or {}
            if not (isinstance(nhan, dict) and nhan.get("vi") and nhan.get("en")):
                raise LoiDongBo(f"{pid}: mục `agents` cần `nhan` có vi và en")
            if m.get("category") not in (c.get("nhom_kho") or {}):
                raise LoiDongBo(f"{pid}: category {m.get('category')!r} chưa khai trong `nhom_kho`")
    if not _TIEN_TO_RE.match(str(c.get("tien_to") or "")):
        raise LoiDongBo(f"{pid}: `tien_to` chỉ gồm chữ thường, số, gạch nối, tối đa 16 ký tự")
    for cat, nhan in (c.get("nhom_kho") or {}).items():
        if not (isinstance(nhan, dict) and nhan.get("vi") and nhan.get("en")):
            raise LoiDongBo(f"{pid}: `nhom_kho.{cat}` cần vi và en")
    if c.get("tach"):
        if not _TACH_RE.match(str(c["tach"])):
            raise LoiDongBo(f"{pid}: `tach` phải là tiền tố id kết thúc bằng dấu chấm, ví dụ `vanhanh.agency.`")
        if not any(m["den"] == "agents" for m in chep):
            raise LoiDongBo(f"{pid}: `tach` chỉ dùng cho gói có agent")
    goi = c.get("goi") or {}
    for k in ("name", "description", "author", "category", "category_label", "license"):
        if not goi.get(k):
            raise LoiDongBo(f"{pid}: thiếu `goi.{k}`")
    return c


def _git(*args, cwd=None) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise LoiDongBo(f"git {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


def tai_goc(c: dict, dich: Path) -> str:
    """Clone nông đúng nhánh khai báo. Trả commit đang đứng.

    Chỉ tải những thư mục `chep` cần (sparse checkout, kèm các tệp ở gốc repo như LICENSE): repo như
    GitNexus hay HyperFrames nặng 400 MB mà skill chỉ vài MB, và job này chạy mỗi ngày. Skill nằm ở gốc
    repo (`tu: "."`) thì cần cả cây, nên tải đủ."""
    _git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", c["ref"],
         f"{GIT_GOC}{c['repo']}.git", str(dich))
    thu_muc = sorted({m["tu"] for m in c["chep"]})
    if "." in thu_muc:
        _git("sparse-checkout", "disable", cwd=dich)
    else:
        _git("sparse-checkout", "set", *thu_muc, cwd=dich)
    return _git("rev-parse", "HEAD", cwd=dich)


def _kiem_tep(p: Path, goc: Path) -> None:
    rel = p.relative_to(goc).as_posix()
    if p.is_symlink():
        raise LoiDongBo(f"liên kết mềm không được chép: {rel}")
    ten = p.name.lower()
    if ten in TEN_CAM or ten.startswith(".env") or ten.endswith(DUOI_CAM) or ten.startswith("id_rsa"):
        raise LoiDongBo(f"tên nhạy cảm: {rel}")
    if p.stat().st_size > TRAN_MOT_TEP:
        raise LoiDongBo(f"tệp quá 5 MB: {rel}")


def _chep_cay(goc: Path, dich: Path, nguon: Path, bo_tep=()) -> None:
    """Chép cả cây `goc` sang `dich`, bỏ thư mục rác và những đường dẫn tương đối nằm trong `bo_tep`."""
    for p in sorted(goc.rglob("*")):
        rel = p.relative_to(goc)
        if any(x in rel.parts for x in BO_QUA) or any(rel.parts[:len(Path(b).parts)] == Path(b).parts
                                                      for b in bo_tep):
            continue
        if rel.parts and rel.parts[0].startswith(".") and goc == nguon:
            continue        # skill ở gốc repo: .github, .claude... là đồ của repo, không phải của skill
        if p.is_symlink() or p.is_file():
            _kiem_tep(p, nguon)
            d = dich / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, d)


def dung_ban_moi(c: dict, nguon: Path, ra: Path, tt: dict = None, dich: dict = None) -> list:
    """Dựng nội dung mới vào `ra`, theo đúng hình dạng nó sẽ nằm trong gói. Trả danh sách tên mục.

    `tt` (nếu truyền) nhận {tên: thông tin} của từng mục: `den` (skills/agents), và với agent thêm
    tên, mô tả vi/en, nhóm, tệp gốc, để dựng manifest và gói lẻ. `dich` là bảng dịch của gói.
    Mục `chep` có `den: "agents"` đi đường `_chep_agents`, xem đầu tệp.

    Mỗi mục `chep` lấy các thư mục con có SKILL.md của `tu`. Tuỳ chọn, đều KHÔNG sửa nội dung skill:
      chi      chỉ lấy những skill này (repo có skill nội bộ, hay skill có giấy phép không cho phát lại);
      bo       bỏ những skill này;
      doi_ten  đổi tên THƯ MỤC khi trùng slug với gói khác trong cùng brain (nội dung giữ nguyên);
      ten      `tu` tự nó là một skill (SKILL.md nằm ngay ở đó, thường là gốc repo): tên thư mục trong gói;
      bo_tep   với skill `ten`: đường dẫn tương đối không chép theo (test, ảnh demo, thư mục skill khác);
      phang    repo để skill thành tệp `.md` phẳng (`skills/fk-x.md`, như FlowKit) thay vì thư mục có
               SKILL.md: mỗi tệp `.md` trừ README là một skill, tên theo tên tệp, chép NGUYÊN VĂN
               thành `<tên>/SKILL.md`. Tệp không có frontmatter thì Vanhanh lấy dòng đầu làm mô tả."""
    skills, tu_dau = [], {}
    tt = {} if tt is None else tt
    for m in c["chep"]:
        tu = nguon / m["tu"]
        if not tu.is_dir():
            raise LoiDongBo(f"repo gốc không còn thư mục {m['tu']}")
        if m["den"] == "agents":
            _chep_agents(c, m, tu, nguon, ra, skills, tu_dau, tt, dich or {})
            continue
        if m.get("ten"):
            if not (tu / "SKILL.md").is_file():
                raise LoiDongBo(f"repo gốc không còn {m['tu']}/SKILL.md")
            cap = [(tu, m["ten"])]
        elif m.get("phang"):
            chi, bo = set(m.get("chi") or []), set(m.get("bo") or [])
            cap = [(f, (m.get("doi_ten") or {}).get(f.stem, f.stem)) for f in sorted(tu.iterdir())
                   if not f.is_symlink() and f.is_file() and f.suffix == ".md"
                   and f.stem.upper() not in TEN_CHU and (not chi or f.stem in chi) and f.stem not in bo]
            thieu = chi - {f.stem for f, _ in cap}
            if thieu:
                raise LoiDongBo(f"repo gốc không còn skill: {', '.join(sorted(thieu))}")
        else:
            chi, bo = set(m.get("chi") or []), set(m.get("bo") or [])
            cap = [(d, (m.get("doi_ten") or {}).get(d.name, d.name)) for d in sorted(tu.iterdir())
                   if not d.is_symlink() and d.is_dir() and (d / "SKILL.md").is_file()
                   and (not chi or d.name in chi) and d.name not in bo]
            thieu = chi - {d.name for d, _ in cap}
            if thieu:
                raise LoiDongBo(f"repo gốc không còn skill: {', '.join(sorted(thieu))}")
        for d, ten in cap:
            if not _ID_RE.match(ten):
                raise LoiDongBo(f"tên skill lạ: {ten!r}")
            if ten in skills:
                raise LoiDongBo(f"hai skill trùng tên: {ten}")
            skills.append(ten)
            tt[ten] = {"den": "skills"}
            tu_dau[ten] = m["tu"] if m.get("ten") else f"{m['tu']}/{d.name}"
            if m.get("phang"):
                _kiem_tep(d, nguon)
                (ra / m["den"] / ten).mkdir(parents=True)
                shutil.copyfile(d, ra / m["den"] / ten / "SKILL.md")
            else:
                _chep_cay(d, ra / m["den"] / ten, nguon, m.get("bo_tep") or ())
    if not skills:
        raise LoiDongBo("repo gốc không có mục nào ở thư mục đã khai")
    (ra / "docs").mkdir(parents=True, exist_ok=True)
    for ten in c.get("giay_phep") or ["LICENSE"]:
        p = nguon / ten
        if p.is_file() and not p.is_symlink():
            shutil.copyfile(p, ra / "docs" / ("LICENSE-goc" + (Path(ten).suffix or ".txt")))
    (ra / "docs" / "NGUON.md").write_text(_nguon_md(c, tu_dau, tt), encoding="utf-8")
    tep = [p for p in ra.rglob("*") if p.is_file()]
    if len(tep) > TRAN_SO_TEP:
        raise LoiDongBo(f"quá {TRAN_SO_TEP} tệp ({len(tep)})")
    if sum(p.stat().st_size for p in tep) > TRAN_TONG:
        raise LoiDongBo("quá 40 MB")
    return skills


def _chep_agents(c, m, tu, nguon, ra, ten_da_co, tu_dau, tt, dich) -> None:
    """Một mục `chep` kiểu agent: mỗi tệp `.md` có frontmatter trong `tu` (kể cả thư mục con) là một
    agent, thành `agents/<tien_to><tên tệp>.md`. `chi`, `bo`, `doi_ten` theo TÊN TỆP gốc (không đuôi)."""
    chi, bo = set(m.get("chi") or []), set(m.get("bo") or [])
    tep = [f for f in sorted(tu.rglob("*.md"))
           if not any(x.startswith(".") or x in BO_QUA for x in f.relative_to(tu).parts)
           and f.stem.upper() not in TEN_CHU and (not chi or f.stem in chi) and f.stem not in bo]
    thieu = chi - {f.stem for f in tep}
    if thieu:
        raise LoiDongBo(f"repo gốc không còn agent: {', '.join(sorted(thieu))}")
    for f in tep:
        _kiem_tep(f, nguon)
        if not f.is_file():
            continue
        ten = (c.get("tien_to") or "") + (m.get("doi_ten") or {}).get(f.stem, f.stem)
        if not _ID_RE.match(ten):
            raise LoiDongBo(f"tên agent lạ: {ten!r}")
        if ten in ten_da_co:
            raise LoiDongBo(f"hai mục trùng tên: {ten}")
        rel = f.relative_to(nguon).as_posix()
        van_ban, thong_tin = _agent_vanhanh(f.read_text(encoding="utf-8"), ten, c, m, dich.get(f.stem), rel)
        (ra / "agents").mkdir(parents=True, exist_ok=True)
        (ra / "agents" / f"{ten}.md").write_text(van_ban, encoding="utf-8")
        ten_da_co.append(ten)
        tu_dau[ten] = rel
        tt[ten] = dict(thong_tin, den="agents", goc=f.stem, category=m["category"], tu=rel)


def _khoi_frontmatter(fm: str) -> list:
    """Chia frontmatter thành [(khoá, [các dòng])]. Một khoá ăn mọi dòng sau nó tới khoá kế tiếp
    (giá trị nhiều dòng, danh sách `- a`). Không cần PyYAML: job CI không cài gì."""
    khoi = []
    for dong in fm.splitlines():
        mk = _KHOA_RE.match(dong)
        if mk:
            khoi.append((mk.group(1), [dong]))
        elif khoi:
            khoi[-1][1].append(dong)
        else:
            khoi.append((None, [dong]))
    return khoi


def _gia_tri(dong: list) -> str:
    """Giá trị CHỮ của một khoá frontmatter (một dòng, khối `>`/`|`, hay chữ thường xuống dòng)."""
    dau = dong[0].split(":", 1)[1].strip()
    sau = [x.strip() for x in dong[1:] if x.strip()]
    s = " ".join(sau if dau in ("", ">", "|", ">-", "|-", ">+", "|+") else [dau] + sau)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].replace('\\"', '"').replace("\\\\", "\\") if s[0] == '"' else s[1:-1].replace("''", "'")
    return s.strip()


def _bo_gach(s: str) -> str:
    return _GACH_DAI.sub(" - ", s or "").strip()


def _cat(s: str, tran: int) -> str:
    """Cắt ở ranh giới từ, kèm dấu ba chấm. Vanhanh cắt tên ở 120 và mô tả ở 300 ký tự (`packs_store`)."""
    s = " ".join((s or "").split())
    if len(s) <= tran:
        return s
    return s[:tran - 3].rsplit(" ", 1)[0].rstrip(",;: ") + "..."


def _agent_vanhanh(van_ban: str, ten: str, c: dict, m: dict, vi, rel: str):
    """Tệp agent cho Vanhanh: frontmatter thêm khoá của Vanhanh, THÂN GIỮ NGUYÊN TỪNG BYTE.

    Trả (văn bản, thông tin). `vi` là [tên, mô tả] tiếng Việt từ bảng dịch, hoặc None."""
    mo = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", van_ban, re.S)
    if not mo:
        raise LoiDongBo(f"agent không có frontmatter: {rel}")
    khoi = _khoi_frontmatter(mo.group(1))
    goc = {k: _gia_tri(d) for k, d in khoi if k}
    ten_goc = goc.get("name") or ten
    mo_ta_en = _cat(_bo_gach(goc.get("description")), 300)
    if vi is not None and not (isinstance(vi, list) and len(vi) == 2 and all(isinstance(x, str) and x for x in vi)):
        raise LoiDongBo(f"bảng dịch: mục {rel} phải là [tên, mô tả]")
    ten_vi = _cat(vi[0], 120) if vi else _cat(_bo_gach(ten_goc), 120)
    mo_ta_vi = _cat(vi[1], 300) if vi else mo_ta_en
    the = [m["nhan"]["vi"]] + ([c["the"]] if c.get("the") else [])
    dau = ["---", "type: agent", f"slug: {ten}", f"name: {_q(ten_vi)}", f"role: {_q(mo_ta_vi)}", "tags:"]
    dau += [f"- {_q(x)}" for x in the]
    dau += [f"group: {_q(m['nhan']['vi'])}", f"ten_goc: {_q(ten_goc)}", f"nguon: {_q(c['repo'] + '/' + rel)}"]
    for k, d in khoi:
        if k not in KHOA_VANHANH:
            dau += d
    van_ban_moi = "\n".join(dau + ["---"]) + "\n" + van_ban[mo.end():]
    return van_ban_moi, {"ten_vi": ten_vi, "ten_en": _cat(_bo_gach(ten_goc), 120),
                         "mo_ta_vi": mo_ta_vi, "mo_ta_en": mo_ta_en or mo_ta_vi}


def _doc_dich(pid: str) -> dict:
    """Bảng dịch `theo-goc/dich/<id>.json`: {tên tệp gốc: [tên, mô tả]}. Không có thì rỗng."""
    p = CAU_HINH / "dich" / f"{pid}.json"
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise LoiDongBo(f"{p.name}: bảng dịch phải là map")
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _nguon_md(c: dict, tu_dau: dict, tt: dict = None) -> str:
    """Trang nguồn của gói. Không ghi commit hay ngày: tệp này nằm trong phần so sánh, ghi thứ đổi
    mỗi lần chạy thì ngày nào gói cũng lên bản mới dù repo gốc không đổi gì."""
    url = "https://github.com/" + c["repo"]
    if any(v.get("den") == "agents" for v in (tt or {}).values()):
        dong = [f"# Nguồn của gói theo repo gốc `{c['repo']}`", "",
                f"Agent trong gói này lấy từ [{c['repo']}]({url}), nhánh `{c['ref']}`. Thân prompt",
                "chép **nguyên văn**: không dịch, không rút gọn. Phần đầu mỗi tệp thêm vài khoá để Vanhanh",
                "đọc được (`type`, `slug`, `name` và `role` tiếng Việt, `tags`, `group`); tên gốc nằm ở",
                "`ten_goc`, các khoá gốc khác giữ nguyên.", "",
                "Mỗi ngày kho so lại với repo gốc (`tools/theo-goc.py`). Repo gốc đổi thì gói lên một bản",
                "vá, Vanhanh báo trong chuông và bạn bấm Cập nhật. Agent bạn đã tự sửa thì Vanhanh giữ lại,",
                "không ghi đè. Commit gốc của bản đang phát hành nằm ở trường `upstream.commit` trong",
                "`index.json`.", "",
                f"Giấy phép gốc: **{c['goi']['license']}**, nguyên văn ở `docs/LICENSE-goc*` nếu repo có.", "",
                "| Agent | Tệp gốc |", "|---|---|"]
        for s, tu in tu_dau.items():
            dong.append(f"| `{s}` | `{tu}` |")
        return "\n".join(dong) + "\n"
    dong = [f"# Nguồn của gói theo repo gốc `{c['repo']}`", "",
            f"Skill trong gói này chép **nguyên văn** từ [{c['repo']}]({url}), nhánh `{c['ref']}`:",
            "không dịch, không rút gọn, không sửa frontmatter.", "",
            "Mỗi ngày kho so lại với repo gốc (`tools/theo-goc.py`). Repo gốc đổi thì gói lên một bản",
            "vá, Vanhanh báo trong chuông và bạn bấm Cập nhật. Skill bạn đã tự sửa thì Vanhanh giữ lại,",
            "không ghi đè. Commit gốc của bản đang phát hành nằm ở trường `upstream.commit` trong",
            "`index.json`.", "",
            f"Giấy phép gốc: **{c['goi']['license']}**, nguyên văn ở `docs/LICENSE-goc*` nếu repo có.", "",
            "| Skill | Thư mục gốc |", "|---|---|"]
    for s, tu in tu_dau.items():
        dong.append(f"| `{s}` | `{tu}` |")
    return "\n".join(dong) + "\n"


def _cay(goc: Path, phan: list) -> dict:
    """{đường dẫn tương đối: sha256} của những phần gói do repo gốc quản."""
    ra = {}
    for ten in phan:
        p = goc / ten
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file():
                ra[f.relative_to(goc).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    return ra


def _ban_cu(thu_muc: Path) -> str:
    try:
        for dong in (thu_muc / "vanhanh-pack.yaml").read_text(encoding="utf-8").splitlines():
            if dong.startswith("version:"):
                return dong.split(":", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def _tang_ban(v: str) -> str:
    if not v:
        return "1.0.0"
    a, b, c = (v.split(".") + ["0", "0", "0"])[:3]
    return f"{int(a)}.{int(b)}.{int(c) + 1}"


def _q(s: str) -> str:
    return json.dumps(str(s), ensure_ascii=False)


def _theo_loai(ten: list, tt: dict) -> dict:
    """{"skills": [...], "agents": [...]} theo thứ tự chép, bỏ loại rỗng. Thiếu `tt` thì coi là skill."""
    ra = {}
    for t in ten:
        ra.setdefault((tt or {}).get(t, {}).get("den", "skills"), []).append(t)
    return ra


def viet_manifest(pid: str, c: dict, ban: str, skills: list, tt: dict = None) -> str:
    g = c["goi"]
    loai = _theo_loai(skills, tt)
    if set(loai) != {"skills"}:
        return "\n".join([
            "format: vanhanh-pack", "spec: 1", f"id: {pid}", f"version: {ban}",
            f"name: {{vi: {_q(g['name']['vi'])}, en: {_q(g['name']['en'])}}}",
            f"description: {{vi: {_q(g['description']['vi'])},",
            f"              en: {_q(g['description']['en'])}}}",
            f"author: {{name: {_q(g['author'])}, url: {_q('https://github.com/' + c['repo'])}}}",
            f"license: {g['license']}",
            f"homepage: {_q('https://github.com/' + c['repo'])}",
            f"compat: {{app: {_q(g.get('compat') or '>=1.0.0')}}}",
            "# Gói theo repo gốc: thư mục " + ", ".join(f"{k}/" for k in loai)
            + " do tools/theo-goc.py dựng từ repo gốc, đừng sửa tay.",
            f"upstream: {{repo: {_q(c['repo'])}, ref: {_q(c['ref'])}}}",
            "provides:",
        ] + [f"  {k}: [{', '.join(v)}]" for k, v in loai.items()] + [""])
    return "\n".join([
        "format: vanhanh-pack",
        "spec: 1",
        f"id: {pid}",
        f"version: {ban}",
        f"name: {{vi: {_q(g['name']['vi'])}, en: {_q(g['name']['en'])}}}",
        f"description: {{vi: {_q(g['description']['vi'])},",
        f"              en: {_q(g['description']['en'])}}}",
        f"author: {{name: {_q(g['author'])}, url: {_q('https://github.com/' + c['repo'])}}}",
        f"license: {g['license']}",
        f"homepage: {_q('https://github.com/' + c['repo'])}",
        f"compat: {{app: {_q(g.get('compat') or '>=1.0.0')}}}",
        "# Gói theo repo gốc: thư mục skills/ do tools/theo-goc.py chép nguyên văn, đừng sửa tay.",
        f"upstream: {{repo: {_q(c['repo'])}, ref: {_q(c['ref'])}}}",
        "provides:",
        f"  skills: [{', '.join(skills)}]",
        "",
    ])


def _tier(thu_muc: Path) -> str:
    """Cùng luật với `packs._tier` bên Vanhanh: có tệp .py là bậc code."""
    return "code" if any(thu_muc.rglob("*.py")) else "data"


def _dong_goi(pid: str) -> Path:
    spec = importlib.util.spec_from_file_location("dong_goi", GOC / "tools" / "dong-goi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC, mod.NGUON, mod.RA = GOI.parent, GOI, DIST
    return mod.dong(pid)


def ghi_index(pid: str, c: dict, ban: str, skills: list, commit: str, zip_: Path, hom_nay: str,
              tt: dict = None) -> None:
    d = json.loads(INDEX.read_text(encoding="utf-8"))
    g = c["goi"]
    b = zip_.read_bytes()
    loai = _theo_loai(skills, tt)
    muc = {
        "id": pid,
        "kind": "agent" if set(loai) == {"agents"} else "skill",
        "name": g["name"],
        "description": g["description"],
        "version": ban,
        "author": {"name": g["author"], "url": "https://github.com/" + c["repo"]},
        "category": g["category"],
        "category_label": g["category_label"],
        "tier": _tier(GOI / pid),
        "verified": True,
        "updated": hom_nay,
        "homepage": f"https://github.com/lequydailb-dotcom/vanhanh-store/tree/main/packs/{pid}",
        "source": "https://github.com/" + c["repo"],
        "license": g["license"],
        "upstream": {"repo": c["repo"], "ref": c["ref"], "commit": commit, "synced": hom_nay},
        "provides": loai,
        "download": {"url": f"dist/{zip_.name}", "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)},
    }
    if g.get("icon"):
        muc["icon"] = g["icon"]
    goi = d["packs"]
    for i, x in enumerate(goi):
        if x.get("id") == pid:
            goi[i] = muc
            break
    else:
        goi.append(muc)
    d["updated"] = hom_nay
    INDEX.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dong_bo(pid: str, chi_kiem: bool = False, hom_nay: str = "", bo_qua_ma: bool = False) -> dict:
    """Đồng bộ một gói. Trả {id, doi, can_duyet, ban, commit, tep_ma, ghi}.

    `bo_qua_ma`: gói có tệp mã đổi thì chỉ báo, không ghi. CI dùng nó để đẩy thẳng bản chỉ đổi chữ
    của các gói khác, còn gói cần duyệt đi riêng một Pull Request."""
    hom_nay = hom_nay or datetime.date.today().isoformat()
    c = doc_cau_hinh(pid)
    thu_muc = GOI / pid
    phan = sorted({m["den"] for m in c["chep"]} | {"docs"})
    with tempfile.TemporaryDirectory(prefix="theo-goc-") as tmp:
        tmp = Path(tmp)
        commit = tai_goc(c, tmp / "goc")
        tt = {}
        skills = dung_ban_moi(c, tmp / "goc", tmp / "moi", tt, _doc_dich(pid))
        cu, moi = _cay(thu_muc, phan), _cay(tmp / "moi", phan)
        if cu == moi and (thu_muc / "vanhanh-pack.yaml").is_file():
            # Gói gộp đứng yên nhưng gói lẻ vẫn soát: lần đầu bật `tach`, hay ai đó xoá nhầm một gói lẻ.
            so_tach = _dong_bo_tach(pid, c, tmp / "moi", tt, hom_nay) if c.get("tach") and not chi_kiem else 0
            if not so_tach:
                return {"id": pid, "doi": False, "can_duyet": False, "commit": commit, "ghi": False}
            return {"id": pid, "doi": True, "can_duyet": False, "ban": _ban_cu(thu_muc), "commit": commit,
                    "tep_ma": [], "so_tep_doi": 0, "so_tach": so_tach, "ghi": True}
        doi = {k for k in set(cu) | set(moi) if cu.get(k) != moi.get(k)}
        tep_ma = sorted(k for k in doi if not k.lower().endswith(DUOI_CHU) and not k.startswith("docs/")
                        and Path(k).stem.upper() not in TEN_CHU)
        ban = _tang_ban(_ban_cu(thu_muc))
        kq = {"id": pid, "doi": True, "can_duyet": bool(tep_ma), "ban": ban, "commit": commit,
              "tep_ma": tep_ma, "so_tep_doi": len(doi)}
        if chi_kiem or (bo_qua_ma and kq["can_duyet"]):
            return dict(kq, ghi=False)
        thu_muc.mkdir(parents=True, exist_ok=True)
        for ten in phan:
            shutil.rmtree(thu_muc / ten, ignore_errors=True)
            if (tmp / "moi" / ten).is_dir():
                shutil.copytree(tmp / "moi" / ten, thu_muc / ten)
        (thu_muc / "vanhanh-pack.yaml").write_text(viet_manifest(pid, c, ban, skills, tt), encoding="utf-8")
        zip_ = _dong_goi(pid)
        ghi_index(pid, c, ban, skills, commit, zip_, hom_nay, tt)
        if c.get("tach"):
            kq["so_tach"] = _dong_bo_tach(pid, c, tmp / "moi", tt, hom_nay)
    return dict(kq, ghi=True)


def _id_tach(c: dict, ten: str) -> str:
    return c["tach"] + ten[len(c.get("tien_to") or ""):]


def _manifest_tach(cid: str, pid: str, c: dict, ten: str, info: dict, ban: str) -> str:
    g = c["goi"]
    return "\n".join([
        "format: vanhanh-pack", "spec: 1", f"id: {cid}", f"version: {ban}",
        f"name: {{vi: {_q(info['ten_vi'])}, en: {_q(info['ten_en'])}}}",
        f"description: {{vi: {_q(info['mo_ta_vi'])},",
        f"              en: {_q(info['mo_ta_en'])}}}",
        f"author: {{name: {_q(g['author'])}, url: {_q('https://github.com/' + c['repo'])}}}",
        f"license: {g['license']}",
        f"homepage: {_q(_url_tep(c, info['tu']))}",
        f"compat: {{app: {_q(g.get('compat') or '>=1.0.0')}}}",
        f"# Một agent lẻ của gói theo repo gốc {pid}: tools/theo-goc.py dựng lại mỗi ngày, đừng sửa tay.",
        f"thuoc_goi: {pid}",
        "provides:",
        f"  agents: [{ten}]",
        "",
    ])


def _url_tep(c: dict, rel: str) -> str:
    return f"https://github.com/{c['repo']}/blob/{c['ref']}/{rel}"


def _dong_bo_tach(pid: str, c: dict, moi: Path, tt: dict, hom_nay: str) -> int:
    """Mỗi agent của gói gộp thành một gói lẻ `<tach><tên>`. Trả số gói lẻ thêm, đổi hay bỏ.

    Gói lẻ chứa đúng tệp agent của gói gộp (cùng byte), giấy phép gốc và một trang nguồn ngắn. Nó lên
    bản vá khi tệp agent của nó đổi; repo gốc bỏ agent thì gói lẻ rời danh mục và thư mục bị xoá
    (tệp zip cũ giữ lại, như mọi bản cũ khác trong `dist/`). Danh mục ghi MỘT lần cho cả lượt."""
    d = json.loads(INDEX.read_text(encoding="utf-8"))
    cu_muc = {x["id"]: x for x in d["packs"] if x.get("thuoc_goi") == pid}
    muc_moi, so = {}, 0
    for ten, info in tt.items():
        if info.get("den") != "agents":
            continue
        cid = _id_tach(c, ten)
        if not _ID_RE.match(cid):
            raise LoiDongBo(f"id gói lẻ lạ: {cid!r}")
        tm = GOI / cid
        with tempfile.TemporaryDirectory(prefix="theo-goc-tach-") as t:
            t = Path(t)
            (t / "agents").mkdir()
            shutil.copyfile(moi / "agents" / f"{ten}.md", t / "agents" / f"{ten}.md")
            (t / "docs").mkdir()
            for lic in sorted((moi / "docs").glob("LICENSE-goc*")):
                shutil.copyfile(lic, t / "docs" / lic.name)
            (t / "docs" / "NGUON.md").write_text(
                f"# Nguồn của agent `{ten}`\n\n"
                f"Một agent lẻ của gói `{pid}`, lấy từ [{c['repo']}/{info['tu']}]({_url_tep(c, info['tu'])}).\n"
                "Thân prompt chép nguyên văn, phần đầu tệp thêm khoá cho Vanhanh (xem `docs/NGUON.md` của gói gộp).\n"
                "Repo gốc đổi agent này thì gói lên một bản vá, Vanhanh báo trong chuông.\n\n"
                f"Giấy phép gốc: **{c['goi']['license']}**, nguyên văn ở `docs/LICENSE-goc*`.\n", encoding="utf-8")
            ban_cu = _ban_cu(tm)
            giong = (bool(ban_cu) and cid in cu_muc and _cay(tm, ["agents", "docs"]) == _cay(t, ["agents", "docs"])
                     and (tm / "vanhanh-pack.yaml").read_text(encoding="utf-8")
                     == _manifest_tach(cid, pid, c, ten, info, ban_cu))
            if giong:
                muc_moi[cid] = cu_muc[cid]
                continue
            ban = _tang_ban(ban_cu)
            tm.mkdir(parents=True, exist_ok=True)
            for p in ("agents", "docs"):
                shutil.rmtree(tm / p, ignore_errors=True)
                shutil.copytree(t / p, tm / p)
        (tm / "vanhanh-pack.yaml").write_text(_manifest_tach(cid, pid, c, ten, info, ban), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            zip_ = _dong_goi(cid)
        b = zip_.read_bytes()
        g = c["goi"]
        muc_moi[cid] = {
            "id": cid,
            "kind": "agent",
            "name": {"vi": info["ten_vi"], "en": info["ten_en"]},
            "description": {"vi": info["mo_ta_vi"], "en": info["mo_ta_en"]},
            "version": ban,
            "author": {"name": g["author"], "url": "https://github.com/" + c["repo"]},
            "category": info["category"],
            "category_label": c["nhom_kho"][info["category"]],
            "tier": "data",
            "verified": True,
            "updated": hom_nay,
            "homepage": f"https://github.com/lequydailb-dotcom/vanhanh-store/tree/main/packs/{cid}",
            "source": _url_tep(c, info["tu"]),
            "license": g["license"],
            "thuoc_goi": pid,
            "provides": {"agents": [ten]},
            "download": {"url": f"dist/{zip_.name}", "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)},
        }
        so += 1
    for cid in cu_muc:
        if cid not in muc_moi:
            shutil.rmtree(GOI / cid, ignore_errors=True)
            so += 1
    goi = [x for x in d["packs"] if x.get("thuoc_goi") != pid]
    i = next((k for k, x in enumerate(goi) if x.get("id") == pid), len(goi) - 1)
    goi[i + 1:i + 1] = [muc_moi[k] for k in sorted(muc_moi)]
    if so:
        d["packs"], d["updated"] = goi, hom_nay
        INDEX.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return so


def main(argv: list) -> int:
    chi_kiem, bo_qua_ma = "--kiem" in argv, "--khong-ma" in argv
    ids = [a for a in argv if not a.startswith("--")] or sorted(p.stem for p in CAU_HINH.glob("*.json"))
    ket_qua, loi = [], []
    for pid in ids:
        try:
            kq = dong_bo(pid, chi_kiem, bo_qua_ma=bo_qua_ma)
        except (LoiDongBo, OSError, ValueError, subprocess.TimeoutExpired) as e:
            loi.append(f"{pid}: {e}")
            print(f"LỖI {pid}: {e}")
            continue
        ket_qua.append(kq)
        if not kq["doi"]:
            print(f"{pid}: giống repo gốc ({kq['commit'][:7]})")
        else:
            print(f"{pid}: bản mới {kq['ban']} từ {kq['commit'][:7]}, {kq['so_tep_doi']} tệp đổi"
                  + (f", có tệp mã cần duyệt: {', '.join(kq['tep_ma'][:10])}" if kq["can_duyet"] else "")
                  + (f", {kq['so_tach']} gói lẻ thêm/đổi/bỏ" if kq.get("so_tach") else "")
                  + ("" if kq["ghi"] else ", CHƯA ghi"))
    da_ghi = [k for k in ket_qua if k["ghi"]]
    cho = [k["id"] for k in ket_qua if k["doi"] and not k["ghi"]]
    out = os.environ.get("GITHUB_OUTPUT")
    if out and not chi_kiem:
        tom_tat = "; ".join(f"{k['id']} {k['ban']} ({k['commit'][:7]})" for k in da_ghi)
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"doi={'1' if da_ghi else '0'}\n")
            f.write(f"can_duyet={'1' if any(k['can_duyet'] for k in da_ghi) else '0'}\n")
            f.write(f"cho_duyet={' '.join(cho)}\n")
            f.write(f"tom_tat={tom_tat}\n")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
