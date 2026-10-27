"""
Клиент Discord Rich Presence (IPC) через Named Pipes (Windows) и Unix Domain Sockets (Linux).
Прямое подключение без сторонних библиотек.
"""

import os
import sys
import time
import json
import socket
import struct
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("MusicRPC.DiscordIPC")


class DiscordIPC:
    """Низкоуровневый клиент Discord Rich Presence."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.sock: Optional[socket.socket] = None
        self.pipe: Optional[Any] = None
        self.connected = False
        self.last_connect_attempt = 0.0

    def _find_ipc_path(self) -> Optional[str]:
        if sys.platform == "win32":
            for i in range(10):
                path = rf"\\.\pipe\discord-ipc-{i}"
                if os.path.exists(path):
                    return path
            return None

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        candidates = [
            f"{runtime_dir}/discord-ipc-{i}" for i in range(10)
        ] + [
            f"/tmp/discord-ipc-{i}" for i in range(10)
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _write_raw(self, data: bytes):
        if sys.platform == "win32":
            if self.pipe:
                self.pipe.write(data)
        else:
            if self.sock:
                self.sock.sendall(data)

    def _read_raw(self, length: int) -> bytes:
        buf = b""
        while len(buf) < length:
            needed = length - len(buf)
            if sys.platform == "win32":
                chunk = self.pipe.read(needed) if self.pipe else b""
            else:
                chunk = self.sock.recv(min(needed, 4096)) if self.sock else b""
            if not chunk:
                break
            buf += chunk
        return buf

    def connect(self) -> bool:
        if self.connected:
            return True

        now = time.time()
        if now - self.last_connect_attempt < 3.0:
            return False
        self.last_connect_attempt = now

        ipc_path = self._find_ipc_path()
        if not ipc_path:
            return False

        try:
            if sys.platform == "win32":
                self.pipe = open(ipc_path, "r+b", buffering=0)
            else:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(3.0)
                self.sock.connect(ipc_path)

            handshake = json.dumps({"v": 1, "client_id": self.client_id}).encode("utf-8")
            self._write_raw(struct.pack("<II", 0, len(handshake)) + handshake)

            hdr = self._read_raw(8)
            if not hdr or len(hdr) < 8:
                self.disconnect()
                return False

            op, length = struct.unpack("<II", hdr)
            data = self._read_raw(length)
            if len(data) < length:
                self.disconnect()
                return False

            resp = json.loads(data.decode("utf-8"))
            if resp.get("evt") == "READY":
                self.connected = True
                user = resp.get("data", {}).get("user", {})
                username = user.get("global_name") or user.get("username")
                logger.info("Подключено к Discord (пользователь: %s)", username)
                return True
            else:
                self.disconnect()
                return False
        except Exception as e:
            self.disconnect()
            return False

    def disconnect(self):
        self.connected = False
        if self.pipe:
            try:
                self.pipe.close()
            except Exception:
                pass
            self.pipe = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def reconnect(self, new_client_id: Optional[str] = None) -> bool:
        if self.connected:
            try:
                self.clear_activity()
            except Exception:
                pass
        self.disconnect()
        if new_client_id:
            self.client_id = new_client_id
        self.last_connect_attempt = 0.0
        return self.connect()

    def send_frame(self, op: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.connected:
            if not self.connect():
                return None

        try:
            raw = json.dumps(data).encode("utf-8")
            self._write_raw(struct.pack("<II", op, len(raw)) + raw)

            hdr = self._read_raw(8)
            if not hdr or len(hdr) < 8:
                self.disconnect()
                return None
            op_resp, length = struct.unpack("<II", hdr)
            buf = self._read_raw(length)
            if len(buf) < length:
                self.disconnect()
                return None
            return json.loads(buf.decode("utf-8"))
        except Exception as e:
            logger.warning("Ошибка связи с Discord IPC: %s", e)
            self.disconnect()
            return None

    def set_activity(self, activity: Optional[Dict[str, Any]]) -> bool:
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": os.getpid(),
                "activity": activity
            },
            "nonce": str(time.time())
        }
        resp = self.send_frame(1, payload)
        return resp is not None and resp.get("evt") != "ERROR"

    def clear_activity(self) -> bool:
        return self.set_activity(None)
