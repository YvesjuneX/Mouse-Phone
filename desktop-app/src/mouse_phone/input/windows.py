"""Adaptador de Windows para cursor, clics, rueda y teclas multimedia."""
import ctypes
from ctypes import wintypes

import pyautogui

user32 = ctypes.windll.user32


def read_cursor() -> tuple[int, int]:
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos failed")
    return point.x, point.y


def write_cursor(x: int, y: int) -> None:
    if not user32.SetCursorPos(x, y):
        raise OSError("SetCursorPos failed")


def screen_bounds() -> tuple[int, int, int, int]:
    left, top = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    return left, top, left + user32.GetSystemMetrics(78) - 1, top + user32.GetSystemMetrics(79) - 1


MEDIA_KEYS = {"play_pause": "playpause", "next": "nexttrack", "previous": "prevtrack", "volume_up": "volumeup", "volume_down": "volumedown", "seek_back": "left", "seek_forward": "right"}
