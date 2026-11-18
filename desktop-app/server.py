"""Servidor local para el prototipo Remote Mouse."""
import asyncio
import ctypes
from ctypes import wintypes
import json
import math
import socket
import subprocess
import time

import pyautogui
import websockets
from motion import Motion

PORT = 8765
SENSITIVITY = 1.35
user32 = ctypes.windll.user32


def read_cursor():
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos failed")
    return point.x, point.y


def write_cursor(x, y):
    if not user32.SetCursorPos(x, y):
        raise OSError("SetCursorPos failed")


async def animate(motion):
    previous = time.perf_counter()
    while True:
        await asyncio.sleep(1 / 120)
        now = time.perf_counter()
        motion.tick(now - previous)
        previous = now


def local_ip() -> str:
    """Obtiene la IP LAN preferida sin enviar tráfico."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def stop_previous_server() -> None:
    """Detiene una instancia anterior de este servidor que use el mismo puerto."""
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False
    )
    pids = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) >= 5 and f":{PORT}" in columns[1] and columns[3] == "LISTENING":
            pids.add(columns[-1])

    for pid in pids:
        details = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, check=False,
        ).stdout.lower()
        if "server.py" in details:
            print(f"Cerrando la instancia anterior (PID {pid})…")
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], check=False, capture_output=True)
            time.sleep(0.25)
        else:
            raise RuntimeError(f"El puerto {PORT} está ocupado por otro programa (PID {pid}).")


async def handle_client(websocket):
    left, top = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    motion = Motion(read_cursor, write_cursor, (left, top, left + user32.GetSystemMetrics(78) - 1, top + user32.GetSystemMetrics(79) - 1))
    animation = asyncio.create_task(animate(motion))
    print(f"Móvil conectado: {websocket.remote_address}")
    await websocket.send(json.dumps({"type": "remote_mouse", "version": 2}))
    try:
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                if message["type"] == "move":
                    dx, dy = float(message["dx"]), float(message["dy"])
                    if not (math.isfinite(dx) and math.isfinite(dy)):
                        continue
                    motion.add(dx * SENSITIVITY, dy * SENSITIVITY)
                elif message["type"] == "move_end":
                    motion.tick(0, finish=True)
                elif message["type"] == "click":
                    motion.tick(0, finish=True)
                    pyautogui.click(button=message.get("button", "left"))
                elif message["type"] == "scroll":
                    pyautogui.scroll(int(message.get("amount", 0)))
                elif message["type"] == "media":
                    actions = {
                        "play_pause": "playpause",
                        "play_pause_video": "space",
                        "play_pause_youtube": "k",
                        "next": "nexttrack",
                        "previous": "prevtrack",
                        "volume_up": "volumeup",
                        "volume_down": "volumedown",
                        "seek_back": "left",
                        "seek_forward": "right",
                    }
                    key = actions.get(message.get("action"))
                    if key:
                        pyautogui.keyDown(key, _pause=False)
                        try:
                            await asyncio.sleep(.04)
                        finally:
                            pyautogui.keyUp(key, _pause=False)
            except pyautogui.FailSafeException:
                motion.reset()
                print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed:
        pass
    finally:
        animation.cancel()
        await asyncio.gather(animation, return_exceptions=True)
        print("Móvil desconectado")


async def main():
    stop_previous_server()
    ip = local_ip()
    print("Remote Mouse listo")
    print(f"Introduce esta IP en el móvil: {ip}")
    print(f"Escuchando en ws://0.0.0.0:{PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", PORT, compression=None):
        await asyncio.Future()


if __name__ == "__main__":
    pyautogui.PAUSE = 0
    pyautogui.MINIMUM_DURATION = 0
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor detenido")
