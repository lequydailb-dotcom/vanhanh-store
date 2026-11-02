# Gói `naota.crm` - Quản lý khách hàng (CRM)

Tầng CRM đặt lên **trang Hội thoại** của NAOTA. Lõi Naota đã gom tin
khách từ bot Telegram, bot Zalo và Zalo cá nhân về một kho; gói này cho Naota đọc kho đó như
một sổ khách hàng: ai đang chờ, ai là ai, gắn tag, ghi chú, thống kê, xuất Excel.

Cần **NAOTA 1.0.0 trở lên**. Bản cũ hơn thì gói bị tắt kèm lý do ngay lúc cài.

## Trong gói có gì

| Loại | Slug | Việc |
|---|---|---|
| Plugin | `crm` | 8 tool `crm_*` cho mọi engine (xem bên dưới) |
| Kỹ năng | `cham-soc-khach-hang` | Cách rà Inbox, gắn tag, xuất CSV, và giới hạn của dữ liệu |
| Trợ lý | `cs-cham-soc-khach` | Nhân viên CSKH: rà khách chờ, soạn câu trả lời để chủ duyệt |
| Quy trình | `ra-soat-khach-hang-ngay` | Chạy sáng / chiều: khách chờ, khách mới, tag, đề xuất |

## 8 tool

| Tool | Quyền | Việc |
|---|---|---|
| `crm_khach_hang` | đọc | Danh sách khách, lọc theo kênh / tag / chữ / số ngày |
| `crm_ho_so_khach` | đọc | Hồ sơ một khách kèm mọi hội thoại và tin gần nhất |
| `crm_hoi_thoai` | đọc | Danh sách hội thoại, hoặc toàn bộ tin của một hội thoại |
| `crm_tim_tin` | đọc | Tìm chữ trong mọi tin nhắn |
| `crm_cho_tra_loi` | đọc | Hội thoại câu cuối là của khách, quá N giờ chưa ai trả lời |
| `crm_thong_ke` | đọc | Tổng, hôm nay, chưa đọc, theo kênh, khách mới theo ngày, số khách mỗi tag |
| `crm_gan_tag` | ghi nháp | Gắn / bỏ tag, ghi chú lên khách (chỉ ghi vào kho của Naota) |
| `crm_xuat_csv` | ghi nháp | Xuất danh sách khách ra `exports/` của brain, mở bằng Excel |

Không tool nào gửi tin hay gọi ra ngoài. Muốn trả lời khách thì vẫn dùng tool của kênh
(`zalo_send_message`, bot Telegram) hoặc app trên điện thoại.

## Ví dụ hỏi trong chat

- "Có khách nào chờ hơn 2 tiếng chưa được trả lời không?"
- "Chị Lan bên Zalo đã hỏi gì, tóm tắt cho anh."
- "Gắn tag VIP và ghi chú 'thích màu be' cho chị Lan."
- "Tuần này bao nhiêu khách mới, kênh nào nhiều nhất?"
- "Xuất danh sách khách đã hỏi giá ra Excel."

## Giới hạn phải biết

- Kho chỉ có dữ liệu **từ lúc bot / Zalo được nối vào Naota**, không có lịch sử cũ.
- **Zalo cá nhân chỉ ghi khi bạn bật** ở mục Kênh của trang Hội thoại, và tin bạn tự trả lời
  bằng app trên điện thoại có thể không vào kho, nên "chờ trả lời" ở kênh này là gợi ý để kiểm
  lại, không phải kết luận.
- Ảnh, file, tin thoại chỉ giữ loại tin và tên / đường dẫn; nội dung file nằm trong inbox của
  brain và bị dọn theo hạn.

## Sau khi cài

Trợ lý, kỹ năng và quy trình được ghi vào **brain đang mở lúc bấm Cài**. Trợ lý để
`model: ""` (chạy theo mặc định của engine đang dùng). Muốn rà tự động mỗi sáng, tạo một
Nhắc hẹn trỏ vào quy trình `ra-soat-khach-hang-ngay` ở trang Việc định kỳ, kèm kênh nhận báo
cáo (Telegram của bạn hoặc chat dashboard).
