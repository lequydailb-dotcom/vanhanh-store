# Nguồn của gói `vanhanh.deepseek-review`

Skill trong gói này lấy từ **[DeepSeek](https://github.com/deepseek-ai/deepseek-harness)**, thư mục
[https://github.com/deepseek-ai/deepseek-harness/tree/master/.agents/skills](https://github.com/deepseek-ai/deepseek-harness/tree/master/.agents/skills).

Giấy phép gốc: **MIT** - nguyên văn ở `docs/LICENSE.txt`.

## Đã sửa những gì

Nội dung skill (thân file, `scripts/`, `references/`, `templates/`) **giữ nguyên bản
gốc, không dịch**. Chỉ frontmatter của `SKILL.md` được chỉnh cho khớp Vanhanh:

- `description` dài hơn 150 ký tự được rút gọn - router của Vanhanh cắt đúng ở
  150 nên phần dư vốn mất im lặng. Mô tả gốc được chép xuống cuối file.
- Thêm `group` để trang Kỹ năng gom nhóm.
- Vài skill được đổi tên thư mục cho khỏi trùng slug trong cùng một brain
  (ví dụ `access` -> `discord-access`).
- Mỗi `SKILL.md` có một dòng ghi nguồn ở cuối.

## Bảng đối chiếu

| Slug trong Vanhanh | Đường dẫn gốc |
|---|---|
| `dsh-code-review` | `deepseek-harness/.agents/skills/dsh-code-review` |
| `dsh-prose-standard` | `deepseek-harness/.agents/skills/dsh-prose-standard` |
| `dsh-find-simplifications` | `deepseek-harness/.agents/skills/dsh-find-simplifications` |
| `record-browser-gif` | `deepseek-harness/.agents/skills/record-browser-gif` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
