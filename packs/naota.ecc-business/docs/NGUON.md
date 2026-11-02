# Nguồn của gói `naota.ecc-business`

Skill trong gói này lấy từ **[ECC (Everything Claude Code)](https://github.com/affaan-m/ECC)** của
Affaan Mustafa, commit `76aaa77df6ad` (bản 2.2.3).

Giấy phép gốc: **MIT** - nguyên văn ở `docs/LICENSE.txt`.

## Đã sửa những gì

Nội dung skill (thân file và các tệp đi kèm) **giữ nguyên bản gốc, không dịch**. Chỉ
frontmatter của `SKILL.md` được chỉnh cho khớp Naota:

- `description` được viết lại cho vừa trần 150 ký tự của router Naota (router cắt đúng
  ở 150 nên phần dư vốn mất im lặng). Mô tả gốc được chép xuống cuối file.
- Thêm `group` để trang Kỹ năng gom nhóm. Bỏ khối `metadata` riêng của ECC.
- `security-review` đổi thành `ecc-security-review` cho khỏi đè lệnh `/security-review`
  có sẵn của Claude Code.
- Mỗi `SKILL.md` có một dòng ghi nguồn ở cuối.

## Bảng đối chiếu

| Slug trong Naota | Đường dẫn gốc |
|---|---|
| `market-research` | `ECC/skills/market-research` |
| `competitive-platform-analysis` | `ECC/skills/competitive-platform-analysis` |
| `benchmark-methodology` | `ECC/skills/benchmark-methodology` |
| `competitive-report-structure` | `ECC/skills/competitive-report-structure` |
| `product-lens` | `ECC/skills/product-lens` |
| `investor-materials` | `ECC/skills/investor-materials` |
| `investor-outreach` | `ECC/skills/investor-outreach` |
| `lead-intelligence` | `ECC/skills/lead-intelligence` |
| `council` | `ECC/skills/council` |
| `customer-billing-ops` | `ECC/skills/customer-billing-ops` |
| `inventory-demand-planning` | `ECC/skills/inventory-demand-planning` |
| `returns-reverse-logistics` | `ECC/skills/returns-reverse-logistics` |

## Lưu ý trước khi dùng

ECC viết cho Claude Code, nên vài chỗ nhắc tới lệnh `/...`, hook, đường dẫn `~/.claude` hay
MCP (Exa, firecrawl, fal.ai, Context7) mà brain của bạn có thể chưa có. Thiếu thì bỏ qua
bước đó hoặc đấu MCP tương ứng ở trang Kết nối; phần phương pháp vẫn dùng được trên mọi
bộ não của Naota.
