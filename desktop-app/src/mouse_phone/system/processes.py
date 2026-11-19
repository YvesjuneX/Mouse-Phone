"""Gestión del proceso local del servidor en Windows."""
import subprocess
import time


def stop_previous_server(port: int) -> None:
    """Detiene únicamente otra instancia de este servidor en el mismo puerto."""
    result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False)
    pids = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) >= 5 and f":{port}" in columns[1] and columns[3] == "LISTENING":
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
            raise RuntimeError(f"El puerto {port} está ocupado por otro programa (PID {pid}).")
