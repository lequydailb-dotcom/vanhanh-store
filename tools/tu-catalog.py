"""Sinh gói connector từ `system/mcp-catalog.json` của NAOTA.

    python tools/tu-catalog.py <đường dẫn tới naota>

Vì sao có script này thay vì chép tay 26 lần: mỗi connector là vài chục dòng khai báo, chép tay
thì sai một chỗ không ai thấy, và mỗi lần Naota sửa một connector lại phải chép lại. Chạy lại
lệnh này là gói khớp catalog, không phải đi dò từng trường.

Bốn chỗ script phải xử lý, và mỗi chỗ đều là một luật thật của `server/packs.py`:

  ICON. Catalog trỏ `/static/logos/x.png` - đường dẫn TUYỆT ĐỐI của dashboard. Gói bị từ chối
  nếu icon bắt đầu bằng `/`, nên logo phải được CHÉP VÀO gói và trỏ lại `assets/x.png`.

  SVG. Endpoint phục vụ ảnh của gói cố ý KHÔNG trả `.svg` (mở thẳng một tab là chạy script bên
  trong). Ba logo `.svg` rơi về một icon Lucide - xấu hơn logo thật nhưng hiện được. Từ bản
  1.0.1 các gói này đã mang bản PNG dựng sẵn trong `assets/`; script XOÁ SẠCH thư mục gói rồi
  sinh lại, nên chạy lại là mất logo (và mất mọi sửa tay khác). Chỉ chạy khi thật sự di trú lại.

  KHÔNG ĐÓNG GÓI ĐƯỢC. `transport: internal` là allowlist bảo vệ `importlib.import_module`, và
  `auth.type: qr` là đường riêng của Zalo với ba endpoint cùng một nhánh JS. Cả hai KHÔNG khai
  bằng dữ liệu được, nên chúng ở lại trong app.

  QUYỀN. Connector từ gói luôn bắt đầu ở mức chỉ đọc, bất kể catalog khai gì. Script không cố
  lách chuyện đó - nó là luật cố ý của `packs.py`, và người dùng tự nâng quyền từng tài khoản.

Tệp connector ghi ra JSON chứ không phải YAML (`packs._doc_file` đọc cả hai, theo đuôi tệp).
Bản đầu tự viết một bộ ghi YAML và nó hỏng ngay ở cấu trúc lồng: `requires: {node: ">=18"}` ra
thành `requires:   node: ">=18"` trên MỘT dòng, tức YAML sai cú pháp. 18 trên 26 gói vỡ, và chỉ
lộ ra khi đem từng gói cho `packs.py` nạp thử. Catalog đầy `tool_meta`, `inject_args`, `env`,
`requires` lồng nhau nên đó là ca thường chứ không phải ca hiếm. `json.dumps` thì không có chỗ
nào để sai.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
NGUON = GOC / "packs"

# Ba thứ này KHÔNG khai bằng dữ liệu được - xem docstring.
BO_QUA = {
    "zalo": "đăng nhập bằng QR, có đường riêng trong app",
    "botcake": "transport internal, gọi thẳng module của server",
    "substack": "transport internal, gọi thẳng module của server",
}

# Logo .svg không phục vụ được qua đường asset của gói -> icon Lucide thay thế.
THAY_SVG = {"shopify": "shopping-bag", "n8n": "workflow", "hostinger": "server"}

CODE_FIELD = ("command", "args", "env", "cred_dir", "isolate_home", "oauth_file",
              "needs_local_browser")

_DAU = {"àáảãạăằắẳẵặâầấẩẫậ": "a", "èéẻẽẹêềếểễệ": "e", "ìíỉĩị": "i",
        "òóỏõọôồốổỗộơờớởỡợ": "o", "ùúủũụưừứửữự": "u", "ỳýỷỹỵ": "y", "đ": "d"}


def slug(s: str) -> str:
    """'Bán hàng' -> 'ban-hang'. Mã máy để lọc ổn định qua các bản dịch."""
    s = str(s or "").lower()
    for nguon, dich in _DAU.items():
        for c in nguon:
            s = s.replace(c, dich)
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-") or "khac"


def lam_goi(c: dict, logo_dir: Path) -> tuple:
    cid = c["id"]
    pid = "naota." + cid
    thu_muc = NGUON / pid
    if thu_muc.exists():
        shutil.rmtree(thu_muc)
    (thu_muc / "connectors").mkdir(parents=True)

    # Bỏ khoá bắt đầu bằng `_`: chúng là ghi chú cho người đọc catalog, không phải cấu hình.
    con = {k: v for k, v in c.items() if not k.startswith("_")}
    icon = str(con.get("icon") or "")
    if icon.startswith("/static/logos/"):
        ten = icon.rsplit("/", 1)[-1]
        if ten.lower().endswith(".svg"):
            con["icon"] = THAY_SVG.get(cid, "plug")
        else:
            (thu_muc / "assets").mkdir(exist_ok=True)
            shutil.copy2(logo_dir / ten, thu_muc / "assets" / ten)
            con["icon"] = "assets/" + ten

    (thu_muc / "connectors" / (cid + ".json")).write_text(
        json.dumps(con, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    ten_hien = con.get("name", cid)
    mo_ta = con.get("description", "")
    nhom = con.get("category", "Khác")
    j = lambda v: json.dumps(v, ensure_ascii=False)   # noqa: E731
    (thu_muc / "naota-pack.yaml").write_text(
        "format: naota-pack\n"
        "spec: 1\n"
        "id: " + pid + "\n"
        "version: 1.0.0\n"
        "name: {vi: " + j(ten_hien) + "}\n"
        "description: {vi: " + j(mo_ta) + "}\n"
        "author: {name: Naota}\n"
        "license: MIT\n"
        'homepage: "https://github.com/vuongtex/naota-store"\n'
        # 1.0.0 là bản đầu đọc đúng phiên bản của CHÍNH NÓ; bản trước đó từ chối MỌI gói có
        # khai `compat`, kèm câu "bản này là " bỏ trống.
        'compat: {app: ">=1.0.0"}\n'
        "provides:\n"
        "  connectors: [connectors/" + cid + ".json]\n",
        encoding="utf-8", newline="\n")

    code = str(con.get("transport") or "http").lower() == "stdio" \
        or any(k in con for k in CODE_FIELD)
    return pid, {
        "id": pid, "kind": "connector",
        "name": {"vi": ten_hien},
        "description": {"vi": mo_ta},
        "version": "1.0.0",
        "author": {"name": "Naota"},
        "category": slug(nhom), "category_label": {"vi": nhom},
        "tier": "code" if code else "data",
        "verified": True, "updated": "2026-09-05",
        "homepage": "https://github.com/vuongtex/naota-store/tree/main/packs/" + pid,
        # Id connector gói này cấp. Kho dùng nó để KHÔNG hiện hai thẻ cho cùng một dịch vụ khi
        # app vẫn còn bản của mình - và để biết thẻ nào trở nên cài được sau khi app bỏ nó đi.
        "provides": {"connectors": [cid]},
        "download": {"url": "", "sha256": "", "size": 0},
    }


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Cách dùng: python tools/tu-catalog.py <đường dẫn naota>")
    repo = Path(sys.argv[1])
    cat = json.loads((repo / "system" / "mcp-catalog.json").read_text(encoding="utf-8"))
    logo_dir = repo / "dashboard" / "logos"

    from importlib import util as _u
    spec = _u.spec_from_file_location("dong_goi", Path(__file__).resolve().parent / "dong-goi.py")
    dg = _u.module_from_spec(spec)
    spec.loader.exec_module(dg)

    muc, bo = [], []
    for c in cat.get("connectors", []):
        cid = c.get("id")
        if not cid:
            continue
        if cid in BO_QUA:
            bo.append((cid, BO_QUA[cid]))
            continue
        pid, m = lam_goi(c, logo_dir)
        z = dg.dong(pid)
        b = z.read_bytes()
        m["download"] = {"url": "dist/" + z.name, "sha256": hashlib.sha256(b).hexdigest(),
                         "size": len(b)}
        muc.append(m)

    idx = json.loads((GOC / "index.json").read_text(encoding="utf-8"))
    # Giữ nguyên mục KHÔNG phải connector sinh từ catalog; thay sạch phần connector để chạy lại
    # lệnh này không đẻ ra bản trùng.
    giu = [g for g in idx.get("packs", [])
           if g.get("kind") != "connector" or not str(g.get("id", "")).startswith("naota.")]
    idx["packs"] = giu + muc
    idx["updated"] = "2026-09-05"
    (GOC / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")

    print("\nĐã sinh " + str(len(muc)) + " gói connector.")
    for cid, ly in bo:
        print("  BỎ QUA " + cid + ": " + ly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
