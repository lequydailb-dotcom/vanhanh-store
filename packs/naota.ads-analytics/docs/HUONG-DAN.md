# Gói `naota.ads-analytics`

3 trợ lý và 3 quy trình, viết riêng cho kho Naota.

## Vì sao trợ lý và quy trình nằm chung một gói

Workflow gọi agent bằng slug. `_agent_sysprompt` đọc file agent bằng `_read_md`, và thiếu file thì hàm đó trả về rỗng chứ KHÔNG báo lỗi. Nghĩa là một workflow thiếu agent vẫn chạy, nhưng chạy với một agent không có vai trò lẫn prompt, và không ai được báo. Vì vậy gói này mang theo đủ agent mà workflow của nó cần.

## Vì sao slug agent có tiền tố riêng

Bốn gói trong bộ này đều có một agent kiểm chứng. Nếu chúng dùng chung một slug thì `pack_vault` chỉ ghi được bản của gói cài trước, và gỡ gói đó sẽ xoá file mà ba gói kia vẫn đang gọi. Tiền tố riêng giữ cho bốn gói độc lập hoàn toàn: cài lẻ gói nào cũng chạy, gỡ gói nào cũng không đụng gói khác.

## Quy trình trong gói

| Slug | Tên | Chuỗi agent |
|---|---|---|
| `bao-cao-quang-cao-tuan` | Báo cáo quảng cáo tuần | qc-phan-tich-so-lieu -> qc-phan-tich-quang-cao |
| `san-ngan-sach-lang-phi` | Săn ngân sách lãng phí | qc-phan-tich-so-lieu -> qc-phan-tich-quang-cao |
| `doc-search-console-thang` | Đọc Search Console hàng tháng | qc-phan-tich-so-lieu -> qc-phan-tich-quang-cao |

Workflow chạy tuần tự. `{{input}}` là thứ bạn gõ vào lúc chạy, `{{prev}}` là kết quả của bước liền trước. Bước có `verify_agent` sẽ được agent kiểm chứng soi lại, chưa đạt thì chạy lại tối đa `max_retries` lần.

## Trợ lý trong gói

- `qc-phan-tich-quang-cao` - Chuyên viên quảng cáo: Đọc số liệu quảng cáo Meta, Google, TikTok rồi chỉ ra chỗ đang đốt tiền và việc cần làm tuần tới.
- `qc-phan-tich-so-lieu` - Chuyên viên số liệu: Gom số từ bảng tính, Search Console, đơn hàng thành một bảng gọn kèm điều bất thường đáng chú ý.
- `qc-kiem-chung` - Kiểm chứng độc lập (quảng cáo): Đánh giá độc lập báo cáo quảng cáo, mặc định là nó đang sai cho tới khi chứng minh được ngược lại.

## Skill đã gắn sẵn cho từng trợ lý

| Trợ lý | Skill |
|---|---|
| `qc-kiem-chung` | `grounded-citations` (cần `naota.hermes-research`), `verification-before-completion` (cần `naota.superpowers`) |
| `qc-phan-tich-quang-cao` | `grounded-citations` (cần `naota.hermes-research`), `query-wiki` (hệ thống), `notes` (hệ thống) |
| `qc-phan-tich-so-lieu` | `xlsx` (cần `naota.hermes-office`), `notes` (hệ thống) |

Skill ghi **(hệ thống)** có sẵn trong mọi brain, không phải cài gì thêm.

Skill còn lại đến từ các gói kỹ năng trong kho: `naota.hermes-office`, `naota.hermes-research`, `naota.superpowers`. Naota không có cơ chế khai phụ thuộc giữa các gói, nên nếu bạn chưa cài chúng thì agent vẫn chạy bình thường: mỗi agent được dạy là gọi skill không có thì đi tiếp bằng năng lực sẵn có rồi báo lại một dòng cho bạn biết thiếu gì.

## Chỗ bạn nên chỉnh sau khi cài

1. **Model.** Mọi agent để `model: ""`, tức chạy theo mặc định của engine bạn đang dùng. Ghim model cụ thể chỉ khi bạn chắc máy mình có model đó.

Agent và workflow được ghi vào **brain đang mở lúc bấm Cài**, không phải mọi brain. Naota không ghi đè mục bạn tự tạo trùng tên, và gỡ gói chỉ xoá thứ bạn chưa sửa.
