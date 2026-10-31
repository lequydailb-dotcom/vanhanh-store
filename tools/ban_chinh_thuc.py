"""Luật "MCP của bên thứ 3 đi theo bản chính thức".

Connector chạy một MCP của bên thứ 3 qua `npx` hoặc `uvx` phải:

- lấy MCP từ KÊNH PHÁT HÀNH chính thức (npm, PyPI), không phải từ GitHub hay một đường dẫn: code
  trên nhánh `main` là code chưa phát hành, chưa ai gắn số cho nó;
- và đi theo BẢN MỚI NHẤT của kênh đó, tức tên gói kết thúc bằng `@latest`.

Vì sao phải ghi rõ `@latest` mà không để trống phiên bản: cả `npx -y ten-goi` lẫn `uvx ten-goi`
đều dùng lại bản đã có trong bộ nhớ đệm của máy. Để trống thì máy nào tải lần đầu ở bản nào là kẹt
ở bản đó mãi, trong khi máy cài sau lại chạy bản khác. `@latest` bắt chúng hỏi kênh phát hành mỗi
lần khởi động, nên mọi máy chạy cùng một bản.

Ngoại lệ có tên: khuôn khai `ngoai_le_ban_chinh_thuc` là một câu nói rõ VÌ SAO (bên thứ 3 chưa có
bản phát hành nào, hay code của Naota đọc thẳng định dạng của một bản cụ thể). Naota không đọc
trường này; nó để quyết định ấy nằm trong dữ liệu cho người review đọc được.

Không chạm mạng. Đây chỉ soi lệnh; `soi-ban-moi.py` mới là chỗ chạy thử bản mới nhất thật.
"""

LENH = ("npx", "uvx")

# Tuỳ chọn có đi kèm một giá trị, để không nhầm giá trị đó là tên gói.
_CO_GIA_TRI = {
    "npx": {"-p", "--package", "--registry", "--cache", "--userconfig"},
    "uvx": {"--with", "--with-requirements", "--with-editable", "--python", "-p", "--index",
            "--index-url", "--extra-index-url", "--default-index", "--constraints", "-c",
            "--overrides", "--cache-dir"},
}


def goi_tu_lenh(command, args):
    """Tên gói (kèm phiên bản nếu có) mà lệnh sẽ tải. "" nếu không phải npx/uvx hay không tìm ra."""
    cmd = str(command or "").strip().lower()
    if cmd not in LENH:
        return ""
    args = [str(a) for a in (args or [])]
    i = 0
    while i < len(args):
        a = args[i]
        # Dạng gộp `--from=x`, `--package=x`
        if "=" in a and a.startswith("--"):
            k, v = a.split("=", 1)
            if (cmd == "uvx" and k == "--from") or (cmd == "npx" and k == "--package"):
                return v
            i += 1
            continue
        if (cmd == "uvx" and a == "--from") or (cmd == "npx" and a in ("-p", "--package")):
            return args[i + 1] if i + 1 < len(args) else ""
        if a in _CO_GIA_TRI[cmd]:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return ""


def loi_ban(con):
    """Danh sách lỗi của một khuôn connector theo luật trên. Rỗng = đạt."""
    cmd = str((con or {}).get("command") or "").strip().lower()
    if cmd not in LENH:
        return []
    if str(con.get("ngoai_le_ban_chinh_thuc") or "").strip():
        return []
    goi = goi_tu_lenh(cmd, con.get("args"))
    if not goi:
        return [f"không tìm ra tên gói trong lệnh {cmd}"]
    thap = goi.lower()
    if thap.startswith(("git+", "http:", "https:", "file:", ".", "/")) or "github.com" in thap:
        return [f"'{goi}' lấy code thẳng từ GitHub hoặc đường dẫn, chưa phải bản phát hành. "
                f"Dùng gói chính thức trên npm/PyPI kèm @latest; bên thứ 3 chưa phát hành bản nào "
                f"thì khai `ngoai_le_ban_chinh_thuc` nói rõ vì sao"]
    if not thap.endswith("@latest"):
        return [f"'{goi}' không đi theo bản mới nhất: viết '{ten_goc(goi)}@latest'. "
                f"Cần ghim một bản cụ thể thì khai `ngoai_le_ban_chinh_thuc` nói rõ vì sao"]
    return []


def ten_goc(goi):
    """Tên gói bỏ phần phiên bản: `@scope/x@1.2` -> `@scope/x`, `x==1.2` -> `x`, `x[mcp]@1` -> `x[mcp]`."""
    g = str(goi or "")
    for sep in ("==", ">=", "<=", "~=", "<", ">"):
        g = g.split(sep, 1)[0]
    dau = "@" if g.startswith("@") else ""
    return dau + g[len(dau):].split("@", 1)[0]
