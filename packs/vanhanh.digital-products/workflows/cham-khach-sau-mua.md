---
type: workflow
name: Chăm khách sau mua
slug: cham-khach-sau-mua
status: active
description: Chuỗi dẫn khách mới tới kết quả đầu tiên rồi xin lời chứng thực dùng
  được.
steps:
- agent: bh-cham-khach
  task: 'Thiết kế chuỗi chăm khách sau mua cho sản phẩm: {{input}}


    Tìm kết quả đầu tiên khách đạt được trong 24 giờ, liệt kê chỗ hay tắc, rồi ra
    chuỗi tin nhắn kèm mốc thời gian gửi.'
- agent: bh-cham-khach
  task: 'Từ chuỗi dưới đây, soạn thêm phần xin lời chứng thực:


    {{prev}}


    Gửi sau khi khách có kết quả thật. Hỏi bằng câu cụ thể đo được, không hỏi chung
    chung. Kèm cách xử lý khi khách im lặng.'
  verify_agent: bh-kiem-chung
  max_retries: 1
updated: '2026-09-05'
---

Chuỗi dẫn khách mới tới kết quả đầu tiên rồi xin lời chứng thực dùng được.
