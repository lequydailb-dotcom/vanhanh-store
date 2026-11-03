---
type: workflow
name: Từ kỹ năng ra sản phẩm số
slug: y-tuong-thanh-san-pham-so
status: active
description: Từ những gì bạn đã biết làm, ra ý tưởng sản phẩm số bán được kèm lời
  chào hoàn chỉnh.
steps:
- agent: bh-chien-luoc-offer
  task: 'Tìm sản phẩm số bán được từ những gì người này đã có: {{input}}


    Đề xuất 3 hướng, mỗi hướng nói rõ bán cho ai, giải quyết gì, vì sao người này
    đủ tư cách bán nó. Chấm điểm từng hướng theo mức dễ làm và mức người ta sẵn sàng
    trả tiền, rồi chọn một hướng và nói vì sao.'
- agent: bh-chien-luoc-offer
  task: 'Đóng gói hướng đã chọn dưới đây thành offer hoàn chỉnh:


    {{prev}}


    Đủ sáu mục: điểm A, điểm B, con đường, vì sao tin, rào cản, giá.'
  verify_agent: bh-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ những gì bạn đã biết làm, ra ý tưởng sản phẩm số bán được kèm lời chào hoàn chỉnh.
