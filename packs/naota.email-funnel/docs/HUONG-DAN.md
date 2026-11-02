# Gói `naota.email-funnel`

3 trợ lý và 3 quy trình, viết riêng cho kho Naota.

## Vì sao trợ lý và quy trình nằm chung một gói

Workflow gọi agent bằng slug. `_agent_sysprompt` đọc file agent bằng `_read_md`, và thiếu file thì hàm đó trả về rỗng chứ KHÔNG báo lỗi. Nghĩa là một workflow thiếu agent vẫn chạy, nhưng chạy với một agent không có vai trò lẫn prompt, và không ai được báo. Vì vậy gói này mang theo đủ agent mà workflow của nó cần.

## Vì sao slug agent có tiền tố riêng

Bốn gói trong bộ này đều có một agent kiểm chứng. Nếu chúng dùng chung một slug thì `pack_vault` chỉ ghi được bản của gói cài trước, và gỡ gói đó sẽ xoá file mà ba gói kia vẫn đang gọi. Tiền tố riêng giữ cho bốn gói độc lập hoàn toàn: cài lẻ gói nào cũng chạy, gỡ gói nào cũng không đụng gói khác.

## Quy trình trong gói

| Slug | Tên | Chuỗi agent |
|---|---|---|
| `chuoi-email-sau-lead-magnet` | Chuỗi email sau tài liệu miễn phí | em-chien-luoc-pheu -> em-viet-email |
| `kich-hoat-lai-danh-sach` | Kích hoạt lại danh sách nguội | em-chien-luoc-pheu -> em-viet-email |
| `chan-doan-pheu` | Chẩn đoán phễu đang rò | em-chien-luoc-pheu |

Workflow chạy tuần tự. `{{input}}` là thứ bạn gõ vào lúc chạy, `{{prev}}` là kết quả của bước liền trước. Bước có `verify_agent` sẽ được agent kiểm chứng soi lại, chưa đạt thì chạy lại tối đa `max_retries` lần.

## Trợ lý trong gói

- `em-chien-luoc-pheu` - Chiến lược phễu: Vạch đường từ tài liệu miễn phí tới sản phẩm trả phí, và chỉ ra khâu đang rò khách.
- `em-viet-email` - Người viết email: Viết email dạng thư tay, mỗi email một ý, có lý do mở và lý do đọc tiếp.
- `em-kiem-chung` - Kiểm chứng độc lập (email): Đánh giá độc lập chuỗi email, mặc định là nó đang lộ quá nhiều hoặc hứa quá tay.

## Skill đã gắn sẵn cho từng trợ lý

| Trợ lý | Skill |
|---|---|
| `em-chien-luoc-pheu` | `brainstorming` (cần `naota.superpowers`), `query-wiki` (hệ thống), `notes` (hệ thống) |
| `em-kiem-chung` | `grounded-citations` (cần `naota.hermes-research`), `verification-before-completion` (cần `naota.superpowers`) |
| `em-viet-email` | `humanizer` (cần `naota.hermes-creative`), `query-wiki` (hệ thống) |

Skill ghi **(hệ thống)** có sẵn trong mọi brain, không phải cài gì thêm.

Skill còn lại đến từ các gói kỹ năng trong kho: `naota.hermes-creative`, `naota.hermes-research`, `naota.superpowers`. Naota không có cơ chế khai phụ thuộc giữa các gói, nên nếu bạn chưa cài chúng thì agent vẫn chạy bình thường: mỗi agent được dạy là gọi skill không có thì đi tiếp bằng năng lực sẵn có rồi báo lại một dòng cho bạn biết thiếu gì.

## Chỗ bạn nên chỉnh sau khi cài

1. **Model.** Mọi agent để `model: ""`, tức chạy theo mặc định của engine bạn đang dùng. Ghim model cụ thể chỉ khi bạn chắc máy mình có model đó.

Agent và workflow được ghi vào **brain đang mở lúc bấm Cài**, không phải mọi brain. Naota không ghi đè mục bạn tự tạo trùng tên, và gỡ gói chỉ xoá thứ bạn chưa sửa.
