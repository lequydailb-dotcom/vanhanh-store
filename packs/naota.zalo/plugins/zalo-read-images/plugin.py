"""Plugin of the naota.zalo store pack: read the IMAGES people post in a Zalo group.

Why this exists: the Zalo MCP alone cannot read images in group chats. There are three gaps stacked on top of each other:
  1. A group photo arrives with `msgType: "chat.photo"`, which is not on the MCP's auto-download list (`image`, `video`...), so it is
     never fetched. The buffered message only carries the CDN link.
  2. `zalo_view_media` downloads to `~/.zalo-agent-cli/media/` (outside the brain, so the brain's file tools refuse it), pops the image
     open in the server machine's own viewer (a window on Windows, an error on a VPS), and answers with a bare path.
  3. The hub only forwards text, and the six API engines never send image input, so even a path inside the brain shows them nothing.
On top of that the MCP buffer forgets everything after 2 hours and only holds what arrived since the MCP process started.

What this tool does instead:
  - asks Zalo itself for the group's recent messages through the same CLI the other Zalo plugins rerun (`group history`, see
    `server/zalo_cli.py`), so it is not bounded by the MCP buffer; for a private chat (no group history command) or when the CLI fails it
    falls back to the MCP buffer;
  - downloads each photo into `attachments/zalo/<thread>/` of the brain, so it can be embedded in chat and opened by any engine;
  - lets ChatGPT on the signed-in plan look at the photos and describe them (`server/image_vision.py`), so engines without eyes still
    learn what is in them. Claude Code and Codex can skip that and open the file themselves.

`min_mode: safe`: it writes files into the brain (and spends ChatGPT quota when describing), it sends nothing to Zalo.
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

import image_gen
import image_vision
import zalo_cli

DEFAULT_COUNT = 30            # recent messages scanned for photos
MAX_COUNT = 100               # `group history -n` beyond this is slow and rarely what was meant
DEFAULT_IMAGES = 4
MAX_IMAGES = 8
MAX_BYTES = image_gen.MAX_REF_BYTES     # same cap ChatGPT accepts, so every saved photo can also be described
DOWNLOAD_TIMEOUT = 60
MAX_REDIRECTS = 3
HISTORY_TIMEOUT = 60
_EXT_BY_TYPE = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.IGNORECASE)
_SAFE_ID = re.compile(r"[^0-9A-Za-z_-]")


# ============================================================
# Reading messages (pure, tested without network)
# ============================================================
def _content_dict(content: Any) -> dict:
    """Attachment content as a dict. Text messages carry a plain string; some payloads wrap the object as a JSON string."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str) and content.strip().startswith("{"):
        try:
            got = json.loads(content)
            return got if isinstance(got, dict) else {}
        except ValueError:
            return {}
    return {}


def is_photo_type(msg_type: Any) -> bool:
    t = str(msg_type or "").lower()
    return "photo" in t or t in ("image", "chat.image")


def photo_url(content: Any) -> str:
    """Best link to a photo: `href` (full size), then the HD link inside `params`, then the thumbnail."""
    c = _content_dict(content)
    for k in ("href", "hdUrl", "normalUrl", "url"):
        v = str(c.get(k) or "").strip()
        if v.startswith("http"):
            return v
    params = _content_dict(c.get("params"))
    for k in ("hd", "rawUrl", "url"):
        v = str(params.get(k) or "").strip()
        if v.startswith("http"):
            return v
    v = str(c.get("thumb") or "").strip()
    return v if v.startswith("http") else ""


def _caption(content: Any) -> str:
    c = _content_dict(content)
    for k in ("title", "description"):
        v = str(c.get(k) or "").strip()
        if v and not v.startswith("{") and not v.startswith("http"):
            return v[:500]
    return ""


def _ms(v: Any) -> int:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return 0
    return n if n > 10**11 else n * 1000      # seconds -> ms


def _messages(data: Any) -> list:
    msgs = data.get("messages") if isinstance(data, dict) else None
    return msgs if isinstance(msgs, list) else []


def photos_from_history(data: Any) -> List[dict]:
    """Photos in a `group history --json` answer, oldest first."""
    out = []
    for m in _messages(data):
        if not isinstance(m, dict) or not is_photo_type(m.get("msgType")):
            continue
        url = photo_url(m.get("content"))
        if not url:
            continue
        out.append({"message_id": str(m.get("msgId") or m.get("cliMsgId") or ""),
                    "sender_id": str(m.get("fromUid") or ""), "sender_name": "",
                    "is_self": bool(m.get("isSelf")), "ts": _ms(m.get("timestamp")),
                    "caption": _caption(m.get("content")), "url": url})
    out.sort(key=lambda p: p["ts"])
    return out


def photos_from_buffer(data: Any) -> List[dict]:
    """Photos in a `zalo_get_messages` answer of the MCP (normalized messages with `attachment.url`), oldest first."""
    out = []
    for m in _messages(data):
        if not isinstance(m, dict):
            continue
        att = m.get("attachment") if isinstance(m.get("attachment"), dict) else {}
        if not (is_photo_type(m.get("type")) or is_photo_type(att.get("type"))):
            continue
        url = str(att.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        cap = str(att.get("description") or "").strip()
        out.append({"message_id": str(m.get("id") or ""), "sender_id": str(m.get("senderId") or ""),
                    "sender_name": str(m.get("senderName") or ""), "is_self": False, "ts": _ms(m.get("timestamp")),
                    "caption": "" if cap.startswith(("{", "http")) else cap[:500], "url": url})
    out.sort(key=lambda p: p["ts"])
    return out


def pick(photos: List[dict], message_id: str, limit: int) -> List[dict]:
    """One named message, or the newest `limit` photos (kept oldest first so they read in order)."""
    if message_id:
        return [p for p in photos if p["message_id"] == message_id]
    return photos[-limit:] if limit > 0 else []


def url_allowed(url: str) -> bool:
    """Only https, and never a local or private address: the link comes from a chat message, so it is untrusted input."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        ipaddress.ip_address(host)
        return False                    # Zalo's CDN is always a name; a literal IP is not a Zalo photo
    except ValueError:
        return True


def extension(url: str, content_type: str = "") -> str:
    ct = str(content_type or "").split(";")[0].strip().lower()
    if ct in _EXT_BY_TYPE:
        return _EXT_BY_TYPE[ct]
    m = _EXT_RE.search(urlparse(url).path or "")
    if m:
        e = m.group(1).lower()
        return ".jpg" if e == "jpeg" else "." + e
    return ".jpg"


def folder_for(vault_root: Optional[str], thread_id: str) -> Tuple[Path, Path]:
    """(brain root, attachments/zalo/<thread>/). The thread id is reduced to safe characters, so it can never climb out."""
    vault = image_gen._resolve_vault(vault_root)
    safe = _SAFE_ID.sub("_", str(thread_id or ""))[:64] or "unknown"
    return vault, image_gen._attachments_dir(vault) / "zalo" / safe


def _stamp(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M") if ts_ms else ""


# ============================================================
# Touching the world (each one replaceable in tests)
# ============================================================
async def fetch_history(conn: dict, thread_id: str, count: int) -> Tuple[bool, Any, str]:
    return await zalo_cli.run_cli(conn, ["group", "history"], [thread_id], ["-n", str(count)], timeout=HISTORY_TIMEOUT)


async def fetch_buffer(conn: dict, thread_id: str, count: int) -> Tuple[bool, Any, str]:
    """Messages the MCP buffered for this thread (private chats, or when the CLI cannot answer)."""
    try:
        import zalo_personal_channel as zc
        full = zc.ket_noi_theo_id(conn["id"])
        if not full:
            return False, None, "kết nối Zalo này chưa bật"
        data = await zc._goi(full, "zalo_get_messages", {"threadId": thread_id, "since": 0, "limit": max(1, min(count, 100))})
        return True, data, ""
    except Exception as e:      # noqa: BLE001 - a fallback that fails is reported, not raised
        return False, None, f"{type(e).__name__}: {e}"


def sender_names(conn: dict, thread_id: str) -> dict:
    """uid -> name of people who have written in this chat, from Naota's own inbox (instant, no network)."""
    try:
        import conversations
        rows = conversations.group_speakers(f"zalo_personal:{conn['id']}", thread_id)
    except Exception:      # noqa: BLE001 - names are a nicety; the photos still come back without them
        return {}
    return {str(r["uid"]): str(r["name"]) for r in rows if r.get("uid")}


async def download(url: str, dest_dir: Path, stem: str) -> Tuple[Optional[Path], str]:
    """Save one photo as `<dest_dir>/<stem>.<ext>`. Reuses a copy saved earlier for the same message."""
    for old in dest_dir.glob(stem + ".*") if dest_dir.is_dir() else []:
        if old.is_file() and old.stat().st_size > 0:
            return old, ""
    if not url_allowed(url):
        return None, "link ảnh không phải https của Zalo nên không tải"
    # Redirects are followed by hand so every hop is checked BEFORE it is requested: letting httpx follow them and checking the
    # final URL afterwards would already have sent a request to whatever internal address a hop pointed at.
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(DOWNLOAD_TIMEOUT, connect=15), follow_redirects=False) as client:
            for _hop in range(MAX_REDIRECTS + 1):
                async with client.stream("GET", url) as r:
                    if r.status_code in (301, 302, 303, 307, 308):
                        nxt = str(r.url.join(r.headers.get("location") or ""))
                        if not url_allowed(nxt):
                            return None, "link ảnh chuyển hướng ra ngoài Zalo nên không tải"
                        url = nxt
                        continue
                    if r.status_code != 200:
                        return None, f"Zalo trả HTTP {r.status_code} (link ảnh có thể đã hết hạn)"
                    ctype = r.headers.get("content-type") or ""
                    if ctype and not ctype.lower().startswith("image/"):
                        return None, f"link không phải ảnh ({ctype.split(';')[0]})"
                    buf = bytearray()
                    async for chunk in r.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > MAX_BYTES:
                            return None, f"ảnh lớn hơn {MAX_BYTES // (1024 * 1024)}MB nên không tải"
                    break
            else:
                return None, "link ảnh chuyển hướng quá nhiều lần"
    except Exception as e:      # noqa: BLE001
        return None, f"tải ảnh lỗi: {type(e).__name__}: {e}"
    if not buf:
        return None, "ảnh rỗng"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (stem + extension(url, ctype))
    dest.write_bytes(bytes(buf))
    return dest, ""


# ============================================================
# The tool
# ============================================================
def _int(v: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(n, hi))


def _want_describe(v: Any) -> Optional[bool]:
    if v is None or str(v).strip() == "":
        return None
    return v is True or str(v).strip().lower() in ("1", "true", "yes", "co", "có")


async def _read_images(args, ctx):
    args = args or {}
    why = zalo_cli.check()
    if why:
        return "ERROR: " + why
    conn, why = zalo_cli.pick_connection(zalo_cli.connections(), str(args.get("connection_id") or ""))
    if not conn:
        return "ERROR: " + why
    thread_id = str(args.get("thread_id") or args.get("group_id") or "").strip()
    if not thread_id:
        return "ERROR: thiếu thread_id (id nhóm). Tìm bằng zalo_search_threads hoặc zalo_list_threads."
    message_id = str(args.get("message_id") or "").strip()
    count = _int(args.get("count"), DEFAULT_COUNT, 1, MAX_COUNT)
    limit = _int(args.get("max_images"), DEFAULT_IMAGES, 1, MAX_IMAGES)
    question = str(args.get("question") or "").strip()

    ok, data, err = await fetch_history(conn, thread_id, count)
    source = "zalo"
    photos = photos_from_history(data) if ok else []
    if not ok or (message_id and not pick(photos, message_id, limit)):
        ok2, data2, err2 = await fetch_buffer(conn, thread_id, count)
        more = photos_from_buffer(data2) if ok2 else []
        if more:
            have = {p["message_id"] for p in photos}
            photos = sorted(photos + [p for p in more if p["message_id"] not in have], key=lambda p: p["ts"])
            source = "zalo+mcp" if ok else "mcp"
        elif not ok:
            return (f"ERROR: không lấy được tin của cuộc chat {thread_id}. Lịch sử nhóm qua Zalo: {err}. "
                    f"Bộ đệm MCP: {err2 or 'không có ảnh nào'}.")
    chosen = pick(photos, message_id, limit)
    if not chosen:
        if message_id:
            return (f"ERROR: không thấy tin ảnh {message_id} trong {count} tin gần nhất. Tăng count (tối đa {MAX_COUNT}) "
                    "hoặc kiểm lại message_id.")
        return json.dumps({"ok": True, "thread_id": thread_id, "account": conn["label"], "scanned": count, "images": [],
                           "note": f"Không có ảnh nào trong {count} tin gần nhất của cuộc chat này."}, ensure_ascii=False)

    names = sender_names(conn, thread_id)
    vault, folder = folder_for(getattr(ctx, "vault_root", None), thread_id)
    images, failed = [], []
    for p in chosen:
        stem = datetime.fromtimestamp((p["ts"] or 0) / 1000).strftime("%Y%m%d-%H%M%S") + "_" + (
            _SAFE_ID.sub("_", p["message_id"])[:40] or "anh")
        saved, why = await download(p["url"], folder, stem)
        sender = ("(chính tài khoản này)" if p["is_self"] else
                  p["sender_name"] or names.get(p["sender_id"]) or p["sender_id"])
        if not saved:
            failed.append({"message_id": p["message_id"], "sender": sender, "error": why})
            continue
        rel = saved.relative_to(vault).as_posix()
        images.append({"message_id": p["message_id"], "sender": sender, "sender_id": p["sender_id"],
                       "time": _stamp(p["ts"]), "caption": p["caption"], "path": rel,
                       "embed": f"![Ảnh Zalo {_stamp(p['ts'])}]({rel})"})

    out = {"ok": bool(images), "thread_id": thread_id, "account": conn["label"], "source": source,
           "scanned": count, "images": images}
    if failed:
        out["failed"] = failed
    if not images:
        out["error"] = "không tải được ảnh nào"
        return "ERROR: " + json.dumps(out, ensure_ascii=False)

    describe = _want_describe(args.get("describe"))
    if describe is None:
        describe = image_vision.connected()
    if describe:
        if not image_vision.connected():
            out["description_error"] = image_vision.not_connected_reason()
        else:
            texts = []
            step = image_vision.MAX_IMAGES
            for i in range(0, len(images), step):
                batch = images[i:i + step]
                labels = [f"tin {im['message_id']}, {im['sender']}, {im['time']}"
                          + (f", chú thích: {im['caption']}" if im["caption"] else "") for im in batch]
                res = await image_vision.describe_images([im["path"] for im in batch], question,
                                                         vault_root=str(vault), labels=labels)
                if res.get("ok"):
                    if len(images) > step:
                        res["text"] = f"(Ảnh {i + 1} đến {i + len(batch)})\n" + res["text"]
                    texts.append(res["text"])
                else:
                    out["description_error"] = res.get("error") or "ChatGPT không xem được ảnh"
                    break
            if texts:
                out["description"] = "\n\n".join(texts)
    out["note"] = ("Ảnh đã lưu trong brain. Engine tự xem được ảnh (Claude Code, Codex) thì mở file ở 'path'. Không tự xem được "
                   "thì dựa vào 'description' (ChatGPT đã nhìn ảnh thật) hoặc gọi naota_describe_image. Muốn người dùng thấy ảnh "
                   "thì nhúng nguyên chuỗi 'embed' vào câu trả lời.")
    return json.dumps(out, ensure_ascii=False)


def register(ctx):
    ctx.register_tool(
        name="zalo_read_images",
        description=(
            "ĐỌC ẢNH người ta gửi trong một NHÓM Zalo (chat riêng cũng được, nhưng chỉ ảnh trong 2 giờ gần nhất). Tải ảnh về "
            "brain (attachments/zalo/) rồi trả đường dẫn, người gửi, giờ, chú thích và lời tả nội dung ảnh do ChatGPT nhìn ảnh "
            "thật (chép nguyên văn chữ/số trong ảnh). Dùng thay zalo_view_media: tool đó chỉ mở ảnh trên máy chủ, bạn không "
            "thấy gì. Tham số: thread_id (id nhóm, từ zalo_search_threads), message_id (tuỳ chọn, một tin ảnh cụ thể), count "
            "(số tin gần nhất để quét, mặc định 30, tối đa 100), max_images (mặc định 4, tối đa 8), question (cần tìm gì trong "
            "ảnh), describe (false = chỉ tải, không nhờ ChatGPT tả; engine tự xem được ảnh có thể đặt false rồi mở file)."
        ),
        handler=_read_images, min_mode="safe", check_fn=zalo_cli.check,
        schema={"type": "object", "properties": {
            "thread_id": {"type": "string", "description": "id nhóm Zalo (từ zalo_search_threads/zalo_list_threads)"},
            "message_id": {"type": "string", "description": "id một tin ảnh cụ thể (tuỳ chọn)"},
            "count": {"type": "integer", "description": "số tin gần nhất để quét tìm ảnh, mặc định 30, tối đa 100"},
            "max_images": {"type": "integer", "description": "số ảnh mới nhất lấy về, mặc định 4, tối đa 8"},
            "question": {"type": "string", "description": "cần biết gì trong ảnh, vd 'tổng tiền trên hoá đơn'"},
            "describe": {"type": "boolean", "description": "nhờ ChatGPT tả ảnh (mặc định có, nếu đã đăng nhập ChatGPT)"},
            "connection_id": {"type": "string", "description": "id kết nối Zalo, chỉ cần khi đã đấu nhiều tài khoản"}},
            "required": ["thread_id"]},
    )
