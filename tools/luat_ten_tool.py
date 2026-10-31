"""Luật tên tool dùng chung cho `kiem-tra.py` (soi tên KHAI trong khuôn) và `soi-ban-moi.py`
(soi tên THẬT mà bản mới nhất của MCP trả về). Hai nơi phải dùng cùng một bộ luật, nên nó nằm ở
đây thay vì chép hai lần.
"""
import re


# ============================================================
# Tên tool nghe là biết KHÔNG hoàn tác được, hoặc tiêu tiền thật.
#
# Danh sách này cố ý RỘNG và cố ý gây phiền: một cái tên bị bắt oan thì tác giả gói khai lại
# một dòng là xong, còn một cái lọt lưới thì người dùng mất dữ liệu hoặc mất tiền. Đổi cân
# bằng đó theo hướng ngược lại là đổi sai chiều.
# ============================================================
# TIỀN, hoặc mất mát không dựng lại được bằng thao tác thường. Không có ngoại lệ: một tool tên
# kiểu này mà nằm ở nhóm ghi nghĩa là mức "Ghi nháp" tiêu được tiền của người dùng.
TIEN = [r"purchase", r"buy", r"pay", r"payment", r"checkout", r"charge", r"refund",
        r"invoice", r"billing", r"subscribe", r"renew", r"transfer"]

# PHÁ HUỶ hoặc gây tác động ra ngoài. Khác nhóm trên ở chỗ mức độ THẬT SỰ phụ thuộc dịch vụ:
# xoá một dòng trong ghi chú Google Keep rơi vào thùng rác, còn xoá một bản ghi DNS thì hạ cả
# website. Máy không phân biệt được, người viết gói thì có.
#
# Nên luật ở đây là: mặc định CHẶN, và tác giả gói gỡ chặn bằng cách liệt kê tên tool vào
# `ghi_da_can_nhac` của khuôn. Không phải để cho dễ - mà để quyết định đó có tên, nằm trong
# dữ liệu, và người review đọc được. Một cảnh báo in ra rồi trôi đi thì không ai đọc.
PHA = [r"delete", r"remove", r"destroy", r"drop", r"purge", r"wipe", r"erase",
       r"order", r"execute", r"run", r"trigger", r"deploy", r"restart", r"reboot",
       r"reset", r"send", r"publish", r"post", r"broadcast", r"cancel", r"restore",
       r"revoke", r"migrate", r"rotate"]

# Tên CHỨA một từ trên nhưng thật ra chỉ đọc. Liệt kê từng cái, không nới thành mẫu chung -
# nới một lần là thủng cả hàng rào.
THA = {
    "get_order", "list_orders", "search_orders", "get_invoice", "list_invoices",
    "get_payment", "list_payments", "get_execution", "search_executions", "list_executions",
    "get_deployment", "list_deployments", "get_post", "list_posts", "search_posts",
    "get_subscription", "list_subscriptions", "get_transfer", "list_transfers",
    # KiotViet: hoá đơn bán hàng là nguồn doanh thu, chỉ GET (kiotviet-mcp, tools/invoices.ts).
    "kiotviet_invoices_list", "kiotviet_invoices_get_by_id", "kiotviet_invoices_get_by_code",
    # Sapo: xem phiếu hoàn tiền của một đơn, chỉ GET (sapo-omni-mcp, tools/orders/refunds.ts).
    "list_refunds",
}


def _khop(ten, mau):
    t = str(ten or "").lower()
    if t in THA or "*" in t or "?" in t:
        return False
    return any(re.search(p, t) for p in mau)
