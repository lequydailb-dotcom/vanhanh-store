# Gói `naota.research-assistants`

3 trợ lý đứng riêng. Không cần workflow, gọi thẳng từ trang Trợ lý hoặc từ chat.

## Trợ lý và skill đã gắn

| Slug | Tên | Skill |
|---|---|---|
| `tl-nghien-cuu` | Trợ lý nghiên cứu | `grounded-citations` (cần `naota.hermes-research`), `ingest-source` (hệ thống), `query-wiki` (hệ thống), `notes` (hệ thống) |
| `tl-dich-ban-dia` | Dịch và bản địa hoá | `humanizer` (cần `naota.hermes-creative`), `notes` (hệ thống) |
| `tl-giai-thich` | Người giải thích | `grounded-citations` (cần `naota.hermes-research`), `query-wiki` (hệ thống) |

Skill ghi **(hệ thống)** có sẵn trong mọi brain, không phải cài gì thêm.

Skill còn lại đến từ: `naota.hermes-creative`, `naota.hermes-research`. Naota không có cơ chế khai phụ thuộc giữa các gói, nên chưa cài chúng thì trợ lý vẫn chạy: mỗi trợ lý được dạy là gọi skill không có thì đi tiếp bằng năng lực sẵn có rồi báo lại một dòng cho bạn biết thiếu gì.

## Chỗ bạn nên chỉnh sau khi cài

Mọi trợ lý để `model: ""`, tức chạy theo mặc định của engine bạn đang dùng. Ghim model cụ thể chỉ khi bạn chắc máy mình có model đó.

Trợ lý được ghi vào **brain đang mở lúc bấm Cài**, không phải mọi brain. Naota không ghi đè trợ lý bạn tự tạo trùng tên, và gỡ gói chỉ xoá thứ bạn chưa sửa.
