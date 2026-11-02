# Nguồn của gói `naota.ecc-engineering-team`

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
| `ecc-planner` (Người lập kế hoạch) | `ECC/agents/planner.md` |
| `ecc-architect` (Kiến trúc sư phần mềm) | `ECC/agents/architect.md` |
| `ecc-code-reviewer` (Người review code) | `ECC/agents/code-reviewer.md` |
| `ecc-security-reviewer` (Người soát bảo mật) | `ECC/agents/security-reviewer.md` |
| `ecc-build-error-resolver` (Người sửa lỗi build) | `ECC/agents/build-error-resolver.md` |
| `ecc-code-simplifier` (Người đơn giản hoá code) | `ECC/agents/code-simplifier.md` |
| `ecc-silent-failure-hunter` (Người săn lỗi bị nuốt) | `ECC/agents/silent-failure-hunter.md` |
| `ecc-performance-optimizer` (Người tối ưu hiệu năng) | `ECC/agents/performance-optimizer.md` |
| `ecc-database-reviewer` (Người review database) | `ECC/agents/database-reviewer.md` |
| `ecc-python-reviewer` (Người review Python) | `ECC/agents/python-reviewer.md` |
| `ecc-typescript-reviewer` (Người review TypeScript) | `ECC/agents/typescript-reviewer.md` |
| `ecc-react-reviewer` (Người review React) | `ECC/agents/react-reviewer.md` |
| `ecc-tdd-guide` (Người dẫn TDD) | `ECC/agents/tdd-guide.md` |
| `ecc-refactor-cleaner` (Người dọn code chết) | `ECC/agents/refactor-cleaner.md` |
| `ecc-doc-updater` (Người cập nhật tài liệu) | `ECC/agents/doc-updater.md` |
| `ecc-e2e-runner` (Người chạy test E2E) | `ECC/agents/e2e-runner.md` |
| `ecc-docs-lookup` (Người tra tài liệu) | `ECC/agents/docs-lookup.md` |

## Lưu ý trước khi dùng

ECC viết cho Claude Code, nên vài chỗ nhắc tới lệnh `/...`, hook, đường dẫn `~/.claude` hay
MCP (Exa, firecrawl, fal.ai, Context7) mà brain của bạn có thể chưa có. Thiếu thì bỏ qua
bước đó hoặc đấu MCP tương ứng ở trang Kết nối; phần phương pháp vẫn dùng được trên mọi
bộ não của Naota.
