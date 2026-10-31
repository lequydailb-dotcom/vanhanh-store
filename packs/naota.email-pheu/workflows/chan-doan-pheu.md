---
type: workflow
name: Chẩn đoán phễu đang rò
slug: chan-doan-pheu
status: active
description: Từ số liệu từng khâu, chỉ ra khâu mất khách nhiều nhất và việc cần sửa
  trước.
steps:
- agent: em-chien-luoc-pheu
  task: 'Chẩn đoán phễu sau: {{input}}


    Tính tỉ lệ đi tiếp ở từng khâu. So với mức thường thấy của loại phễu này. Chỉ
    ra khâu rò nặng nhất và ước tính sửa được thì thêm bao nhiêu khách. Nếu thiếu
    số ở khâu nào, nói rõ cần đo gì trước khi đoán.'
  verify_agent: em-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ số liệu từng khâu, chỉ ra khâu mất khách nhiều nhất và việc cần sửa trước.
