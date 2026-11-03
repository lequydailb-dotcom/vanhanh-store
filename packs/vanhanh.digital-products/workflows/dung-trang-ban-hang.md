---
type: workflow
name: Dựng trang bán hàng
slug: dung-trang-ban-hang
status: active
description: Từ sản phẩm ra hồ sơ khách rồi ra bài bán hàng, có bước soát lời hứa
  quá tay.
steps:
- agent: bh-chien-luoc-offer
  task: 'Dựng offer đầy đủ cho sản phẩm sau: {{input}}


    Đủ sáu mục: điểm A, điểm B, con đường, vì sao tin, rào cản, giá.'
- agent: bh-viet-ban-hang
  task: 'Viết trang bán hàng hoàn chỉnh từ offer dưới đây:


    {{prev}}


    Chỗ nào cần bằng chứng thật mà offer chưa có thì để trống kèm ghi chú trong ngoặc
    vuông, tuyệt đối không bịa.'
  verify_agent: bh-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ sản phẩm ra hồ sơ khách rồi ra bài bán hàng, có bước soát lời hứa quá tay.
