---
type: workflow
name: Chuỗi email sau tài liệu miễn phí
slug: chuoi-email-sau-lead-magnet
status: active
description: Từ tài liệu miễn phí và sản phẩm trả phí, ra chuỗi email nuôi dưỡng có
  kiểm chứng phần được phép cho đi.
steps:
- agent: em-chien-luoc-pheu
  task: 'Vạch đường từ miễn phí sang trả phí cho trường hợp sau: {{input}}'
- agent: em-viet-email
  task: 'Viết chuỗi email theo chiến lược dưới đây:


    {{prev}}


    Mỗi lý do chưa mua thành một email. Email đầu gửi ngay sau khi tải, các email
    sau giãn dần. Ghi rõ ngày gửi của từng email.'
  verify_agent: em-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ tài liệu miễn phí và sản phẩm trả phí, ra chuỗi email nuôi dưỡng có kiểm chứng phần được phép cho đi.
