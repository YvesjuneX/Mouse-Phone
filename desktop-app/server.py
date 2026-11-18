"""Servidor local para el prototipo Remote Mouse."""
import asyncio
import json
import math
import socket
import subprocess
import time

import pyautogui
import websockets

PORT = 8765
SENSITIVITY = 1.35


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
    remainder_x = remainder_y = 0.0
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
                    remainder_x += dx * SENSITIVITY
                    remainder_y += dy * SENSITIVITY
                    x, y = math.trunc(remainder_x), math.trunc(remainder_y)
                    remainder_x -= x
                    remainder_y -= y
                    if x or y:
                        pyautogui.moveRel(x, y, duration=0, _pause=False)
                elif message["type"] == "click":
                    pyautogui.click(button=message.get("button", "left"))
                elif message["type"] == "scroll":
                    pyautogui.scroll(int(message.get("amount", 0)))
                elif message["type"] == "media":
                    actions = {
                        "play_pause": "playpause",
                        "next": "nexttrack",
                        "previous": "prevtrack",
                        "volume_up": "volumeup",
                        "volume_down": "volumedown",
                        "seek_back": "left",
                        "seek_forward": "right",
                    }
                    key = actions.get(message.get("action"))
                    if key:
                        pyautogui.press(key)
            except pyautogui.FailSafeException:
                remainder_x = remainder_y = 0.0
                print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed:
        pass
    finally:
        print("Móvil desconectado")


async def main():
    stop_previous_server()
    ip = local_ip()
    print("Remote Mouse listo")
    print(f"Introduce esta IP en el móvil: {ip}")
    print(f"Escuchando en ws://0.0.0.0:{PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", PORT):
        await asyncio.Future()


if __name__ == "__main__":
    pyautogui.PAUSE = 0
    pyautogui.MINIMUM_DURATION = 0
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor detenido")
