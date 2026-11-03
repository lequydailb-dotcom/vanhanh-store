---
type: workflow
name: Đọc Search Console hàng tháng
slug: doc-search-console-thang
status: active
description: Từ dữ liệu Search Console ra danh sách trang và từ khoá đáng làm tiếp.
steps:
- agent: qc-phan-tich-so-lieu
  task: 'Gom dữ liệu Google Search Console cho kỳ: {{input}}


    Lấy top trang và top từ khoá theo hiển thị, click, tỉ lệ click và vị trí trung
    bình, so với kỳ trước.'
- agent: qc-phan-tich-quang-cao
  task: 'Từ dữ liệu dưới đây, chỉ ra việc đáng làm:


    {{prev}}


    Ba nhóm: trang nhiều hiển thị mà ít click (sửa tiêu đề và mô tả), từ khoá đang
    ở vị trí 8-20 (đẩy lên trang một dễ hơn làm mới), và trang đang tụt so với kỳ
    trước. Mỗi mục kèm việc cụ thể.'
  verify_agent: qc-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ dữ liệu Search Console ra danh sách trang và từ khoá đáng làm tiếp.
