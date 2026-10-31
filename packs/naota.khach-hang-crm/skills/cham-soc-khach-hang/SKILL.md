---
name: Chăm sóc khách hàng đa kênh
description: Rà Inbox khách từ Telegram, Zalo Bot, Zalo cá nhân bằng tool crm_*: khách chờ trả lời, hồ sơ, gắn tag, ghi chú, xuất CSV, thống kê.
description_en: "Work the multi-channel customer inbox with the crm_* tools: unanswered customers, profiles, tags, notes, CSV export, stats."
group: Bán hàng
---

# Chăm sóc khách hàng đa kênh

## Khi nào dùng

Khi người dùng hỏi những câu kiểu: "hôm nay có khách nào chưa được trả lời", "khách A đã
hỏi gì", "gắn tag VIP cho chị Lan", "tuần này có bao nhiêu khách mới", "xuất danh sách
khách đã hỏi giá ra Excel", "khách nào hỏi về hoàn tiền", "tóm tắt hội thoại với anh Nam".

Không dùng để GỬI tin cho khách: tool `crm_*` chỉ đọc và ghi tag. Muốn nhắn thì dùng tool của
kênh (`zalo_send_message`, bot Telegram) và chỉ khi người dùng bảo gửi.

## Dữ liệu này từ đâu và giới hạn của nó

Kho hội thoại của Naota (trang **Hội thoại** trên thanh bên) gom tin từ ba nguồn: khách nhắn
cho bot Telegram, khách nhắn cho bot Zalo, và tin gửi tới tài khoản Zalo cá nhân đã đấu.

Ba điều phải nhớ khi kết luận:

- **Chỉ có dữ liệu từ ngày Naota bắt đầu trực.** Không có lịch sử cũ trước đó.
- **Zalo cá nhân chỉ ghi khi chủ bật** (mục Kênh ở trang Hội thoại), và tin chủ tự trả lời
  bằng app trên điện thoại có thể không vào kho. Nên hội thoại Zalo cá nhân "chờ trả lời" có
  thể đã được trả lời rồi; nói rõ điều đó, đừng kết luận "khách bị bỏ quên".
- **Ảnh, file, tin thoại chỉ giữ loại tin và tên/đường dẫn**, không giữ nội dung. Muốn xem thì
  mở file trong inbox của brain hoặc đường link `url` nếu có.

## Cách làm từng việc

**Rà khách chờ trả lời (việc nên làm mỗi sáng và mỗi chiều)**
1. `crm_cho_tra_loi` với `gio` = 2 (hoặc theo người dùng).
2. Với mỗi hội thoại, đọc `tin_cuoi`; câu nào cần người thật (hỏi giá sỉ, khiếu nại, đòi hoàn
   tiền) thì nêu lên đầu.
3. Báo dạng danh sách ngắn: tên khách, kênh, chờ bao lâu, câu khách hỏi. Kèm gợi ý trả lời
   nếu người dùng muốn, nhưng KHÔNG tự gửi.

**Hồ sơ một khách**
1. `crm_ho_so_khach` với `q` là tên. Nhiều người trùng tên thì tool trả danh sách: hỏi lại
   người dùng chọn ai, đừng đoán.
2. Tóm tắt: khách đã hỏi gì, đã được trả lời gì, còn gì dang dở, tag và ghi chú hiện có.

**Gắn tag và ghi chú**
- Dùng `crm_gan_tag` với `khach_id`. Tag ngắn, viết hoa chữ đầu, dùng lại tag đã có (xem
  `crm_thong_ke` mục `tag`) thay vì sinh tag mới gần nghĩa. Bộ tag gợi ý: `Quan tâm`,
  `Đã hỏi giá`, `Đã mua`, `VIP`, `Khiếu nại`, `Cần gọi lại`.
- Ghi chú là chỗ để thứ tool không tự thấy: khách thích màu gì, hẹn gọi lúc nào, lý do chưa mua.

**Thống kê và xuất**
- `crm_thong_ke` cho số hôm nay / tuần / theo kênh và khách mới theo ngày. So với tuần trước
  nếu người dùng hỏi xu hướng.
- `crm_xuat_csv` ghi file vào `exports/` của brain; nhúng link `[tên file](exports/...)` vào
  câu trả lời để người dùng tải.

## Lỗi hay gặp

- Tool trả `ERROR: ... cần NAOTA 1.0.0`: Naota chưa có kho hội thoại. Bảo người dùng cập
  nhật Naota (mục Cập nhật trên thanh bên).
- Kho trống dù đã có bot: bot chưa được BẬT ở trang Chatbot, hoặc chưa có khách nhắn từ lúc
  bật. Với Zalo cá nhân: kiểm công tắc Ghi hội thoại ở mục Kênh của trang Hội thoại.
