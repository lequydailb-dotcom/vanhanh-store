# Gửi một gói vào kho

Gói trong kho **chạy trên máy người khác**, và gói bậc `code` chạy Python thật bên trong máy chủ
Naota của họ - đọc được mọi khoá API và mọi tệp mà Naota đọc được. Vì vậy mọi Pull Request đều
được đọc mã trước khi trộn, và phần lớn hướng dẫn dưới đây tồn tại để việc đọc đó nhanh và chắc.

## Các bước

1. Fork repo này.
2. Tạo `packs/<id>/` với `naota-pack.yaml` ở gốc. `id` phải **trùng đúng tên thư mục**, chỉ gồm
   chữ thường, số và `. - _`, và **bằng tiếng Anh** (`naota.crm`, không phải `naota.khach-hang-crm`).
   Tên thương hiệu như `naota.kiotviet` giữ nguyên. Tên hiển thị thì vẫn viết cả tiếng Việt lẫn tiếng Anh.
3. Đóng gói và lấy dấu vân tay:

       python tools/dong-goi.py <id>

   Lệnh in ra đường dẫn `.zip` trong `dist/` và chuỗi `sha256`.
4. Thêm một mục vào `packs[]` trong `index.json`, dùng `download.url` **tương đối**
   (`dist/<tên tệp>.zip`) và dán đúng `sha256` lệnh trên vừa in. Gói kết nối thì khai thêm
   `icon` trỏ vào logo **nằm trong gói** (`packs/<id>/assets/<tên>.png`): đó là logo hiện trên
   thẻ trong Kho cài đặt, và cũng là tệp khuôn connector trỏ tới qua `assets/<tên>.png`, nên
   hai chỗ không bao giờ lệch nhau.
5. Chạy trình kiểm trước khi gửi:

       python tools/kiem-tra.py

   Nó soi cấu trúc gói, phân loại quyền, và đối chiếu `.zip` với thư mục nguồn. CI chạy đúng
   lệnh này trên mọi Pull Request, nên chạy trước ở máy mình là biết ngay thay vì đợi.
6. Mở Pull Request. Trong phần mô tả, nói rõ **gói làm gì** và **vì sao cần quyền nó xin**.

Cả mã nguồn lẫn tệp `.zip` đều phải có trong PR. Thiếu một trong hai thì không review được: mã để
đọc, `.zip` để chạy thử.

## Gói của bạn sẽ bị đọc những gì

- **Mọi tệp `.py`.** Gói không có tệp `.py` vẫn có thể chạy mã: `transport: stdio` khiến Naota
  chạy `npx` với toàn bộ biến môi trường của máy chủ. Khai `command`, `args` hay `env` là gói
  thuộc bậc `code`, dù không một dòng Python nào.
- **Địa chỉ gói gọi ra ngoài.** Một connector dựng URL từ dữ liệu người dùng là chỗ phải giải
  thích rõ.
- **Trùng `id` với connector có sẵn.** Bị từ chối thẳng, không có ngoại lệ: một gói khai trùng
  `id` kèm `url_template` khác sẽ âm thầm bẻ hướng một kết nối **đang đăng nhập thật**.
- **Icon.** Phải nằm trong gói. Icon ở xa là một beacon nổ mỗi lần vẽ trang, tức lộ IP và nhịp
  dùng của người cài cho bạn. Dùng `.png`, `.webp` hoặc `.jpg` (256x256 là đủ), không dùng
  `.svg`: đường phục vụ ảnh của gói cố ý từ chối SVG.
- **Mô tả tool.** Nó đi thẳng vào danh sách công cụ của những engine đang cầm quyền chạy lệnh,
  nên mô tả gài chỉ dẫn cho mô hình là lý do từ chối.

## Phân loại quyền: chỗ dễ sai nhất

Naota xếp mỗi tool vào ba nhóm `read` / `write` / `danger`, khai trong `tool_meta` của khuôn
connector. Mức **Ghi nháp** của người dùng tự chạy được mọi thứ trong nhóm `write` mà không hỏi.

Điều phải biết: **Naota KHÔNG tự đoán ra `danger`.** Tool nào bạn không khai rõ thì cùng lắm nó
rơi vào `write` theo tên. Nên một tool xoá dữ liệu hay tiêu tiền mà bạn quên khai sẽ tự chạy ở
mức Ghi nháp, im lặng, cho tới lúc nó xoá thật.

`tools/kiem-tra.py` chặn hai lớp:

- **Đụng tới tiền** (mua, thanh toán, hoàn tiền, gia hạn, chuyển khoản): bắt buộc `danger`,
  không có ngoại lệ.
- **Phá huỷ hoặc tác động ra ngoài** (xoá, huỷ, gửi, đăng, chạy, khởi động lại): mặc định cũng
  bắt buộc `danger`. Nếu bạn đã cân nhắc và thấy trong dịch vụ CỤ THỂ này nó nhẹ - ví dụ xoá
  một dòng trong ghi chú cá nhân, hay huỷ một tác vụ chạy lại được - thì liệt kê tên tool đó
  vào `ghi_da_can_nhac` ở gốc khuôn:

      "ghi_da_can_nhac": ["delete_list_item", "restore_note"]

  Trường này Naota không đọc; nó chỉ để lại dấu vết rằng quyết định ấy là có chủ ý, cho người
  review sau đọc được. Đừng dùng nó để cho qua trình kiểm - dùng thế thì thà khai `danger`.

Khai `danger` thì khuôn phải có câu `risk` nói bằng lời thường chuyện gì có thể mất.

## MCP của bên thứ 3: đi theo bản chính thức

Luật kho: **bên thứ 3 có bản phát hành chính thức thì gói phải đi theo bản
đó**. Với connector chạy MCP qua `npx` hoặc `uvx`, nghĩa là:

- Lấy MCP từ kênh phát hành chính thức (npm, PyPI). Không chạy code thẳng từ GitHub
  (`git+https://...`): code trên nhánh `main` là code chưa ai phát hành.
- Viết tên gói kèm `@latest`, ví dụ `npx -y hostinger-api-mcp@latest` hay
  `uvx google-ads-mcp@latest`. Để trống phiên bản là CHƯA đủ: `npx` và `uvx` dùng lại bản đã
  tải, nên máy nào tải lần đầu ở bản nào là kẹt ở bản đó mãi.

Bên thứ 3 ra bản mới thì mọi máy chạy bản đó ở lần khởi động kế tiếp, không cần ra bản gói.
Hai ngoại lệ, khai bằng `ngoai_le_ban_chinh_thuc` ở gốc khuôn connector, một câu nói rõ vì sao:

- Bên thứ 3 chưa phát hành bản nào, nên chỉ có đường GitHub.
- Naota thôi đi theo bản gốc và tự giữ một bản riêng. Ví dụ duy nhất hiện có: Zalo trong app, từ
  Naota 1.0.0 chạy [`naota-zalo`](https://github.com/vuongtex/naota-zalo) (bản CLI riêng, ghim
  theo tag phát hành), chỉ thư viện `zca-js` bên dưới là còn đi theo bản chính thức.

`tools/kiem-tra.py` chặn mọi connector `npx`/`uvx` không theo luật này.

Bên thứ 3 chưa phát hành lên npm mà `npx -y github:...` cũng không chạy được (gói cần build
lúc cài, như KiotViet, Haravan), thì kho tự build MỘT lần từ một commit ghim và giữ tệp `.tgz`
trong `mcp/`. Connector chạy `npx -y --package=<URL tệp trong mcp/> <lệnh>`, kèm
`ngoai_le_ban_chinh_thuc`. Repo gốc, commit, sha256 và mọi chỗ kho sửa ghi trong
`mcp/nguon.json`; build lại bằng `python tools/mcp_dong_goi.py <tên>`. Không bao giờ ghi đè tệp
cũ: đổi commit là ra tệp mới và bản gói mới. Lý do đầy đủ ở đầu `tools/mcp_dong_goi.py`.

Không có MCP nào dùng được (cả bản cộng đồng cũng không: thiếu giấy phép, lấy token từ trình duyệt, gửi
token ra máy khác), thì kho tự viết một MCP nhỏ trong `mcp-nguon/<tên>/`, như `pancake-chat-mcp`. Luật
riêng: KHÔNG thư viện phụ thuộc (đọc hết được trong một lần), chỉ gọi đúng máy chủ của dịch vụ, không ghi
token ra log. `tools/mcp_dong_goi.py <tên>` đóng `.tgz` ra đúng một sha256, trình kiểm so từng tệp trong
`.tgz` với thư mục nguồn, và test của nó đặt ở `tests/<id gói>/` chạy chính tệp đã đóng gói.

Cái giá của luật là bản mới có thể mang **tool mới chưa ai phân loại**, và Naota xếp một tool
không khai, tên không chứa từ gợi ý ghi nào, vào nhóm **đọc** (vụ thật lúc đặt luật:
`workspace-mcp` 2.x thêm `run_script_function`). Vì vậy CI có thêm job `soi-ban-moi`, chạy mỗi
ngày: nó chạy thử bản mới nhất thật của từng MCP, phân loại tool thật bằng đúng hàm của Naota,
và đỏ khi có tool phá huỷ hay tiêu tiền chưa nằm ở nhóm `danger`. Thấy đỏ thì khai tool đó trong
`tool_meta` rồi ra bản gói mới. Chạy tay:

    NAOTA_OS_DIR=../naota python tools/soi-ban-moi.py

MCP **chính chủ chạy từ xa** (`transport: http`, ví dụ GitHub) không chạy thử được vì cần đăng
nhập. Nếu bên đó công bố danh sách tool trong mã nguồn mỗi bản phát hành, nối khuôn với nguồn đó
bằng một tệp `chinh-chu/<id>.json` (xem `chinh-chu/github.json` làm mẫu, lý do ở
`tools/chinh_chu.py`). Job `soi-ban-moi` khi ấy đọc bộ tool của bản phát hành mới nhất mỗi ngày,
áp cùng luật cộng nhãn đọc/ghi/phá huỷ của chính bên đó, và đỏ khi bộ tool khác bộ kho đã soát.
Đọc ghi chú phát hành, sửa `tool_meta` nếu cần, rồi ghi lại bộ đã soát:

    NAOTA_OS_DIR=../naota python tools/soi-ban-moi.py --chi-chinh-chu --ghi-da-soat

Ghi lại bộ đã soát không cần ra bản gói, vì `chinh-chu/` nằm ngoài `packs/`.

MCP dạng **cổng** (một tool chạy được mọi lệnh, như `execute` của Hostinger 2.x) thì phân loại
theo từng lệnh con bằng `call_rules`, xem khuôn `packs/naota.hostinger/` làm mẫu. Lệnh con
không có trong danh sách đọc phải rơi về `danger`, để lệnh bên thứ 3 thêm sau này không tự chạy.

## Điều gì bị từ chối

- `transport: internal` và `auth.type: qr` - hai đường riêng của lõi Naota, không khai bằng gói.
- Gói làm thay việc đã có MCP chính chủ. Đấu MCP đó vào còn hơn.
- Gói tự ý gửi dữ liệu người dùng đi đâu đó, kể cả "để thống kê".

## Test cho gói có mã

Plugin chạy bên trong máy chủ Naota và gọi module của lõi, nên test của nó đặt ở `tests/<id gói>/test_*.py`
(ngoài `packs/`, nên không vào tệp `.zip`) và chạy trên một bản checkout NAOTA:

    NAOTA_OS_DIR=../naota python tests/naota.zalo/test_zalo_read_images.py

CI chạy mọi tệp đó trên nhánh `main` của NAOTA ở mỗi Pull Request và mỗi ngày một lần, để lõi đổi mà
gói gãy thì biết ngay. Xem `tests/naota.zalo/` làm mẫu.

## Ra bản mới

Tăng `version` ở **cả hai** chỗ: manifest trong gói và mục trong `index.json`. Thêm tệp `.zip`
mới vào `dist/` (giữ tệp cũ lại, đừng ghi đè - người dùng cần tải được bản cũ), rồi đổi
`download.url` và `sha256`.

**Đổi mã gói** (Naota 1.1.0 trở lên): đổi tên thư mục và `id`, tăng `version`, và khai mã cũ ở
cả manifest lẫn mục danh mục:

    replaces:
      - naota.ma-cu

Máy đang cài mã cũ thấy gói mới như một bản cập nhật. Cài lên là Naota chuyển dữ liệu riêng của
plugin, năng lực trong brain và trạng thái bật sang mã mới rồi gỡ gói cũ. Plugin đổi tên thì đường
`/ext/<tên cũ>/` vẫn tới plugin mới. Đặt `compat.app: ">=1.1.0"`, vì bản cũ hơn không hiểu
`replaces` và sẽ cài gói mới nằm cạnh gói cũ.

Người đã cài sẽ thấy nút đổi thành **Có bản mới**. Naota **không tự cài đè một gói có mã**: mã
Python hay khuôn connector trong gói đổi thì người dùng phải mở ra xem rồi mới cài, nếu không chốt
chữ ký nội dung thành vô nghĩa. MCP của bên thứ 3 mà gói gọi tới thì khác: nó đi theo bản chính
thức mới nhất của bên đó (xem mục trên), không cần ra bản gói.
