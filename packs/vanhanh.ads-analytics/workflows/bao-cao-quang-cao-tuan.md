---
type: workflow
name: Báo cáo quảng cáo tuần
slug: bao-cao-quang-cao-tuan
status: active
description: Gom số quảng cáo tuần rồi ra báo cáo kèm việc cần làm, có kiểm chứng
  độc lập.
steps:
- agent: qc-phan-tich-so-lieu
  task: 'Gom số liệu quảng cáo cho kỳ sau: {{input}}


    Lấy chi phí, hiển thị, click, đơn hàng và doanh thu của từng chiến dịch, so với
    kỳ liền trước. Nguồn nào chưa lấy được thì ghi rõ là thiếu. Trả về bảng cộng ba
    dòng nhận xét.'
- agent: qc-phan-tich-quang-cao
  task: 'Từ bảng số liệu dưới đây, viết báo cáo tuần cho chủ shop:


    {{prev}}


    Mở đầu bằng chỗ đang đốt tiền. Sau đó tới chỗ đang tốt và nên nhân lên. Kết bằng
    danh sách 3-5 việc bấm được trong tuần tới, mỗi việc kèm con số biện minh.'
  verify_agent: qc-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Gom số quảng cáo tuần rồi ra báo cáo kèm việc cần làm, có kiểm chứng độc lập.
