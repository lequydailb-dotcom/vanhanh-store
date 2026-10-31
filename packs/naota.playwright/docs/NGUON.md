# Nguồn của gói `naota.playwright`

Gói này **không mang theo mã của Playwright**. Nó chỉ là một tờ khai connector trỏ Naota chạy MCP server chính chủ của Microsoft:

```
npx -y @playwright/mcp@latest
```

- Mã nguồn: <https://github.com/microsoft/playwright-mcp> (Apache-2.0)
- Gói npm: <https://www.npmjs.com/package/@playwright/mcp>
- Playwright: <https://github.com/microsoft/playwright> (Apache-2.0)

Vì mã tải thẳng từ npm lúc chạy, gói này không chép lại tệp nào của Microsoft và không ghim phiên bản: `@latest` lấy bản mới nhất mỗi lần khởi động.

## Phân loại quyền cho 71 tool

`mcp_catalog.classify` xét `read` trước, rồi `danger`, rồi `write`, và thứ **không khớp gì thì rơi về `read`**. Nên cả 71 tool đều được kể tên trong `tool_meta`, bỏ sót một cái là nó chạy được ở mức Chỉ đọc mà không ai thấy.

| Mức | Gồm gì |
|---|---|
| `read` | Đọc cấu trúc trang, tìm phần tử, đọc console và danh sách request, các lệnh `verify_*`, tô sáng phần tử. |
| `write` | Mở trang, đổi cỡ cửa sổ, quản lý tab, chụp màn hình, xuất PDF, quay video và trace. Đổi trạng thái trình duyệt hoặc ghi tệp, không đụng tới trang của người khác. |
| `danger` | Bấm, gõ, điền form, kéo thả, chuột toạ độ, xử lý hộp thoại: đây là chỗ đặt hàng và xoá dữ liệu thật xảy ra. Cộng thêm `browser_evaluate` và `browser_run_code_unsafe` (chạy mã tuỳ ý), `browser_file_upload` (đẩy tệp trên máy lên web), `browser_route`/`browser_network_request` (chặn và tự phát request), và toàn bộ cookie/localStorage/sessionStorage. |

Cookie và storage bị xếp `danger` **kể cả lệnh chỉ đọc**: chúng là phiên đăng nhập, đọc ra được là mạo danh được. Trong ba mức của Naota thì đó là hậu quả ngang một lệnh phá huỷ, nên nó không thuộc mức đọc.

## Mặc định an toàn

Bốn ô cấu hình điền sẵn `isolated=true` và `headless=true`. `isolated` là quan trọng nhất: mặc định GỐC của Playwright MCP là hồ sơ lưu trên đĩa, tức nó thấy mọi trang bạn đang đăng nhập. Gói này lật ngược mặc định đó.
