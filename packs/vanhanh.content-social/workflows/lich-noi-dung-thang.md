---
type: workflow
name: Lịch nội dung một tháng
slug: lich-noi-dung-thang
status: active
description: Từ chủ đề và sản phẩm đang bán, lên lịch nội dung một tháng có nhịp bán
  xen nhịp cho đi.
steps:
- agent: nd-goc-nhin
  task: 'Lên khung nội dung một tháng cho: {{input}}


    Chia theo tuần. Mỗi tuần một chủ đề lớn. Trong tuần, phân bổ theo nhịp 3 bài cho
    đi giá trị, 1 bài kể chuyện, 1 bài bán. Với mỗi bài ghi tiêu đề nháp, người đọc,
    lời hứa và góc tiếp cận.'
- agent: nd-bien-tap
  task: 'Soát lại lịch nội dung dưới đây:


    {{prev}}


    Kiểm ba thứ: có bài nào trùng ý bài khác không, nhịp bán có dày quá không, và
    tuần nào đang yếu nhất. Đề xuất sửa cụ thể cho từng chỗ.'
  verify_agent: nd-kiem-chung
  max_retries: 1
updated: '2026-09-05'
---

Từ chủ đề và sản phẩm đang bán, lên lịch nội dung một tháng có nhịp bán xen nhịp cho đi.
