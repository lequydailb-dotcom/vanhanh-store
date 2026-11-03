"""Reading images posted in a Zalo group.

    VANHANH_OS_DIR=../vanhanh python tests/vanhanh.zalo/test_zalo_read_images.py   (NO network: fake CLI, buffer, httpx)

The Zalo MCP alone cannot read images in group chats. Three gaps stacked up: the MCP never downloads `chat.photo`,
`zalo_view_media` opens the photo on the server and answers with a path outside the brain, and the API engines only ever see text.
What is pinned here:
  1. PARSING. A group photo is `msgType: "chat.photo"` with the link in `content.href` (HD link inside `params`); text, stickers and
     links are not photos.
  2. UNTRUSTED LINKS. The link comes from a chat message: only https on a hostname, never localhost or a literal IP, also after a
     redirect, and never more than the size cap.
  3. THE BRAIN FENCE. Files land in `attachments/zalo/<thread>/` whatever the thread id looks like ("../../x" cannot climb out).
  4. FALLBACKS. Private chats (no group history) and failed CLI calls fall back to the MCP buffer; a named message not in the history
     is looked up there too; both failing is an ERROR, not an empty success.
  5. EYES FOR EVERY ENGINE. ChatGPT gets the saved photos with one label per photo; `describe=false` skips it. (`image_vision`
     itself is tested in the VANHANH repo, tests/python/test_image_vision.py.)
"""
from _paths import PACK, ROOT, SERVER  # noqa: E402,F401
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path

os.environ.setdefault("VANHANH_STATE_DIR", tempfile.mkdtemp(prefix="vanhanh-zri-"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx  # noqa: E402
import yaml  # noqa: E402

import image_gen  # noqa: E402
import image_vision  # noqa: E402
import zalo_cli  # noqa: E402

fails = []


def check(name, cond, them=""):
    print(("ok   " if cond else "FAIL ") + name + (("  [" + str(them) + "]") if them and not cond else ""))
    if not cond:
        fails.append(name)


def load(slug):
    spec = importlib.util.spec_from_file_location(slug.replace("-", "_"), PACK / "plugins" / slug / "plugin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = load("zalo-read-images")
JPEG = b"\xff\xd8\xff\xe0" + b"x" * 200
T0 = 1_791_100_000_000      # ms


def photo(mid, uid, ts, href="https://f21-zpc.zdn.vn/jpg/abc.jpg", title="", params=None, self_=False):
    c = {"title": title, "description": "", "href": href, "thumb": href.replace(".jpg", "_t.jpg"),
         "params": json.dumps(params or {"hd": href.replace(".jpg", "_hd.jpg"), "width": 1280})}
    return {"msgId": mid, "fromUid": uid, "msgType": "chat.photo", "content": c, "timestamp": ts, "isSelf": self_}


HISTORY = {"groupId": "g1", "count": 5, "messages": [
    {"msgId": "100", "fromUid": "u1", "msgType": "webchat", "content": "chào cả nhà", "timestamp": T0},
    photo("101", "u1", T0 + 1000, title="hoá đơn hôm nay"),
    {"msgId": "102", "fromUid": "u2", "msgType": "chat.sticker", "content": {"id": 5}, "timestamp": T0 + 2000},
    photo("103", "u2", T0 + 3000, href="https://f22-zpc.zdn.vn/jpg/def.jpg"),
    {"msgId": "104", "fromUid": "u2", "msgType": "chat.recommended", "content": {"href": "https://example.com/a"},
     "timestamp": T0 + 4000},
]}

# ============================================================
# 1. Parsing
# ============================================================
ps = P.photos_from_history(HISTORY)
check("only chat.photo messages are photos (text, sticker, link skipped)", [p["message_id"] for p in ps] == ["101", "103"],
      [p["message_id"] for p in ps])
check("the full-size href is used, not the thumbnail", ps[0]["url"] == "https://f21-zpc.zdn.vn/jpg/abc.jpg", ps[0]["url"])
check("the caption is kept", ps[0]["caption"] == "hoá đơn hôm nay")
check("history answer that is not a dict yields nothing, no crash", P.photos_from_history(None) == []
      and P.photos_from_history({"messages": "x"}) == [])
check("no href: fall back to the HD link inside params",
      P.photo_url({"params": json.dumps({"hd": "https://x.zdn.vn/hd.jpg"})}) == "https://x.zdn.vn/hd.jpg")
check("content wrapped as a JSON string is understood", P.photo_url(json.dumps({"href": "https://x.zdn.vn/a.jpg"}))
      == "https://x.zdn.vn/a.jpg")
check("a caption that is a link or JSON is not a caption", P._caption({"title": "https://x"}) == ""
      and P._caption({"description": "{\"a\":1}"}) == "")
check("seconds and ms timestamps both read as ms", P._ms(1_791_100_000) == 1_791_100_000_000 and P._ms(T0) == T0)

BUFFER = {"messages": [
    {"id": "201", "threadId": "dm1", "threadType": "dm", "senderId": "u9", "senderName": "Lan", "type": "chat.photo",
     "text": "https://f1.zdn.vn/p.jpg", "timestamp": T0 + 10,
     "attachment": {"type": "chat.photo", "url": "https://f1.zdn.vn/p.jpg", "description": "ảnh sản phẩm"}},
    {"id": "202", "threadId": "dm1", "senderId": "u9", "type": "text", "text": "ok", "timestamp": T0 + 20, "attachment": None},
]}
bp = P.photos_from_buffer(BUFFER)
check("MCP buffer photos keep sender name and caption", len(bp) == 1 and bp[0]["sender_name"] == "Lan"
      and bp[0]["caption"] == "ảnh sản phẩm", bp)
check("pick: newest N kept in reading order", [p["message_id"] for p in P.pick(ps, "", 1)] == ["103"])
check("pick: a named message only", [p["message_id"] for p in P.pick(ps, "101", 1)] == ["101"])

# ============================================================
# 2. Untrusted links
# ============================================================
check("https on a Zalo hostname is allowed", P.url_allowed("https://f21-zpc.zdn.vn/jpg/abc.jpg"))
check("plain http is refused", not P.url_allowed("http://f21-zpc.zdn.vn/a.jpg"))
check("localhost and .local are refused", not P.url_allowed("https://localhost/a.jpg")
      and not P.url_allowed("https://nas.local/a.jpg"))
check("a literal IP is refused (v4 and v6)", not P.url_allowed("https://127.0.0.1/a.jpg")
      and not P.url_allowed("https://[::1]/a.jpg") and not P.url_allowed("https://10.0.0.5/a.jpg"))
check("file: and other schemes are refused", not P.url_allowed("file:///etc/passwd"))
check("extension from content-type, then URL, then jpg", P.extension("https://a/x", "image/png") == ".png"
      and P.extension("https://a/x.webp?s=1") == ".webp" and P.extension("https://a/x") == ".jpg")

# ============================================================
# 3. The brain fence
# ============================================================
vault = Path(tempfile.mkdtemp(prefix="vanhanh-zri-vault-"))
root, folder = P.folder_for(str(vault), "../../etc")
check("thread folder stays inside attachments/zalo", folder.resolve().is_relative_to((vault / "attachments" / "zalo").resolve())
      and ".." not in folder.name, folder)

# ============================================================
# Fake world: CLI, MCP buffer, HTTP
# ============================================================
CONN = {"id": "z1", "label": "Zalo chính", "home": "/state/z1"}
STATE = {"history": (True, HISTORY, ""), "buffer": (True, {"messages": []}, ""), "http": [], "described": [],
         "connected": True, "names": {"u1": "Đại Lê"}}
zalo_cli.check = lambda: None
zalo_cli.connections = lambda: [dict(CONN)]


async def fake_history(conn, thread_id, count):
    STATE["history_args"] = (thread_id, count)
    return STATE["history"]


async def fake_buffer(conn, thread_id, count):
    STATE["buffer_called"] = True
    return STATE["buffer"]


P.fetch_history = fake_history
P.fetch_buffer = fake_buffer
P.sender_names = lambda conn, thread: dict(STATE["names"])


def handler(request):
    STATE["http"].append(str(request.url))
    u = str(request.url)
    if "redirect" in u:
        return httpx.Response(302, headers={"location": "https://127.0.0.1/steal.jpg"})
    if "big" in u:
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"x" * (P.MAX_BYTES + 10))
    if "html" in u:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>")
    if "gone" in u:
        return httpx.Response(404)
    return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=JPEG)


transport = httpx.MockTransport(handler)
P.httpx = types.SimpleNamespace(AsyncClient=lambda **kw: httpx.AsyncClient(transport=transport, **kw), Timeout=httpx.Timeout)


async def fake_describe(paths, question="", vault_root=None, labels=None, timeout_s=180.0):
    STATE["described"].append({"paths": list(paths), "question": question, "labels": list(labels or []), "vault": vault_root})
    return {"ok": True, "text": "Ảnh 1: hoá đơn 250.000đ", "count": len(paths)}

image_vision.connected = lambda: STATE["connected"]
image_vision.describe_images = fake_describe
CTX = types.SimpleNamespace(vault_root=str(vault))


def run(args):
    STATE["http"].clear()
    STATE["described"].clear()
    STATE.pop("buffer_called", None)
    return asyncio.run(P._read_images(args, CTX))


# ============================================================
# 4. The tool, end to end
# ============================================================
out = run({"thread_id": "g1"})
d = json.loads(out)
check("reads the two newest group photos", d["ok"] and [im["message_id"] for im in d["images"]] == ["101", "103"], out[:300])
check("photos saved inside the brain under attachments/zalo/g1", all(
    im["path"].startswith("attachments/zalo/g1/") and (vault / im["path"]).read_bytes() == JPEG for im in d["images"]), d["images"])
check("sender resolved from the inbox, id kept when unknown", d["images"][0]["sender"] == "Đại Lê"
      and d["images"][1]["sender"] == "u2", [im["sender"] for im in d["images"]])
check("embed string ready to paste", d["images"][0]["embed"].startswith("![") and d["images"][0]["path"] in d["images"][0]["embed"])
check("ChatGPT described them in one look with a label per photo", len(STATE["described"]) == 1
      and len(STATE["described"][0]["labels"]) == 2 and "hoá đơn hôm nay" in STATE["described"][0]["labels"][0]
      and d.get("description") == "Ảnh 1: hoá đơn 250.000đ", STATE["described"])
check("scan size defaults to 30 messages", STATE["history_args"] == ("g1", 30))

out = run({"thread_id": "g1", "max_images": 1, "describe": False})
d = json.loads(out)
check("max_images=1 keeps the newest only", [im["message_id"] for im in d["images"]] == ["103"])
check("describe=false does not call ChatGPT", STATE["described"] == [] and "description" not in d)
check("a photo saved earlier is reused, not downloaded again", STATE["http"] == [], STATE["http"])

STATE["connected"] = False
d = json.loads(run({"thread_id": "g1", "max_images": 1}))
check("ChatGPT not signed in: photos still returned, describe skipped by default", d["ok"] and STATE["described"] == []
      and "description_error" not in d)
d = json.loads(run({"thread_id": "g1", "max_images": 1, "describe": True}))
check("describe asked for but ChatGPT not signed in: says how to fix", "ChatGPT" in d.get("description_error", ""))
STATE["connected"] = True

out = run({"thread_id": "g1", "count": 500})
check("count is capped at 100", STATE["history_args"] == ("g1", 100))

# Private chat: the CLI has no history for it, the MCP buffer has the photo.
STATE["history"] = (False, None, "Get history failed: not a group")
STATE["buffer"] = (True, BUFFER, "")
d = json.loads(run({"thread_id": "dm1"}))
check("private chat falls back to the MCP buffer", d["ok"] and d["source"] == "mcp"
      and [im["message_id"] for im in d["images"]] == ["201"] and d["images"][0]["sender"] == "Lan", d)

STATE["buffer"] = (False, None, "MCP not running")
out = run({"thread_id": "dm1"})
check("CLI and MCP both failing is an ERROR that names both reasons", out.startswith("ERROR")
      and "not a group" in out and "MCP not running" in out, out)

# A named message older than the history window, but still in the buffer.
STATE["history"] = (True, HISTORY, "")
STATE["buffer"] = (True, BUFFER, "")
d = json.loads(run({"thread_id": "g1", "message_id": "201"}))
check("a named message missing from history is looked up in the buffer", STATE.get("buffer_called")
      and [im["message_id"] for im in d["images"]] == ["201"] and d["source"] == "zalo+mcp", d)
STATE["buffer"] = (True, {"messages": []}, "")
out = run({"thread_id": "g1", "message_id": "999"})
check("a named message found nowhere is an ERROR with a next step", out.startswith("ERROR") and "count" in out, out)

STATE["history"] = (True, {"messages": [HISTORY["messages"][0]]}, "")
d = json.loads(run({"thread_id": "g1"}))
check("no photos at all: ok with an empty list and a plain note", d["ok"] and d["images"] == [] and d["note"])

# Bad links never reach the disk.
for tag, why in (("redirect", "chuyển hướng"), ("big", "MB"), ("html", "không phải ảnh"), ("gone", "404")):
    STATE["history"] = (True, {"messages": [photo("3" + tag, "u1", T0, href=f"https://f9.zdn.vn/{tag}.jpg")]}, "")
    out = run({"thread_id": "g-" + tag, "describe": False})
    check(f"bad link ({tag}) is reported, nothing saved", out.startswith("ERROR") and why in out
          and not (vault / "attachments" / "zalo" / ("g-" + tag)).exists(), out[:200])
    check(f"bad link ({tag}) never reaches an internal address", not any("127.0.0.1" in u for u in STATE["http"]), STATE["http"])
STATE["history"] = (True, {"messages": [photo("401", "u1", T0, href="http://f9.zdn.vn/a.jpg")]}, "")
out = run({"thread_id": "g-http", "describe": False})
check("http link refused before any request", out.startswith("ERROR") and STATE["http"] == [], STATE["http"])

out = run({})
check("missing thread_id says where to find it", out.startswith("ERROR") and "zalo_search_threads" in out)

# ============================================================
# Registration matches the manifest
# ============================================================
class Ctx:
    def __init__(self):
        self.tools = []
        self.vault_root = str(vault)

    def register_tool(self, **kw):
        self.tools.append(kw)


c = Ctx()
load("zalo-read-images").register(c)
y = yaml.safe_load((PACK / "plugins" / "zalo-read-images" / "plugin.yaml").read_text(encoding="utf-8"))
by = {t["name"]: t for t in c.tools}
check("tools match plugin.yaml", sorted(by) == sorted(y["tools"]) == ["zalo_read_images"], sorted(by))
check("saving photos into the brain is a write (safe), never readonly", by["zalo_read_images"]["min_mode"] == "safe")
check("enabled inside the pack", y.get("enabled") is True)
check("the description steers away from zalo_view_media", "zalo_view_media" in by["zalo_read_images"]["description"])

for f in (Path(__file__), PACK / "plugins" / "zalo-read-images" / "plugin.py", PACK / "plugins" / "zalo-read-images" / "plugin.yaml"):
    check(f"no em dash in {f.name}", chr(0x2014) not in f.read_text(encoding="utf-8"))

if fails:
    print("\nFAIL - test_zalo_read_images: " + str(len(fails)) + " lỗi: " + ", ".join(fails))
    sys.exit(1)
print("\nOK - test_zalo_read_images: tất cả pass")
