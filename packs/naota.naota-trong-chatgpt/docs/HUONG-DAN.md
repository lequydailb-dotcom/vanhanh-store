# Gói `naota.naota-trong-chatgpt` - Naota trong ChatGPT

Bạn chat trên **chatgpt.com** bằng gói ChatGPT của mình, và ChatGPT tự gọi công cụ của Naota khi cần: xem doanh thu, đọc brain, tạo nhắc lịch, giao việc, gửi Zalo...

Phần suy nghĩ chạy bằng gói ChatGPT của bạn, **không tốn hạn mức Codex**. Naota chỉ lo phần làm.

> Vì sao là một gói: Naota giữ mọi cuộc chat chung **một nền tảng**, nên tính năng đưa chat sang chatgpt.com không bật sẵn cho mọi người. Ai cần thì cài.

---

## Trong gói có gì

| Loại | Slug | Việc |
|---|---|---|
| Plugin | `naota-trong-chatgpt` | Cửa OAuth và địa chỉ MCP cho ChatGPT, cùng một trang cài đặt riêng |

Gói không thêm tool mới. ChatGPT dùng đúng bộ công cụ Naota đã có (kết nối MCP, brain, nhắc lịch, Kanban, plugin), với mức quyền bạn chọn.

## Cần có gì

- **NAOTA 1.0.0 trở lên.** Bản cũ hơn thì gói bị tắt kèm lý do ngay lúc cài.
- **Gói ChatGPT** Plus, Pro, Business (Team), Enterprise hoặc Edu. Gói miễn phí không có tính năng này.
- **Máy tính.** Bước cài đặt (Developer mode) chỉ làm được trên bản web chatgpt.com, không làm được trong app điện thoại.
- **Naota có địa chỉ https.** ChatGPT không nhận địa chỉ kiểu `http://12.34.56.78:7777`. Gắn tên miền riêng trước (Cài đặt, mục Giọng nói, thương hiệu và truy cập).
- **Naota đã đặt mật khẩu quản trị.** Bước cho phép dựa vào đăng nhập dashboard. Chưa có mật khẩu thì cửa này đóng.

---

## Bước 1: Cài gói và lấy địa chỉ

1. Mở **Naota Store**, tìm **Naota trong ChatGPT**, bấm cài và đồng ý chạy mã.
2. Vào trang **Plugin**, tìm thẻ **Naota trong ChatGPT**, bấm **Mở trang**.
3. Bấm **Chép** để chép địa chỉ. Nó có dạng `https://ten-mien-cua-ban/ext/naota-trong-chatgpt/mcp`.

Nếu trang báo "ChatGPT chỉ nhận địa chỉ https", xem lại phần tên miền ở trên.

## Bước 2: Chỉ khi dùng gói Business (Team)

Quản trị viên của workspace phải cho phép tạo connector riêng. Trên chatgpt.com vào **Workspace settings, Permissions & roles, Connected data**, bật **Create custom MCP connectors**.

Nếu bạn là người tạo workspace thì bạn chính là quản trị viên.

## Bước 3: Bật Developer mode trên ChatGPT

Trên chatgpt.com (máy tính): **Settings, Apps & Connectors, Advanced settings**, bật **Developer mode**.

> Tên các mục có thể hơi khác theo phiên bản ChatGPT. Tìm chữ "Developer mode" trong phần Settings.

## Bước 4: Tạo connector

Vẫn trong **Settings, Apps & Connectors**, bấm **Create** (hoặc **Add**), rồi điền:

| Ô | Điền gì |
|---|---|
| Name | `Naota` |
| Description | `Trợ lý Naota của tôi: số liệu, brain, nhắc việc, Zalo` |
| MCP Server URL | địa chỉ đã chép ở bước 1 |
| Authentication | **OAuth** |

Tích ô xác nhận tin tưởng connector, rồi bấm **Create**.

## Bước 5: Cho phép

ChatGPT mở một trang của Naota.

- Nếu trình duyệt chưa đăng nhập Naota, trang hiện ô đăng nhập ngay tại chỗ (có cả ô mã 2 lớp nếu bạn đã bật).
- Trang tiếp theo nói rõ ChatGPT được làm gì và đang ở mức quyền nào. Bấm **Cho phép**.

Xong. Quay lại ChatGPT là thấy Naota đã kết nối.

## Bước 6: Dùng

Trong khung chat của ChatGPT, bấm dấu **+** (hoặc biểu tượng công cụ), chọn **Developer mode**, rồi bật **Naota**. Thử:

- "Dùng Naota: có những công cụ gì?"
- "Doanh thu tuần này so với tuần trước thế nào?"
- "Nhắc tôi 8 giờ sáng mai gọi nhà cung cấp."

Mỗi lần ChatGPT định làm một việc có tác động thật (gửi tin, tạo đơn...), nó sẽ **hỏi bạn xác nhận** trước khi gọi.

---

## Mức quyền

Chọn trên trang của gói (trang Plugin, nút **Mở trang**). Đổi xong có hiệu lực ngay, không cần kết nối lại.

| Mức | ChatGPT được làm gì |
|---|---|
| **Toàn quyền** (mặc định) | Đọc dữ liệu và làm việc thật: gửi tin, tạo đơn, đăng bài |
| **Tự làm có giới hạn** | Đọc dữ liệu và viết nháp, không làm việc ra bên ngoài |
| **Chỉ đọc và gợi ý** | Chỉ đọc, không ghi file, không làm việc ra bên ngoài |

Naota tự chặn ở phía mình theo mức đã chọn. ChatGPT không tự nâng quyền được.

## Ngắt kết nối

- **Tạm dừng:** tắt plugin **Naota trong ChatGPT** trên trang Plugin. Kết nối cũ giữ nguyên, bật lại là dùng tiếp.
- **Ngắt hẳn:** bấm **Ngắt mọi kết nối** trên trang của gói. Muốn dùng lại thì làm lại từ bước 4.
- **Gỡ gói:** gỡ ở Naota Store. Mọi đường của gói biến mất cùng lúc.

---

## Điều cần biết trước

- **Bạn chat trong ChatGPT, không phải trong Naota.** Cuộc chat nằm ở lịch sử của ChatGPT, không vào trí nhớ hay lịch sử chat của Naota.
- **Việc nền vẫn chạy bằng model của Naota.** Nhắc lịch tự chạy, vòng lặp, bot Telegram không có ai gõ vào ChatGPT, nên chúng vẫn dùng model bạn chọn ở trang Models.
- **Naota làm việc trên brain đang mở gần nhất** (brain của cuộc trò chuyện gần nhất trên dashboard). Kết quả mỗi công cụ có ghi rõ đang ở brain nào.
- **Developer mode là tính năng OpenAI còn gắn nhãn thử nghiệm.** Giao diện và tên mục của nó có thể đổi.

## Khi không chạy

| Bạn thấy | Nguyên nhân | Làm gì |
|---|---|---|
| Không có mục Developer mode | Gói miễn phí, hoặc đang ở app điện thoại | Dùng gói trả phí, mở chatgpt.com trên máy tính |
| Không có nút Create connector (gói Business) | Quản trị viên chưa cho phép | Làm bước 2 |
| ChatGPT báo không kết nối được server | Địa chỉ không phải https, plugin đang tắt, hoặc Naota chưa có mật khẩu | Xem lại "Cần có gì" và bước 1 |
| Thẻ plugin không có nút Mở trang | Naota cũ hơn 1.0.0, hoặc plugin đang tắt | Cập nhật Naota, bật plugin |
| Trang Naota báo "Yêu cầu này đã quá hạn" | Để trang Cho phép mở quá 10 phút | Kết nối lại từ ChatGPT |
| Đang dùng tốt bỗng bắt kết nối lại | 30 ngày không dùng, hoặc đã bấm Ngắt mọi kết nối | Kết nối lại từ ChatGPT |

## An toàn

- Token chỉ lưu dạng băm trong thư mục dữ liệu riêng của gói, không nằm trong brain.
- ChatGPT chỉ được quay về đúng máy của OpenAI (`chatgpt.com`, `*.openai.com`). Kẻ gian tự đăng ký một kết nối trỏ về máy mình sẽ không nhận được mã.
- Token của gói này tách hẳn khỏi token Claude Code và Codex dùng. Ngắt bên này không ảnh hưởng bên kia.
- Refresh token xoay vòng: một token cũ bị dùng lại là Naota thu hồi cả chuỗi và bắt cho phép lại.
