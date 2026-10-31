# Nguồn của gói `naota.anthropic-chat-channels`

Skill trong gói này lấy từ **[Anthropic](https://github.com/anthropics/claude-plugins-official)**, thư mục
[https://github.com/anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official).

Giấy phép gốc: **Apache-2.0** - nguyên văn ở `docs/LICENSE.txt`.

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
| `discord-configure` | `claude-plugins-official/external_plugins/discord/skills/configure` |
| `discord-access` | `claude-plugins-official/external_plugins/discord/skills/access` |
| `telegram-configure` | `claude-plugins-official/external_plugins/telegram/skills/configure` |
| `telegram-access` | `claude-plugins-official/external_plugins/telegram/skills/access` |
| `imessage-configure` | `claude-plugins-official/external_plugins/imessage/skills/configure` |
| `imessage-access` | `claude-plugins-official/external_plugins/imessage/skills/access` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
