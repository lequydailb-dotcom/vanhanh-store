# Nguồn của gói `vanhanh.founder`

Skill trong gói này lấy từ **[founder-skill](https://github.com/Jakeschincariol/founder-skill)** của
Jake Schincariol, commit `fd9385b0cfe1` (2026-10-06).

Giấy phép gốc: **MIT** - nguyên văn ở `docs/LICENSE.txt`.

## Đã sửa những gì

Nội dung skill (thân file, `lenses.md`, tệp mẫu `.json`/`.md` và 4 công cụ Python) **giữ nguyên
bản gốc, không dịch**. Chỉ frontmatter của `SKILL.md` được chỉnh cho khớp Vanhanh:

- `description` được viết lại cho vừa trần 150 ký tự của router Vanhanh (router cắt đúng ở 150 nên
  phần dư vốn mất im lặng). Mô tả gốc được chép xuống cuối file.
- Thêm `group: "Founder"` để trang Kỹ năng gom nhóm.
- 5 skill gọi tệp trong thư mục của chính nó qua `${CLAUDE_SKILL_DIR}` (board, consumer, pricing,
  cfo, plan) có thêm MỘT dòng `Vanhanh:` dưới tiêu đề: engine không phải Claude Code không tự thay
  biến đó, nên dòng này chỉ đường `skills/<slug>` tính từ gốc brain.
- Mỗi `SKILL.md` có một dòng ghi nguồn ở cuối.
- Không mang theo `.claude-plugin/` và `tests/` của repo gốc. Test của 4 công cụ được chép sang
  `tests/vanhanh.founder/` của kho (ngoài gói) và chạy trên chính tệp trong gói.

## Bảng đối chiếu

| Slug trong Vanhanh | Đường dẫn gốc |
|---|---|
| `founder-board` | `founder-skill/skills/founder-board` |
| `founder-competitors` | `founder-skill/skills/founder-competitors` |
| `founder-consumer` | `founder-skill/skills/founder-consumer` |
| `founder-pricing` | `founder-skill/skills/founder-pricing` |
| `founder-offer` | `founder-skill/skills/founder-offer` |
| `founder-cfo` | `founder-skill/skills/founder-cfo` |
| `founder-marketing` | `founder-skill/skills/founder-marketing` |
| `founder-brand` | `founder-skill/skills/founder-brand` |
| `founder-ops` | `founder-skill/skills/founder-ops` |
| `founder-launch` | `founder-skill/skills/founder-launch` |
| `founder-plan` | `founder-skill/skills/founder-plan` |

## Mã trong gói

Gói có 4 tệp `.py`, đều chỉ dùng thư viện chuẩn, **không gọi mạng**, không chạy lệnh ngoài, chỉ
đọc và ghi trong thư mục `founder/` (hoặc đường dẫn người dùng truyền vào):

- `founder-cfo/unit_economics.py`: tính biên đóng góp, điểm hoà vốn, năm 1 theo tháng, tiền cần có.
- `founder-consumer/panel.py`: chia thẻ người mua giả lập, viết brief cho từng người, kiểm và đếm
  câu trả lời. Không bao giờ tự trả lời thay người mua.
- `founder-pricing/van_westendorp.py`: tính khoảng giá chấp nhận được từ 4 câu trả lời giá.
- `founder-plan/compile.py`: gom các tệp trong `founder/` thành kế hoạch kinh doanh và tính kết
  luận. Nạp `../founder-cfo/unit_economics.py` nên hai skill phải nằm cạnh nhau trong `skills/`.

Đây là công cụ dòng lệnh model chạy bằng shell khi làm theo skill, không phải plugin của Vanhanh:
không tool mới nào vào MCP Hub.

## Lưu ý trước khi dùng

- Chạy theo thứ tự: board -> competitors -> consumer -> pricing -> offer -> cfo -> marketing ->
  brand -> ops -> launch -> plan. Mỗi skill đọc những gì skill trước ghi vào `founder/` ở gốc brain.
  Chạy riêng lẻ từng skill cũng được.
- `founder-board` và `founder-consumer` dùng **sub-agent song song** (tool Agent/Task). Claude Code,
  Codex và Grok Build có sẵn; engine API không có Task nên phải chạy tuần tự, chậm hơn nhiều.
  Hội đồng 100 người mua là 100 lượt gọi sub-agent: thử `--quick` (20 người) trước.
- Người mua giả lập không phải khách thật, mô hình ngôn ngữ thiên về đồng ý, nên tỉ lệ mua là
  trần trên. Không dùng câu trả lời của họ làm lời chứng thực.
- Ví dụ trong skill tính bằng đô la Mỹ. Công cụ in ký hiệu `$` cố định, con số vẫn đúng với
  đồng tiền nào cũng được, chỉ cần nhập mọi giá trị cùng một đơn vị.
- Không phải tư vấn tài chính, pháp lý hay thuế.
