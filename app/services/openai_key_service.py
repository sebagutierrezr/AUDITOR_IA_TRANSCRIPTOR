from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes

from app.services.paths_service import AppPaths


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class OpenAIKeyService:
    def __init__(self) -> None:
        self.path = AppPaths().config / "openai_api_key.dat"

    def get_key(self) -> str:
        env = os.environ.get("OPENAI_API_KEY", "").strip()
        if env:
            return env
        if not self.path.is_file():
            return ""
        try:
            encrypted = base64.b64decode(self.path.read_text(encoding="ascii"))
            if os.name == "nt":
                return self._unprotect(encrypted).decode("utf-8").strip()
            return encrypted.decode("utf-8").strip()
        except Exception:
            return ""

    def has_key(self) -> bool:
        return bool(self.get_key())

    def save_key(self, key: str) -> None:
        value = (key or "").strip()
        if not value:
            self.delete_key()
            return
        raw = value.encode("utf-8")
        encrypted = self._protect(raw) if os.name == "nt" else raw
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            base64.b64encode(encrypted).decode("ascii"), encoding="ascii"
        )

    def delete_key(self) -> None:
        self.path.unlink(missing_ok=True)

    @staticmethod
    def masked(key: str) -> str:
        value = (key or "").strip()
        if not value:
            return "NO CONFIGURADA"
        if len(value) <= 10:
            return "••••••••"
        return value[:3] + "••••••••••" + value[-4:]

    @staticmethod
    def _blob(data: bytes):
        buffer = ctypes.create_string_buffer(data)
        blob = DATA_BLOB(
            len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
        )
        return blob, buffer

    def _protect(self, data: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPCWSTR,
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL

        source, keepalive = self._blob(data)
        result = DATA_BLOB()
        ok = crypt32.CryptProtectData(
            ctypes.byref(source),
            "AUDITOR IA - API KEY",
            None,
            None,
            None,
            0x1,
            ctypes.byref(result),
        )
        if not ok:
            raise OSError("Windows no pudo proteger la API key.")
        try:
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            kernel32.LocalFree(result.pbData)

    def _unprotect(self, data: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL

        source, keepalive = self._blob(data)
        result = DATA_BLOB()
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)
        )
        if not ok:
            raise OSError("Windows no pudo leer la API key guardada.")
        try:
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            kernel32.LocalFree(result.pbData)
