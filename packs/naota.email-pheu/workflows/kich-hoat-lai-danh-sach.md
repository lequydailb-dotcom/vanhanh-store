---
type: workflow
name: Kích hoạt lại danh sách nguội
slug: kich-hoat-lai-danh-sach
status: active
description: Chuỗi email kéo lại người đã lâu không mở, và dọn danh sách một cách
  tử tế.
steps:
- agent: em-chien-luoc-pheu
  task: 'Danh sách sau đã nguội: {{input}}


    Đoán vì sao họ ngừng mở: nội dung lệch nhu cầu, gửi quá dày, hay đã giải quyết
    xong vấn đề. Với mỗi giả thuyết, nói cách kiểm chứng bằng một email.'
- agent: em-viet-email
  task: 'Viết chuỗi 4 email kích hoạt lại theo phân tích dưới đây:


    {{prev}}


    Email cuối phải là một lời chia tay tử tế, cho người ta rời đi dễ dàng. Danh sách
    nhỏ mà chịu mở còn hơn danh sách to mà chết.'
  verify_agent: em-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Chuỗi email kéo lại người đã lâu không mở, và dọn danh sách một cách tử tế.
