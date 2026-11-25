"""Protección local de secretos con Windows DPAPI."""
import ctypes
from ctypes import wintypes
import os


CRYPTPROTECT_UI_FORBIDDEN = 0x1
_ENTROPY = b"MousePhone/device-registry/v1"


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DataBlob, object]:
    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _protect_api():
    if os.name != "nt": raise RuntimeError("Windows DPAPI solo está disponible en Windows")
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DataBlob), wintypes.LPCWSTR, ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
    return crypt32, ctypes.windll.kernel32


def protect(data: bytes) -> bytes:
    crypt32, kernel32 = _protect_api()
    source, _source_buffer = _blob(data)
    entropy, _entropy_buffer = _blob(_ENTROPY)
    output = DataBlob()
    if not crypt32.CryptProtectData(ctypes.byref(source), "Mouse Phone device registry", ctypes.byref(entropy), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try: return ctypes.string_at(output.pbData, output.cbData)
    finally: kernel32.LocalFree(output.pbData)


def unprotect(data: bytes) -> bytes:
    crypt32, kernel32 = _protect_api()
    source, _source_buffer = _blob(data)
    entropy, _entropy_buffer = _blob(_ENTROPY)
    output = DataBlob()
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, ctypes.byref(entropy), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try: return ctypes.string_at(output.pbData, output.cbData)
    finally: kernel32.LocalFree(output.pbData)
