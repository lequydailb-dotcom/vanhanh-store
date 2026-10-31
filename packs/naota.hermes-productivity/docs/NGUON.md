# Nguồn của gói `naota.hermes-productivity`

Skill trong gói này lấy từ **[Nous Research](https://github.com/NousResearch/hermes-agent)**, thư mục
[https://github.com/NousResearch/hermes-agent/tree/main/skills](https://github.com/NousResearch/hermes-agent/tree/main/skills).

Giấy phép gốc: **MIT** - nguyên văn ở `docs/LICENSE.txt`.

## Đã sửa những gì

Nội dung skill (thân file, `scripts/`, `references/`, `templates/`) **giữ nguyên bản
gốc, không dịch**. Chỉ frontmatter của `SKILL.md` được chỉnh cho khớp Naota:

- `description` dài hơn 150 ký tự được rút gọn - router của Naota cắt đúng ở
  150 nên phần dư vốn mất im lặng. Mô tả gốc được chép xuống cuối file.
- Thêm `group` để trang Kỹ năng gom nhóm.
- Vài skill được đổi tên thư mục cho khỏi trùng slug trong cùng một brain
  (ví dụ `access` -> `discord-access`).
- Mỗi `SKILL.md` có một dòng ghi nguồn ở cuối.

## Bảng đối chiếu

| Slug trong Naota | Đường dẫn gốc |
|---|---|
| `airtable` | `hermes-agent/skills/productivity/airtable` |
| `box` | `hermes-agent/skills/productivity/box` |
| `notion` | `hermes-agent/skills/productivity/notion` |
| `obsidian` | `hermes-agent/skills/note-taking/obsidian` |
| `google-workspace` | `hermes-agent/skills/productivity/google-workspace` |
| `teams-meeting-pipeline` | `hermes-agent/skills/productivity/teams-meeting-pipeline` |
| `maps` | `hermes-agent/skills/productivity/maps` |
| `weekly-review-planning` | `hermes-agent/skills/productivity/weekly-review-planning` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
