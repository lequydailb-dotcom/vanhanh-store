# Nguồn của gói `vanhanh.hermes-dev`

Skill trong gói này lấy từ **[Nous Research](https://github.com/NousResearch/hermes-agent)**, thư mục
[https://github.com/NousResearch/hermes-agent/tree/main/skills](https://github.com/NousResearch/hermes-agent/tree/main/skills).

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
| `github` | `hermes-agent/skills/software-development/github` |
| `test-driven-development` | `hermes-agent/skills/software-development/test-driven-development` |
| `systematic-debugging` | `hermes-agent/skills/software-development/systematic-debugging` |
| `requesting-code-review` | `hermes-agent/skills/software-development/requesting-code-review` |
| `simplify-code` | `hermes-agent/skills/software-development/simplify-code` |
| `spike` | `hermes-agent/skills/software-development/spike` |
| `codebase-inspection` | `hermes-agent/skills/software-development/codebase-inspection` |
| `sdlc-review` | `hermes-agent/skills/devops/sdlc-review` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
