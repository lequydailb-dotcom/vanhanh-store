---
type: workflow
name: Bẻ bài dài thành chuỗi post
slug: bai-dai-thanh-chuoi-post
status: active
description: Từ một bài dài hoặc một tài liệu, tách thành chuỗi post đăng dần, mỗi
  post đứng một mình vẫn đọc được.
steps:
- agent: nd-goc-nhin
  task: 'Đọc nội dung dài sau và tách thành 5-7 ý, mỗi ý đủ sức thành một bài đăng
    riêng:


    {{input}}


    Với mỗi ý, ghi người đọc, nỗi đau, lời hứa và góc tiếp cận. Sắp xếp theo thứ tự
    nên đăng và nói vì sao thứ tự đó.'
- agent: nd-viet-bai
  task: 'Viết trọn bộ bài đăng theo dàn ý dưới đây, mỗi ý một bài:


    {{prev}}


    Mỗi bài phải đứng một mình đọc được, không bắt người đọc phải xem bài trước. Nhưng
    bài sau có thể nhắc lại bài trước một câu.'
  verify_agent: nd-kiem-chung
  max_retries: 2
updated: '2026-09-05'
---

Từ một bài dài hoặc một tài liệu, tách thành chuỗi post đăng dần, mỗi post đứng một mình vẫn đọc được.
