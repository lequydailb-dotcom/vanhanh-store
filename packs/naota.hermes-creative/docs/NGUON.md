# Nguồn của gói `naota.hermes-creative`

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
| `architecture-diagram` | `hermes-agent/skills/creative/architecture-diagram` |
| `ascii-video` | `hermes-agent/skills/creative/ascii-video` |
| `baoyu-infographic` | `hermes-agent/skills/creative/baoyu-infographic` |
| `claude-design` | `hermes-agent/skills/creative/claude-design` |
| `design-md` | `hermes-agent/skills/creative/design-md` |
| `humanizer` | `hermes-agent/skills/creative/humanizer` |
| `manim-video` | `hermes-agent/skills/creative/manim-video` |
| `p5js` | `hermes-agent/skills/creative/p5js` |
| `popular-web-designs` | `hermes-agent/skills/creative/popular-web-designs` |
| `songwriting-and-ai-music` | `hermes-agent/skills/creative/songwriting-and-ai-music` |

## Lưu ý trước khi dùng

Skill ở đây viết cho môi trường gốc của nó, nên có skill nhắc tới CLI hoặc biến môi
trường mà máy bạn chưa có. Đọc mục `## Prerequisites` trong từng skill trước khi chạy.
