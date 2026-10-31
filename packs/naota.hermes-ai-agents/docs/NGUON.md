# Nguồn của gói `naota.hermes-ai-agents`

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
| `claude-code` | `hermes-agent/skills/autonomous-ai-agents/claude-code` |
| `codex` | `hermes-agent/skills/autonomous-ai-agents/codex` |
| `opencode` | `hermes-agent/skills/autonomous-ai-agents/opencode` |
| `computer-use` | `hermes-agent/skills/autonomous-ai-agents/computer-use` |
| `hermes-agent` | `hermes-agent/skills/autonomous-ai-agents/hermes-agent` |
| `hermes-agent-skill-authoring` | `hermes-agent/skills/software-development/hermes-agent-skill-authoring` |
| `inspecting-hermes-desktop-dom` | `hermes-agent/skills/software-development/inspecting-hermes-desktop-dom` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
