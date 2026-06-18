from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.conversation import ConversationEngine
from app.schemas import ConversationState


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
REPORTS_DIR = ROOT_DIR / "reports"

SESSIONS: dict[str, ConversationState] = {}
ENGINE = ConversationEngine()


class OARequestHandler(BaseHTTPRequestHandler):
    server_version = "OAHomePainAssistant/0.2.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "sessions": len(SESSIONS)})
            return
        if parsed.path == "/api/state":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(state.to_dict())
            return
        if parsed.path == "/":
            self._send_static(STATIC_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            self._send_static(STATIC_DIR / relative)
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/start":
            data = self._read_json()
            language = str(data.get("language", "en"))
            state = ENGINE.start(language=language)
            SESSIONS[state.session_id] = state
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": [state.transcript[-1]["text"]],
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/message":
            data = self._read_json()
            session_id = str(data.get("session_id", ""))
            text = str(data.get("text", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return

            before = len(state.transcript)
            ENGINE.handle_user_message(state, text)
            assistant_messages = [
                item["text"]
                for item in state.transcript[before:]
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": assistant_messages,
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/save_report":
            data = self._read_json()
            session_id = str(data.get("session_id", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return
            if not state.report:
                self._send_json({"error": "report is not ready"}, HTTPStatus.BAD_REQUEST)
                return

            REPORTS_DIR.mkdir(exist_ok=True)
            filename = f"oa-report-{state.created_at.replace(':', '-')}-{state.session_id[:8]}.json"
            path = REPORTS_DIR / filename
            path.write_text(state.report, encoding="utf-8")
            self._send_json({"saved": True, "path": str(path)})
            return

        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(data, dict):
            return data
        return {}

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path) -> None:
        safe_path = path.resolve()
        if not str(safe_path).startswith(str(STATIC_DIR.resolve())):
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        if not safe_path.is_file():
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
        body = safe_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), OARequestHandler)
    print(f"OA Home Pain Check-in Assistant running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    run(host, port)
