# Nguồn của gói `naota.ecc-business-agents`

Agent trong gói này lấy từ **[ECC (Everything Claude Code)](https://github.com/affaan-m/ECC)** của
Affaan Mustafa, commit `76aaa77df6ad` (bản 2.2.3).

Giấy phép gốc: **MIT** - nguyên văn ở `docs/LICENSE.txt`.

## Đã sửa những gì

Thân prompt của từng agent **giữ nguyên bản gốc, không dịch**. Phần đầu file được viết
lại theo định dạng agent của Naota:

- Slug thêm tiền tố `ecc-` để không đè agent cùng tên người dùng đã có trong brain.
- `name` và `role` tiếng Việt, thêm `tags`, gán `skills` trỏ vào skill của các gói ECC
  khác trong kho (thiếu skill thì agent vẫn làm tiếp, xem dòng cuối mỗi agent).
- Bỏ `tools` và `model` của Claude Code: ở Naota, agent dùng bộ công cụ chung và chạy
  trên bộ não người dùng đang chọn.
- Cuối mỗi agent có một khối ngắn của Naota: ghi nguồn, luật trình bày và cách xử lý khi
  thiếu skill.

## Bảng đối chiếu

| Agent trong Naota | Đường dẫn gốc |
|---|---|
| `ecc-marketing` (Chiến lược gia marketing) | `ECC/agents/marketing-agent.md` |
| `ecc-seo` (Chuyên gia SEO) | `ECC/agents/seo-specialist.md` |
| `ecc-chanh-van-phong` (Chánh văn phòng) | `ECC/agents/chief-of-staff.md` |
| `ecc-cham-chat-luong` (Người chấm chất lượng) | `ECC/agents/agent-evaluator.md` |

## Lưu ý trước khi dùng

ECC viết cho Claude Code, nên vài chỗ nhắc tới lệnh `/...`, hook, đường dẫn `~/.claude` hay
MCP (Exa, firecrawl, fal.ai, Context7) mà brain của bạn có thể chưa có. Thiếu thì bỏ qua
bước đó hoặc đấu MCP tương ứng ở trang Kết nối; phần phương pháp vẫn dùng được trên mọi
bộ não của Naota.
