---
name: Deploy lên Cloudflare
description: Dựng và deploy Worker hoặc web tĩnh lên Cloudflare bằng Wrangler: tạo cấu hình, chạy thử, deploy thật, trả link chạy được.
description_en: "Build and deploy a Worker or static site to Cloudflare with Wrangler: config, dry run, real deploy, live link."
group: Lập trình
---

# Deploy lên Cloudflare

## Khi nào dùng

Người dùng muốn đưa một thứ lên mạng bằng Cloudflare: "deploy trang này lên Cloudflare", "đưa
landing page lên", "làm cho anh một Worker nhận webhook", "cập nhật Worker api-don-hang",
"up thư mục web này lên Pages".

Không dùng cho việc quản lý tài khoản (DNS, tường lửa, SSL, cache, xem lưu lượng, xoá Worker,
đặt biến bí mật): những việc đó đi qua công cụ `execute` của kết nối Cloudflare (MCP).

## Ba công cụ

- `cf_deploy_check`: kiểm tra Node, kết nối, token. Luôn gọi đầu tiên ở lần deploy đầu.
- `cf_worker_deploy`: deploy dự án có `wrangler.jsonc`. `dry_run=true` để đóng gói thử.
- `cf_pages_deploy`: đưa một thư mục web tĩnh đã dựng sẵn lên Pages.

Cả ba dùng token của kết nối Cloudflare. Deploy thật cần kết nối đó ở mức **Toàn quyền**. Nếu
công cụ báo chưa đủ quyền, nói đúng như vậy và chỉ người dùng vào trang Kết nối nâng quyền.
Không tìm đường khác để deploy.

## Chọn đường nào

- **Trang tĩnh mới** (HTML, CSS, ảnh): ưu tiên Worker với static assets (`cf_worker_deploy`).
  Cloudflare đang dồn tính năng mới vào đường này.
- **Đã có dự án Pages**, hoặc người dùng nói rõ "Pages": `cf_pages_deploy`.
- **Có xử lý phía máy chủ** (API, webhook, form gửi về, chuyển hướng): Worker.

## Quy trình

1. Hỏi lại nếu thiếu **tên** dự án (chữ thường, số, gạch nối, vd `trang-nuoc-mam`). Tên này
   thành địa chỉ `<ten>.<tai-khoan>.workers.dev`, đổi về sau là ra địa chỉ mới.
2. Đặt dự án trong bộ não, mặc định `projects/<ten>/`. Công cụ từ chối thư mục ngoài bộ não
   và ngoài thư mục làm việc đã khai ở trang Coding.
3. Viết `wrangler.jsonc` theo mẫu bên dưới.
4. Gọi `cf_deploy_check` với `path`. Đọc kết quả: thiếu Node, sai token hay nhiều tài khoản
   đều hiện ở đây.
5. Gọi `cf_worker_deploy` với `dry_run=true`. Lỗi cú pháp, thiếu tệp hiện ra ở bước này mà chưa
   đụng tới bản đang chạy.
6. Deploy thật. Bản mới **thay ngay** bản đang chạy, nên với dự án đã có người dùng thật thì
   nói rõ sẽ đè lên trước khi gọi.
7. Trả về đường link trong `urls` của kết quả, kèm một câu nói đã đưa lên cái gì.

## Mẫu cấu hình

Web tĩnh (thư mục `public/` chứa `index.html`):

```jsonc
{
  "name": "trang-nuoc-mam",
  "compatibility_date": "2026-09-01",
  "assets": { "directory": "./public" }
}
```

Worker có code (`src/index.js`):

```jsonc
{
  "name": "nhan-webhook",
  "main": "src/index.js",
  "compatibility_date": "2026-09-01"
}
```

```js
export default {
  async fetch(request, env) {
    return new Response("Xin chào từ Cloudflare");
  },
};
```

Dùng D1, KV, R2 thì thêm khối `d1_databases`, `kv_namespaces`, `r2_buckets` vào cấu hình. Tạo
cơ sở dữ liệu hay bucket trước bằng MCP Cloudflare rồi chép `id` vào.

## Lỗi hay gặp

- **"More than one account"**: token thấy nhiều tài khoản. Bảo người dùng điền Account ID vào
  kết nối Cloudflare (ô tuỳ chọn), hoặc thêm `"account_id"` vào `wrangler.jsonc`.
- **Lỗi quyền 10000 / Authentication error**: token thiếu quyền Workers Scripts : Edit (Worker)
  hoặc Cloudflare Pages : Edit (Pages). Tạo lại token có quyền đó.
- **Lần đầu chạy lâu**: máy đang tải Wrangler về, chờ được tới 10 phút trên VPS yếu.
- **Biến bí mật** (khoá API của dịch vụ khác): KHÔNG ghi vào `wrangler.jsonc` hay tệp trong bộ
  não. Đặt qua MCP Cloudflare hoặc bảng điều khiển Cloudflare.
