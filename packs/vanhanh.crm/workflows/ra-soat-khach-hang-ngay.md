---
type: workflow
name: Rà soát khách hàng trong ngày
slug: ra-soat-khach-hang-ngay
status: active
group: Bán hàng
description: Rà khách chờ trả lời và khách mới hôm nay, gắn tag, ra bản tóm tắt kèm câu trả lời đề xuất để chủ duyệt.
steps:
- agent: cs-cham-soc-khach
  task: 'Rà soát Inbox khách hôm nay. Yêu cầu thêm của chủ (có thể trống): {{input}}


    Làm đủ ba việc: (1) khách chờ trả lời quá 2 giờ, xếp theo mức gấp; (2) khách mới hôm
    nay và họ hỏi gì; (3) gắn tag cho khách chưa có tag. Kết thúc bằng danh sách câu trả
    lời đề xuất cho từng khách gấp, và một dòng tổng số. Không gửi tin cho khách.'
  max_retries: 1
updated: '2026-09-20'
---

Chạy một lần mỗi sáng hoặc mỗi chiều. Kết quả là bản tóm tắt để chủ đọc trong 1 phút rồi
quyết định trả lời ai trước. Muốn chạy tự động thì tạo Nhắc hẹn trỏ vào quy trình này
(trang Việc định kỳ), kèm kênh nhận báo cáo.
