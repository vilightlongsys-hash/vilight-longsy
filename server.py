#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VILIGHT - LONGSYS — máy chủ website (backend)
==============================================
Phục vụ trang web (index.html) + API lưu dữ liệu sản phẩm tập trung,
để khi bạn sửa/thêm sản phẩm trong ứng dụng thì khách hàng xem web thấy NGAY.

Chỉ dùng thư viện chuẩn của Python (không cần cài gì thêm).

API:
  GET  /api/data  -> trả về dữ liệu sản phẩm mới nhất (công khai, ai cũng đọc được)
  POST /api/data  -> lưu dữ liệu mới (cần mật khẩu đúng — mật khẩu = mật khẩu đăng nhập phần sửa dữ liệu)

Biến môi trường (tùy chọn):
  PORT            -> cổng chạy (mặc định 8080; Render/Railway tự cấp)
  ADMIN_PW_HASH   -> mã băm SHA-256 của mật khẩu quản trị (mặc định khớp mật khẩu hiện tại của bạn)
  VL_DATA_FILE    -> đường dẫn file lưu dữ liệu (mặc định data.json cạnh file này)
"""
import json
import os
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("VL_DATA_FILE", os.path.join(BASE_DIR, "data.json"))
ADMIN_PW_HASH = os.environ.get(
    "ADMIN_PW_HASH",
    "06d8c8cc2f97f69ebf8ddcf7c305d7960ef5a568c84a8f287a821f322cf74699",
).lower()
PORT = int(os.environ.get("PORT", "8080"))
MAX_BODY = 120 * 1024 * 1024  # 120 MB


def sha256(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_data(obj):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass  # giữ log gọn

    # ---------- API ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            d = read_data()
            if d and d.get("version") == 1 and d.get("data"):
                self._send(200, json.dumps(d))
            else:
                self._send(200, json.dumps({"empty": True}))
            return
        self._serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/data":
            self._send(404, json.dumps({"ok": False, "error": "not found"}))
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0 or length > MAX_BODY:
                raise ValueError("bad length")
            raw = self.rfile.read(length).decode("utf-8")
            obj = json.loads(raw)
        except Exception:
            self._send(400, json.dumps({"ok": False, "error": "Dữ liệu gửi lên không hợp lệ."}))
            return
        pw = str(obj.get("password", ""))
        if sha256(pw) != ADMIN_PW_HASH:
            self._send(401, json.dumps({"ok": False, "error": "Sai mật khẩu quản trị."}))
            return
        data = obj.get("data")
        if not data or data.get("version") != 1 or not data.get("data"):
            self._send(400, json.dumps({"ok": False, "error": "Thiếu dữ liệu sản phẩm."}))
            return
        try:
            write_data(data)
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": "Không ghi được dữ liệu: %s" % e}))
            return
        self._send(200, json.dumps({"ok": True}))

    # ---------- file tĩnh ----------
    def _serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(BASE_DIR, rel))
        if not full.startswith(os.path.normpath(BASE_DIR)):
            self._send(403, "forbidden", "text/plain; charset=utf-8")
            return
        if not os.path.isfile(full):
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        try:
            with open(full, "rb") as f:
                self._send(200, f.read(), ctype)
        except Exception:
            self._send(500, "error", "text/plain; charset=utf-8")


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("VILIGHT - LONGSYS server đang chạy tại cổng %d" % PORT, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
