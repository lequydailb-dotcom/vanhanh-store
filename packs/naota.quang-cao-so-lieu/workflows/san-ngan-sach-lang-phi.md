---
type: workflow
name: Săn ngân sách lãng phí
slug: san-ngan-sach-lang-phi
status: active
description: Tìm nhóm quảng cáo đang tiêu tiền mà không ra đơn, ước tính số tiền cứu
  được.
steps:
- agent: qc-phan-tich-so-lieu
  task: 'Liệt kê mọi nhóm quảng cáo đang chạy trong kỳ: {{input}}


    Với từng nhóm, lấy chi phí, số đơn, chi phí trên mỗi đơn. Sắp xếp theo chi phí
    giảm dần. Đánh dấu nhóm tiêu tiền mà không có đơn nào.'
- agent: qc-phan-tich-quang-cao
  task: 'Từ danh sách dưới đây, chỉ ra chỗ đang lãng phí:


    {{prev}}


    Với mỗi nhóm đề nghị tắt hoặc giảm, nói rõ vì sao, tiền tiết kiệm được mỗi tháng
    là bao nhiêu, và rủi ro nếu tắt nhầm. Xếp theo số tiền cứu được, nhiều nhất lên
    đầu.'
  verify_agent: qc-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Tìm nhóm quảng cáo đang tiêu tiền mà không ra đơn, ước tính số tiền cứu được.
