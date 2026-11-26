"""Casos de uso que traducen comandos válidos a acciones del sistema."""
import asyncio
import math

import pyautogui
from mouse_phone.config.settings import MEDIA_KEY_PRESS_SECONDS, SENSITIVITY
from mouse_phone.input.motion import Motion
from mouse_phone.input import windows


class RemoteController:
    def __init__(self, motion: Motion):
        self.motion = motion

    async def execute(self, message: dict) -> None:
        message_type = message["type"]
        if message_type == "move":
            dx, dy = float(message["dx"]), float(message["dy"])
            if math.isfinite(dx) and math.isfinite(dy):
                self.motion.add(dx * SENSITIVITY, dy * SENSITIVITY)
        elif message_type == "move_end": self.motion.tick(0, finish=True)
        elif message_type == "click":
            self.motion.tick(0, finish=True)
            pyautogui.click(button=message.get("button", "left"))
        elif message_type == "scroll": pyautogui.scroll(int(message.get("amount", 0)))
        elif message_type == "media":
            key = windows.MEDIA_KEYS.get(message.get("action"))
            if key:
                pyautogui.keyDown(key, _pause=False)
                try: await asyncio.sleep(MEDIA_KEY_PRESS_SECONDS)
                finally: pyautogui.keyUp(key, _pause=False)
