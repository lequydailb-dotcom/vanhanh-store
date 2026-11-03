---
name: "continuous-agent-loop"
description: "Run a continuous autonomous agent loop with quality gates, eval checks and recovery controls when a step fails."
group: "ECC · AI agents"
---

# Continuous Agent Loop

This is the v1.8+ canonical loop skill name. It supersedes `autonomous-loops` while keeping compatibility for one release.

## Loop Selection Flow

```text
Start
  |
  +-- Need strict CI/PR control? -- yes --> continuous-pr
  |
  +-- Need RFC decomposition? -- yes --> rfc-dag
  |
  +-- Need exploratory parallel generation? -- yes --> infinite
  |
  +-- default --> sequential
```

## Combined Pattern

Recommended production stack:
1. RFC decomposition (`ralphinho-rfc-pipeline`)
2. quality gates (`plankton-code-quality` + `/quality-gate`)
3. eval loop (`eval-harness`)
4. session persistence (`nanoclaw-repl`)

## Failure Modes

- loop churn without measurable progress
- repeated retries with same root cause
- merge queue stalls
- cost drift from unbounded escalation

## Recovery

- freeze loop
- run `/harness-audit`
- reduce scope to failing unit
- replay with explicit acceptance criteria

---

*Nguồn: [ECC](https://github.com/affaan-m/ECC) của Affaan Mustafa - `ECC/skills/continuous-agent-loop` - giấy phép MIT.*
*Đã sửa để chạy trên VANHANH: `description` được viết lại còn ≤150 ký tự cho router của Vanhanh; `group` được thêm cho trang Kỹ năng của Vanhanh. Nội dung skill giữ nguyên bản gốc.*

*Mô tả gốc:*

> Patterns for continuous autonomous agent loops with quality gates, evals, and recovery controls. Use when running an agent loop that must self-check, gate on evals, and recover from failures.
