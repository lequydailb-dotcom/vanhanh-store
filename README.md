# Kho cài đặt Naota

Trợ lý, kỹ năng, quy trình, công cụ và kết nối làm sẵn cho [NAOTA](https://github.com/vuongtex/naota).

Naota đọc thẳng `index.json` trong repo này, nên **thêm một mục ở đây là mọi máy đang chạy Naota
thấy ngay** - không phải chờ bản cập nhật nào cả. Đó là toàn bộ lý do kho tách ra thành một repo
riêng.

## Người dùng Naota

Không cần làm gì với repo này. Mở Naota, vào tab **Kho cài đặt** trên bất kỳ trang năng lực nào
(Trợ lý, Kỹ năng, Quy trình, Plugin, Kết nối), rồi bấm **Cài đặt**.

Naota tải gói về, **mở ra cho bạn xem bên trong có gì rồi mới hỏi**. Gói có chứa mã Python thì
màn hình xác nhận hiện khối cảnh báo đỏ nói thẳng điều đó, kèm tên từng tệp mã, và gói cài xong
ở trạng thái tắt cho tới khi bạn bật.

Kho không tới được cũng không sao: gói đã cài chạy bình thường, và bạn vẫn cài được từ tệp `.zip`.

## Bố cục repo

    index.json          danh mục - thứ Naota đọc
    packs/<id>/         MÃ NGUỒN từng gói, để ai cũng đọc được trước khi cài
    packs/<id>/assets/  logo của gói: thẻ trong Kho cài đặt và trang Kết nối cùng dùng tệp này
    dist/<id>-<ver>.zip tệp Naota thật sự tải về
    huong-dan/<tên>.md  hướng dẫn cho người dùng, trang Kết nối trỏ link tới đây
    mcp/                MCP bên thứ 3 chưa lên npm, kho build từ commit ghim (xem mcp/nguon.json)
    mcp-nguon/<tên>/    mã nguồn MCP kho tự viết khi không có MCP nào dùng được
    tools/dong-goi.py   đóng gói một thư mục thành .zip và in dấu vân tay
    theo-goc/<id>.json  gói THEO REPO GỐC: repo GitHub của tác giả và thư mục skill chép về
    tools/theo-goc.py   chép nguyên văn từ repo gốc, mỗi ngày CI chạy lại để lấy bản mới

Mã nguồn nằm ngay cạnh tệp phát hành là có chủ ý: gói **chạy được mã Python trong máy chủ Naota
của bạn**, nên bạn phải đọc được nó mà không cần tải gì về trước.

## Repo khuyên dùng (theo repo gốc)

Một số gói không phải bản chụp mà **theo repo gốc**: skill chép nguyên văn từ repo GitHub của tác
giả, không dịch, không sửa. Mỗi ngày job `Theo repo gốc` so lại, repo gốc đổi thì gói lên một bản
vá và Naota báo trong chuông. Đổi chữ thì vào thẳng kho; đổi tệp mã (script) thì thành một Pull
Request chờ chủ kho đọc. Trong Naota, các gói này nằm ở mục **Repo khuyên dùng** của Store.

Thêm một repo: viết `theo-goc/<id>.json` (xem hai tệp có sẵn), chạy `python tools/theo-goc.py <id>`,
rồi `python tools/kiem-tra.py`.
Repo để skill thành tệp `.md` phẳng thay vì thư mục có `SKILL.md` (như FlowKit) thì khai
`"phang": true` trong mục `chep`, xem `theo-goc/naota.flowkit.json`.

Repo chứa **agent** thay vì skill (như agency-agents) thì khai `"den": "agents"`, xem
`theo-goc/naota.agency-agents.json`. Thân prompt giữ nguyên văn, phần đầu tệp thêm vài khoá để Naota
đọc được, tên và mô tả tiếng Việt lấy từ `theo-goc/dich/<id>.json`. Khai thêm `"tach"` thì mỗi agent
còn thành một gói lẻ trong tab Agent của Store (cài từng cái), cập nhật cùng lượt với gói gộp.

## Muốn đóng góp một gói

Xem [CONTRIBUTING.md](CONTRIBUTING.md). Tóm tắt: mở Pull Request kèm mã nguồn, tệp `.zip` và một
mục trong `index.json`. Mọi gói đều **được người phát hành kho đọc mã trước khi trộn vào**.

## Định dạng

Định dạng `index.json` và cách viết một gói: xem
[docs/dev/pack-store-index.md](https://github.com/vuongtex/naota/blob/main/docs/dev/pack-store-index.md)
trong repo NAOTA.
