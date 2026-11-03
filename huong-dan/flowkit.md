# Dùng FlowKit với Vanhanh

[FlowKit](https://github.com/crisng95/flowkit) là bộ công cụ làm video AI bằng Google Flow (Veo 3,
Omni): từ ý tưởng, kịch bản, nhân vật, hình cảnh, clip 8 giây, lồng tiếng, nhạc, ghép phim tới
thumbnail và đăng YouTube.

Gói **FlowKit** trong Kho cài đặt chỉ mang **41 skill** (công thức làm việc) vào Vanhanh. Skill gọi
tới máy chủ FlowKit chạy trên chính máy bạn, nên bạn cần cài FlowKit một lần theo các bước dưới.
Chưa cài thì skill vẫn hiện trong Vanhanh nhưng không tạo được hình hay video.

## Cần chuẩn bị

- Máy Mac hoặc Linux. Windows thì dùng [WSL](https://learn.microsoft.com/vi-vn/windows/wsl/install).
- Python 3.10 trở lên, ffmpeg, trình duyệt Chrome.
- Một tài khoản Google dùng được [Google Flow](https://flow.google.com/).

## Bước 1. Tải FlowKit về máy

```bash
git clone https://github.com/crisng95/flowkit.git ~/flowkit
```

```bash
cd ~/flowkit && ./setup.sh
```

Lệnh `setup.sh` tự kiểm và cài Python, ffmpeg, môi trường ảo và các thư viện cần thiết.

## Bước 2. Cài tiện ích Chrome

1. Mở `chrome://extensions`, bật **Developer mode** (Chế độ nhà phát triển).
2. Bấm **Load unpacked** (Tải tiện ích đã giải nén), chọn thư mục `~/flowkit/extension`.
3. Mở [flow.google.com](https://flow.google.com/), đăng nhập và **để tab đó mở** suốt lúc làm video.
   Chỉ trang Flow mới ký được yêu cầu, nên tắt tab là FlowKit dừng.

## Bước 3. Tạo dự án Flow và chạy máy chủ

1. Trong giao diện Flow, tạo một dự án mới, rồi chép mã dự án (chuỗi dạng
   `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) trên thanh địa chỉ.
2. Chạy máy chủ FlowKit:

```bash
cd ~/flowkit && source venv/bin/activate && FLOW_PROJECT_ID=<mã dự án> python -m agent.main
```

3. Kiểm tra (mở một cửa sổ dòng lệnh khác):

```bash
curl http://127.0.0.1:8100/health
```

Thấy `"extension_connected": true` là xong.

## Bước 4. Cài gói trong Vanhanh

1. Mở Vanhanh, vào **Kỹ năng**, tab **Kho cài đặt**, mục **Repo khuyên dùng**.
2. Chọn **FlowKit: Làm video AI bằng Google Flow**, bấm **Cài đặt**.
3. Khi làm việc, cho Vanhanh chạy lệnh **trong thư mục `~/flowkit`**: nhiều skill gọi script có sẵn
   trong repo (ví dụ `scripts/`, `youtube/`).

Rồi nói với Vanhanh bằng lời thường, ví dụ: "Làm cho mình video 3 cảnh về chú mèo phi hành gia, khổ dọc,
phong cách hoạt hình 3D". Vanhanh sẽ dùng `fk-pipeline` để đi hết các bước, hoặc bạn gọi từng skill như
`fk-create-project`, `fk-gen-images`, `fk-gen-videos`, `fk-concat`.

Gặp lỗi gì thì bảo Vanhanh dùng `fk-doctor`: skill này biết hết các lỗi thường gặp và cách sửa.

## Lưu ý về tài khoản Google

Tác giả FlowKit ghi nhận một số tài khoản bị Google chặn tạo video trong Flow sau khi thử FlowKit.
Nên:

- Dùng **tài khoản Google phụ**, không dùng tài khoản chính.
- Gặp lỗi `PUBLIC_ERROR_UNUSUAL_ACTIVITY` thì **dừng lại**, đừng cố chạy tiếp. FlowKit tự nghỉ 1 giờ.

## Cập nhật

Gói đi theo repo gốc: mỗi ngày kho so lại với FlowKit, có bản mới thì Vanhanh báo trong chuông, bạn
bấm **Cập nhật**. Phần máy chủ FlowKit trên máy bạn thì tự cập nhật:

```bash
cd ~/flowkit && git pull && ./setup.sh
```
