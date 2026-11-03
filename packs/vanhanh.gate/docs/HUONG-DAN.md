# Gói `vanhanh.gate` - Vanhanh Gate

Cổng cho **ChatGPT, Claude và AI khác** làm việc cùng Vanhanh. Bạn chat trên chatgpt.com hay claude.ai bằng gói của mình, và AI đó gọi sang Vanhanh khi cần: xem số liệu, đọc brain, tạo nhắc lịch, gửi Zalo...

Điểm mới từ bản 2.0.0: AI đó **đọc được hội thoại của Vanhanh và nhắn thẳng vào khung chat** như bạn gõ. Ví dụ:

> "Đọc hội thoại Viết Web trên Vanhanh rồi tư vấn anh nên làm gì tiếp."

AI đọc, tư vấn cho bạn. Bạn đồng ý ngay trên ChatGPT (hay Claude), nó nhắn vào đúng hội thoại "Viết Web" để Vanhanh làm tiếp. Trên Vanhanh bạn thấy tin đó với nhãn **từ ChatGPT**, thấy Vanhanh trả lời từng chữ, bấm **Dừng** được, và Vanhanh nhớ lại cho lần sau.

> Tiền thân là gói **Vanhanh trong ChatGPT** (`vanhanh.vanhanh-trong-chatgpt`). Máy đang cài gói cũ thấy Vanhanh Gate như một bản cập nhật: token, mức quyền và địa chỉ đã dán vào ChatGPT được giữ nguyên, không phải kết nối lại.

---

## Trong gói có gì

| Loại | Slug | Việc |
|---|---|---|
| Plugin | `vanhanh-gate` | Cửa OAuth và địa chỉ MCP cho ChatGPT, Claude, cùng một trang cài đặt riêng |

AI bên ngoài dùng đúng bộ công cụ Vanhanh đã có (kết nối MCP, brain, nhắc lịch, Kanban, plugin), cộng năm công cụ chỉ có ở cổng này:

| Công cụ | Việc | Mức quyền |
|---|---|---|
| `vanhanh_chat_find` | Tìm hội thoại theo tên hoặc nội dung | Mọi mức |
| `vanhanh_chat_read` | Đọc các tin cuối của một hội thoại | Mọi mức |
| `vanhanh_chat_send` | Nhắn vào hội thoại để Vanhanh làm, rồi chờ câu trả lời | Chỉ Toàn quyền |
| `vanhanh_chat_result` | Đọc câu trả lời khi Vanhanh làm lâu | Mọi mức |
| `vanhanh_chat_note` | Ghi lại cuộc chat bên ChatGPT/Claude vào Vanhanh: bạn hỏi gì, đã chốt gì | Ghi nháp, Toàn quyền |

## Cần có gì

- **VANHANH 1.1.0 trở lên.** Bản cũ hơn thì gói bị tắt kèm lý do ngay lúc cài.
- **Gói trả phí** của ChatGPT (Plus, Pro, Business, Enterprise, Edu) hoặc của Claude (Pro, Max, Team, Enterprise).
- **Máy tính** cho bước cài đặt lần đầu.
- **Vanhanh có địa chỉ https.** ChatGPT và Claude không nhận địa chỉ kiểu `http://12.34.56.78:7777`. Gắn tên miền riêng trước (Cài đặt, mục Giọng nói, thương hiệu và truy cập).
- **Vanhanh đã đặt mật khẩu quản trị.** Bước cho phép dựa vào đăng nhập dashboard. Chưa có mật khẩu thì cổng này đóng.

---

## Bước 1: Cài gói và lấy địa chỉ

1. Mở **Vanhanh Store**, tìm **Vanhanh Gate**, bấm cài và đồng ý chạy mã.
2. Vào trang **Plugin**, tìm thẻ **Vanhanh Gate**, bấm **Mở trang**.
3. Bấm **Chép** để chép địa chỉ. Nó có dạng `https://ten-mien-cua-ban/ext/vanhanh-gate/mcp`.

## Bước 2a: Nối với ChatGPT

1. Gói **Business**: quản trị viên vào **Workspace settings, Permissions & roles, Connected data**, bật **Create custom MCP connectors**.
2. Trên chatgpt.com (máy tính): **Settings, Apps & Connectors, Advanced settings**, bật **Developer mode**.
3. Vẫn ở **Apps & Connectors**, bấm **Create**, điền:

| Ô | Điền gì |
|---|---|
| Name | `Vanhanh` |
| MCP Server URL | địa chỉ đã chép ở bước 1 |
| Authentication | **OAuth** |

4. Tích ô xác nhận tin tưởng connector, bấm **Create**.

## Bước 2b: Nối với Claude

1. Trên claude.ai (hoặc app Claude Desktop): **Settings, Connectors**, bấm **Add custom connector**.
2. Đặt tên `Vanhanh`, dán địa chỉ đã chép ở bước 1, bấm **Add**.
3. Bấm **Connect** trên connector vừa tạo.

Gói Team hay Enterprise thì chủ sở hữu tổ chức thêm connector trước ở phần quản trị, thành viên chỉ cần bấm Connect.

> Tên các mục có thể hơi khác theo phiên bản ChatGPT hay Claude. Tìm chữ "Connectors" trong phần Settings.

## Bước 3: Cho phép

ChatGPT hoặc Claude mở một trang của Vanhanh.

- Trình duyệt chưa đăng nhập Vanhanh thì trang hiện ô đăng nhập ngay tại chỗ (có cả ô mã 2 lớp nếu bạn đã bật).
- Trang tiếp theo nói rõ AI đó được làm gì và đang ở mức quyền nào. Bấm **Cho phép**.

## Bước 4: Dùng

Bật connector Vanhanh trong khung chat (ChatGPT: dấu **+**, chọn **Developer mode**, bật **Vanhanh**; Claude: nút công cụ, bật **Vanhanh**). Thử:

- "Trên Vanhanh có những hội thoại nào gần đây?"
- "Đọc hội thoại Viết Web trên Vanhanh rồi tư vấn anh nên làm gì tiếp."
- "Ok, bảo Vanhanh làm theo phương án 2."
- "Ghi lại vào Vanhanh những gì mình vừa chốt."

### Vanhanh nắm luôn ngữ cảnh bên ChatGPT, Claude (cần Vanhanh 1.2.0)

Vanhanh không đọc được lịch sử chat trên chatgpt.com hay claude.ai, nên AI bên đó **tự ghi lại** phần đáng giữ: bạn hỏi gì, đã chốt gì, vì sao. Nó ghi khi bạn vừa quyết một việc, không ghi sau mọi câu.

- Mỗi cuộc chat bên đó có một hội thoại riêng trong Lịch sử của Vanhanh, ví dụ **Từ ChatGPT: Kế hoạch Tết**.
- Ghi chép **không tốn hạn mức** bộ não của Vanhanh, nhưng vẫn vào trí nhớ và vòng tự học. Lần sau hỏi Vanhanh, nó nhớ bạn đã quyết gì.
- Muốn ghi vào đúng một hội thoại có sẵn của Vanhanh (ví dụ "Viết Web"), bảo AI đó: "ghi vào hội thoại Viết Web trên Vanhanh".
- Cần đủ lịch sử nguyên văn thì xuất dữ liệu từ ChatGPT (Settings, Data controls, Export) hay Claude (Settings, Privacy, Export data), rồi đưa tệp cho Vanhanh đọc.

Vanhanh làm lâu thì AI kia báo kết quả sẽ hiện trên khung chat của Vanhanh, và bạn nhắn nó **"xem tiếp"** khi muốn nó đọc lại.

---

## Mức quyền

Chọn trên trang của gói (trang Plugin, nút **Mở trang**). Đổi xong có hiệu lực ngay, không cần kết nối lại.

| Mức | AI bên ngoài được làm gì |
|---|---|
| **Toàn quyền** (mặc định) | Đọc dữ liệu, nhắn vào khung chat để Vanhanh làm, và làm việc thật: gửi tin, tạo đơn, đăng bài |
| **Tự làm có giới hạn** | Đọc dữ liệu, đọc hội thoại, ghi chép và viết nháp. Không nhắn vào khung chat, không làm việc ra bên ngoài |
| **Chỉ đọc và gợi ý** | Chỉ đọc, kể cả đọc hội thoại. Không ghi file, không ghi chép, không nhắn vào khung chat |

Vanhanh tự chặn ở phía mình theo mức đã chọn. AI bên ngoài không tự nâng quyền được.

## Ngắt kết nối

- **Tạm dừng:** tắt gói **Vanhanh Gate** ở Vanhanh Store. Kết nối cũ giữ nguyên, bật lại là dùng tiếp.
- **Ngắt hẳn:** bấm **Ngắt mọi kết nối** trên trang của gói. Muốn dùng lại thì nối lại từ bước 2.
- **Gỡ gói:** gỡ ở Vanhanh Store. Mọi đường của gói biến mất cùng lúc.

---

## Điều cần biết trước

- **AI bên ngoài không tự thức dậy.** Nó chỉ đọc được câu trả lời của Vanhanh trong lúc nó đang trả lời bạn. Việc dài thì kết quả luôn nằm trên khung chat của Vanhanh, và bạn nhắn AI kia "xem tiếp" khi cần.
- **Tin nhắn vào khung chat tốn hạn mức bộ não của Vanhanh.** Lượt đó chạy bằng model bạn chọn cho Vanhanh (Claude Code, Codex...), như khi bạn tự gõ. Phần tư vấn bên ChatGPT hay Claude thì tốn hạn mức gói bên đó.
- **Chỉ nhắn được vào hội thoại của bạn** (khung Trò chuyện, chat với Cộng sự). Hội thoại của khách và nhóm chat thì AI bên ngoài không đọc, không nhắn được.
- **Công cụ ngoài khung chat làm việc trên brain đang mở gần nhất.** Kết quả mỗi công cụ có ghi rõ đang ở brain nào. Tin nhắn vào khung chat thì chạy trên brain của chính hội thoại đó.

## Khi không chạy

| Bạn thấy | Nguyên nhân | Làm gì |
|---|---|---|
| Không có mục Developer mode (ChatGPT) | Gói miễn phí, hoặc đang ở app điện thoại | Dùng gói trả phí, mở chatgpt.com trên máy tính |
| Không có nút Add custom connector (Claude) | Gói miễn phí, hoặc tổ chức chưa cho phép | Dùng gói trả phí, hỏi chủ sở hữu tổ chức |
| Báo không kết nối được server | Địa chỉ không phải https, gói đang tắt, hoặc Vanhanh chưa có mật khẩu | Xem lại "Cần có gì" và bước 1 |
| AI báo cần mức Toàn quyền khi nhắn vào khung chat | Gói đang ở mức thấp hơn | Nâng mức quyền trên trang của gói |
| Trang Vanhanh báo "Yêu cầu này đã quá hạn" | Để trang Cho phép mở quá 10 phút | Kết nối lại từ ChatGPT hoặc Claude |
| Đang dùng tốt bỗng bắt kết nối lại | 30 ngày không dùng, hoặc đã bấm Ngắt mọi kết nối | Kết nối lại |

## An toàn

- Token chỉ lưu dạng băm trong thư mục dữ liệu riêng của gói, không nằm trong brain.
- Cổng chỉ trả mã về đúng máy của OpenAI (`chatgpt.com`, `*.openai.com`), của Anthropic (`claude.ai`, `claude.com`), hoặc chính máy của bạn (`localhost`, cho Claude Code và Claude Desktop). Kẻ gian tự đăng ký một kết nối trỏ về máy mình sẽ không nhận được mã.
- Token của gói này tách hẳn khỏi token Claude Code và Codex dùng. Ngắt bên này không ảnh hưởng bên kia.
- Refresh token xoay vòng: một token cũ bị dùng lại là Vanhanh thu hồi cả chuỗi và bắt cho phép lại.
