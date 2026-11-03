---
name: Lên đơn TTS Dropship
description: Việc hằng ngày trên sàn TTS Dropship: tìm hàng, thêm vào giỏ, tách địa chỉ từ tin nhắn khách, tránh tạo khách trùng, báo giá ship, xem trước rồi mới lên đơn thật, theo dõi đơn và tiền về.
description_en: "Daily TTS dropship work: find products, add to cart, parse a customer's chat message, avoid duplicate customers, quote shipping, preview before placing the real order, track orders and payouts."
group: Bán hàng
---

# Lên đơn TTS Dropship

## Khi nào dùng

Khi người dùng dán một tin nhắn khách kiểu "Nguyễn Văn A 0912345678, 12 Lê Lợi, P.1, Q.1,
TPHCM, lấy 2 cái áo thun trắng size L" và muốn lên đơn trên sàn dropship.thitruongsi.com.
Cũng dùng khi họ hỏi "tìm giúp mẫu áo khoác lãi cao", "thêm mẫu này vào giỏ", "đơn của chị Lan
tới đâu rồi", "sản phẩm này lãi bao nhiêu", "tháng này tiền về bao nhiêu".

Không dùng cho sàn khác. Pancake POS, Shopify, TikTok Shop đều có kết nối riêng.

## Điều phải biết trước, vì nó quyết định cả quy trình

**Đơn đã tạo thì sàn KHÔNG cho sửa.** Sai một chữ trong địa chỉ là phải huỷ đơn rồi lên lại,
và huỷ nhiều lần thì ảnh hưởng uy tín tài khoản bán. Toàn bộ công sức nằm ở bước KIỂM TRƯỚC
KHI TẠO.

**Sàn cũng không cho sửa hay xoá khách hàng.** Gói tự chặn tạo khách trùng số điện thoại.

**Mỗi nhà cung cấp là một đơn riêng.** Giỏ có hàng của 3 shop thì ra 3 đơn, 3 phí ship. Nói
trước cho người dùng biết.

**Ba con số giá.** `dropship_price` là giá BẠN trả sàn (giá nhập), `market_price` là giá bán
gợi ý cho khách, `dropship_profit` = `market_price` - `dropship_price` là lãi gợi ý.

**Trên sàn này `city` là TỈNH/THÀNH, `province` là QUẬN/HUYỆN.** Tool đã lo việc đổi tên này.
Khi gọi `tts_customer_write`, cứ truyền `province` = tỉnh, `district` = quận, `ward` = phường.

## Quy trình lên đơn

Bảy bước, chạy đúng thứ tự.

**1. Tách địa chỉ.** Dán NGUYÊN đoạn tin nhắn vào `tts_customers` với `action=parse_address`.
Đọc phần `vanhanh_tim_thay`: nó so với danh mục tỉnh/quận/phường của chính sàn theo cụm từ nguyên
vẹn. Bộ tách của sàn (`san_tach_duoc`) chỉ để tham khảo: nó từng đọc "Quận 1" thành "Q. 12".
- `chac_chan=true`: dùng đúng các tên đó.
- Có `can_xac_nhan`, `ung_vien_quan` hay `ung_vien_phuong`: HỎI LẠI khách, đừng tự chọn.
- Số nhà, tên đường: tự đọc từ tin nhắn. Tên đường trùng tên phường là chuyện rất hay gặp.

**2. Tìm khách cũ.** `tts_customers` với `action=search`, `query` = SỐ ĐIỆN THOẠI. Có rồi thì
lấy `customer_id` và `address_id` trong `dia_chi_mac_dinh` (hoặc `cac_dia_chi`). Địa chỉ lần
này khác thì `tts_customer_write action=add_address`.

**3. Chưa có thì tạo khách.** `tts_customer_write` với `action=create`, `name`, `phone`,
`address1` (số nhà, đường), `province`, `district`, `ward`. Tool tự đối chiếu địa chỉ với
danh mục sàn và tự từ chối nếu số điện thoại đã có khách. Nó trả về `address_id` để dùng ở các
bước sau.

**4. Tìm hàng và chọn đúng phân loại.** `tts_products action=search` (muốn lãi cao thì
`sort_by=dropship_profit`), rồi `action=get` với `product_id` để xem từng variant (màu/size,
giá nhập, tồn kho). Lấy đúng `variants[].id` của phân loại khách muốn. Sai variant là giao
nhầm màu nhầm size.

**5. Thêm vào giỏ.** `tts_cart_update` với `items: [{product_id, variant_id, quantity,
dropship_selling_price}]`. Bỏ trống giá bán thì tool dùng giá gợi ý. Tool chặn giá bán thấp hơn
giá nhập. Đọc lại giỏ trả về để chắc số lượng đúng.

**6. Báo giá ship.** `tts_shipping_rates` với `customer_address_id` (bước 2 hoặc 3), `shop_id`
và `items` như bước 5. Chọn một mục trong `rates` (web sàn mặc định chọn mục đầu tiên).

**7. Xem trước rồi mới tạo.** Gọi `tts_create_order` KHÔNG có `confirm`, truyền:
`shop_id`, `customer_phone` (kèm `customer_address_id` nếu khách có nhiều địa chỉ),
`line_items` như bước 5, `shipping_rate` = nguyên mục đã chọn ở bước 6. Tool tự lấy
`cart_token`, tự kiểm variant, giá, tồn kho, rồi trả bản xem trước. **Đọc lại bằng lời** cho
người dùng: tên người nhận, số điện thoại, địa chỉ đầy đủ, từng món, phí ship, tổng khách trả,
lãi ước tính. Người dùng đồng ý thì gọi lại ĐÚNG các tham số đó kèm `confirm=true`.

Tên người nhận trong bản xem trước thiếu họ hay sai (khách tạo trước bản 1.1.1 hoặc tạo trên
web sàn) thì thêm `recipient_name` với tên đầy đủ, rồi xem trước lại. Không cần tạo lại khách.

Giỏ nhiều shop thì truyền mảng `orders`, mỗi mục một shop. Kết quả trả trạng thái từng đơn:
có đơn lỗi thì **chỉ lên lại đúng đơn đó** sau khi kiểm `tts_orders action=list`, vì các đơn đã
tạo là thật. Gọi lại y hệt một đơn vừa tạo thì tool tự chặn; khách đặt thêm thật thì mới truyền
`allow_repeat=true`.

Mặc định khách trả ship (cộng vào tiền thu hộ). Người dùng muốn tự trả ship cho khách thì
thêm `dropshipper_pays_shipping=true`, phí ship trừ vào lãi.

## Việc hằng ngày khác

- **Đơn đang chờ**: `tts_orders action=list buyer_status=wait_confirm` (hoặc `wait_pickup`,
  `in_transit`, `delivered`, `wait_rate`, `cancelled`). Tìm theo mã đơn hay tên khách bằng
  `query`.
- **Đơn tới đâu**: `tts_orders action=tracking order_id=...`.
- **Lãi thật của một đơn**: `tts_orders action=get`. Khối hoa hồng trong đó có tổng giá bán,
  tổng giá nhà cung cấp, thưởng, phí ship đã tài trợ và tổng lợi nhuận. Trả lời bằng con số
  đó, đừng nhân tay.
- **Tiền về**: `tts_finance action=income` (tổng quan) và `action=escrow` (từng đơn kèm ngày
  giải ngân). Tiền của đơn đã giao còn bị giữ tới khi đơn được đánh giá; mở khoá bằng
  `tts_order_action action=rate`, chỉ gửi được một lần.
- **Khuyến mãi của shop**: `tts_suppliers action=promotions`. Dùng `id` của nó trong
  `price_rule_ids` khi lên đơn.

Gói này cố ý không có tool rút tiền. Người dùng muốn rút thì vào ví trên web của sàn.

## Chỗ sai hay gặp

**Tin bộ tách địa chỉ của sàn.** Đừng. Dùng `vanhanh_tim_thay`, và hỏi lại khi có ứng viên.

**Gọi `tts_create_order` với `confirm=true` ngay lần đầu.** Đừng. Kể cả khi người dùng nói
"cứ lên đơn đi", vẫn đọc bản xem trước ra rồi hỏi một câu, mất năm giây và tránh một đơn phải
huỷ.

**Tạo khách mới mà không tìm trước.** Tool đã chặn trùng số điện thoại, nhưng vẫn tìm trước để
dùng lại đúng địa chỉ cũ.

**Đoán `variant_id`.** Luôn lấy từ `tts_products action=get`.

**Gửi lại lệnh tạo đơn khi thấy lỗi mạng.** Lỗi có chữ "KHÔNG BIẾT sàn đã nhận lệnh hay chưa"
nghĩa là đơn có thể đã nằm trên sàn. Kiểm `tts_orders action=list` trước, đừng gọi lại ngay.

**Kết luận "sàn đổi API" khi một tool lỗi.** Chạy `tts_health_check` trước. Nó phân biệt được
token hỏng, sàn đổi tên trường GraphQL, hay sàn đổi hẳn đường gọi.

Sàn đổi tên trường thì phần lớn **tự khỏi**: gói tự hỏi sàn lược đồ hiện tại, bỏ trường không
còn, lồng lại lớp bọc nếu có, thử lại và lưu bản sửa ra ngoài gói. Kết quả có dòng
`_vanhanh_tu_sua` nói nó đã sửa gì; báo lại cho người dùng một câu, đừng nuốt. Không tự khỏi thì
`tts_graphql action=introspect` để xem hình dạng thật, rồi `action=set` để ghi lại truy vấn.

## Token

Token sàn sống khoảng 3 ngày. Có `@refreshToken` trong kết nối thì gói tự gia hạn, kể cả khi
sàn bất ngờ báo token hỏng. Thấy `canh_bao` về token trong kết quả thì nhắc người dùng dán
thêm refresh token theo hướng dẫn:
https://github.com/lequydailb-dotcom/vanhanh-store/blob/main/huong-dan/tts-dropship.md

## Loop chạy nền

Không bao giờ để một loop tự gọi `tts_create_order`, `tts_cancel_order` hay `tts_order_action`,
kể cả khi kết nối đã ở mức Toàn quyền. Loop được phép đọc: theo dõi vận đơn, cảnh báo đơn treo
quá lâu ở `wait_confirm`, báo tiền sắp về. Việc lên đơn luôn cần một người nhìn vào bản xem
trước.
