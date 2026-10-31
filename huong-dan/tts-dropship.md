# Kết nối TTS Dropship với Naota

Làm một lần, khoảng 3 phút. Xong là bạn nhờ Naota tìm hàng, thêm vào giỏ, tạo khách và lên đơn
trên dropship.thitruongsi.com bằng lời nói thường.

Sàn TTS không phát hành API key, nên Naota dùng chính phiên đăng nhập của bạn trên trình duyệt.
Bạn sẽ copy **2 chuỗi** từ trình duyệt rồi dán vào Naota:

| Chuỗi | Dán vào ô | Để làm gì |
|---|---|---|
| `@publicToken` | Token đăng nhập | Cho Naota vào tài khoản của bạn |
| `@refreshToken` | Refresh token | Cho Naota **tự gia hạn**, khỏi phải làm lại mỗi 3 ngày |

Cần: máy tính có Chrome, Edge hoặc Cốc Cốc. Điện thoại không làm được bước này.

---

## Bước 1. Đăng nhập sàn

Mở [dropship.thitruongsi.com](https://dropship.thitruongsi.com) và đăng nhập như bình thường.

## Bước 2. Copy token đăng nhập

1. Đang ở trang dropship.thitruongsi.com, bấm **F12** (máy Mac: `Cmd + Option + J`).
2. Chọn thẻ **Console** ở khung vừa mở.
3. Dán dòng dưới đây vào rồi bấm **Enter**:

   ```
   copy(localStorage.getItem('@publicToken'))
   ```

   Nếu Chrome báo không cho dán, gõ tay `allow pasting`, bấm Enter, rồi dán lại dòng trên.

4. Không thấy gì hiện ra là **đúng**. Chuỗi đã nằm trong bộ nhớ copy của máy.

## Bước 3. Dán vào Naota

1. Mở Naota, vào trang **Kết nối**, chọn **TTS Dropship (thitruongsi.com)**.
   Đã kết nối từ trước thì bấm **Sửa**.
2. Bấm vào ô **Token đăng nhập (@publicToken)** rồi dán (`Ctrl + V`).
   Chuỗi rất dài, bắt đầu bằng `eyJ`. Dán nguyên văn, đừng cắt bớt.

## Bước 4. Copy refresh token (đừng bỏ qua)

1. Quay lại tab TTS Dropship, vẫn ở thẻ **Console**, dán dòng này rồi **Enter**:

   ```
   copy(localStorage.getItem('@refreshToken'))
   ```

2. Qua Naota, dán vào ô **Refresh token (@refreshToken)**.

Token đăng nhập của sàn chỉ sống khoảng 3 ngày. Có refresh token thì Naota tự xin token mới
trước khi hết hạn, giống hệt cách trang web của sàn tự làm. Thiếu nó thì cứ 3 ngày bạn phải
quay lại làm từ Bước 2.

## Bước 5. Lưu và kiểm tra

1. Ô **Địa chỉ gia hạn token**: để trống. Naota đã biết sẵn địa chỉ của sàn.
2. Bấm **Lưu** (hoặc **Kết nối**).
3. Nhắn Naota: **"Kiểm tra kết nối TTS Dropship"**.

Naota sẽ thử từng việc (hồ sơ, giỏ hàng, khách hàng, tìm hàng, đơn hàng) rồi báo việc nào
chạy, việc nào hỏng, token còn bao lâu và có tự gia hạn được không.

---

## Chọn mức quyền

Trang Kết nối có 3 mức. Chọn theo việc bạn muốn Naota làm:

| Mức | Naota làm được |
|---|---|
| Chỉ đọc (mặc định) | Tìm hàng, xem giỏ, xem khách, xem đơn, xem tiền về |
| Ghi nháp | Thêm trên + thêm/sửa giỏ hàng, tạo khách mới |
| Toàn quyền | Thêm trên + **lên đơn thật**, huỷ đơn, đánh giá đơn |

Muốn Naota lên đơn hộ thì cần **Toàn quyền**. Kể cả ở mức này, mỗi đơn Naota đều đọc bản xem
trước cho bạn và chỉ tạo khi bạn đồng ý.

---

## Nhờ Naota làm gì mỗi ngày

Nói bình thường như nhắn cho trợ lý. Vài câu mẫu:

**Tìm hàng**
- "Tìm áo khoác chống nắng lãi cao trên TTS"
- "Mẫu này có màu gì, size gì, còn bao nhiêu cái?"

**Lên đơn từ tin nhắn khách** (dán nguyên tin nhắn)
- "Lên đơn: Nguyễn Văn A 0912345678, 12 Lê Lợi, P. Bến Nghé, Q.1, TPHCM, lấy 2 áo khoác đen size L"

**Theo dõi**
- "Có đơn nào đang chờ xác nhận không?"
- "Đơn của chị Lan tới đâu rồi?"
- "Đơn #DS5001 lãi bao nhiêu?"
- "Tháng này tiền về bao nhiêu, khi nào rút được?"

### Naota lên đơn thế nào

1. **Tách địa chỉ** từ tin nhắn và đối chiếu với danh mục tỉnh, quận, phường của chính sàn.
   Chỗ nào không chắc (ví dụ tin nhắn chỉ ghi "Thủ Đức" mà sàn có cả TP. Thủ Đức lẫn Q. Thủ
   Đức) thì Naota hỏi lại chứ không đoán.
2. **Tìm khách theo số điện thoại.** Có rồi thì dùng lại. Chưa có mới tạo. Sàn không cho xoá
   khách, nên Naota tự chặn việc tạo trùng.
3. **Tìm hàng** và lấy đúng mã màu, size.
4. **Thêm vào giỏ**, kiểm giá bán không thấp hơn giá nhập.
5. **Báo giá ship** tới địa chỉ của khách.
6. **Đọc bản xem trước**: tên, số điện thoại, địa chỉ, từng món, phí ship, tổng khách trả,
   lãi ước tính. Bạn đồng ý thì Naota mới tạo đơn thật.

Đơn đã tạo thì sàn **không cho sửa**, sai là phải huỷ rồi lên lại. Vì vậy hãy đọc kỹ bản xem
trước. Gọi lại y hệt một đơn vừa tạo thì Naota tự chặn để khỏi ra hai đơn.

Giỏ có hàng của 3 nhà cung cấp thì ra 3 đơn, 3 phí ship. Đây là cách sàn tính, không phải lỗi.

---

## Gặp lỗi thì làm gì

**"Token không đọc được hạn dùng"**
Bạn dán thiếu hoặc dán nhầm ô. Làm lại Bước 2 và 3.

**"Sàn TTS từ chối token" hoặc "token đã hết hạn"**
Có thể bạn chưa dán refresh token, hoặc đã đăng xuất hay đổi mật khẩu trên sàn. Đăng nhập lại
sàn rồi làm lại Bước 2 tới Bước 5, nhớ dán cả hai chuỗi.

**Tìm hàng không ra kết quả**
Nhắn "Kiểm tra kết nối TTS Dropship". Nếu phần tìm hàng báo lỗi về tên trường, Naota thường
tự sửa ở lần gọi sau. Sàn TTS không có tài liệu API chính thức nên họ có thể đổi bất cứ lúc
nào, và gói được làm để tự thích nghi khi điều đó xảy ra.

**Không dùng được thẻ Console**
Cách khác: F12, chọn thẻ **Application** (Firefox: **Storage**), mở **Local Storage** >
`https://dropship.thitruongsi.com`, tìm dòng `@publicToken` và `@refreshToken`, bấm vào từng
dòng rồi copy giá trị ở khung bên dưới.

---

## Bảo mật

- Hai chuỗi này mở được tài khoản bán hàng của bạn. Coi nó như mật khẩu, **không gửi cho ai**,
  kể cả người tự nhận là hỗ trợ của sàn.
- Naota mã hoá token trước khi lưu và không ghi token vào nhật ký.
- Gói này **không có chức năng rút tiền**. Muốn rút tiền thì vào ví trên web của sàn.
- Muốn thu hồi quyền: xoá kết nối TTS Dropship trong trang Kết nối của Naota. Nghi token bị lộ
  thì đổi mật khẩu tài khoản sàn.
