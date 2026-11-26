"""Interfaz local de Windows para mostrar el emparejamiento actual."""
from io import BytesIO
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlencode
import base64

import qrcode
from PIL import ImageTk

from mouse_phone.config.settings import PORT
from mouse_phone.security.pairing import PairingManager
from mouse_phone.security.device_registry import DeviceRegistry
from mouse_phone.security.active_sessions import ActiveSessions


class DesktopWindow:
    def __init__(self, ip: str, pairing: PairingManager, registry: DeviceRegistry, sessions: ActiveSessions, on_close):
        self.ip, self.pairing, self.registry, self.sessions, self.on_close = ip, pairing, registry, sessions, on_close
        self.root = tk.Tk()
        self.root.title("Mouse Phone")
        self.root.resizable(False, False)
        self.root.configure(background="#101828")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        frame = tk.Frame(self.root, bg="#101828", padx=28, pady=24)
        frame.pack()
        tk.Label(frame, text="Mouse Phone", font=("Segoe UI", 22, "bold"), fg="white", bg="#101828").pack()
        tk.Label(frame, text=f"Ordenador disponible: {ip}", font=("Segoe UI", 10), fg="#aebbd1", bg="#101828").pack(pady=(4, 16))
        tk.Label(frame, text="● Cifrado de extremo a extremo", font=("Segoe UI", 10, "bold"), fg="#84efb6", bg="#101828").pack(pady=(0, 10))
        self.qr_label = tk.Label(frame, bg="white", padx=10, pady=10)
        self.qr_label.pack()
        tk.Label(frame, text="Código temporal", font=("Segoe UI", 10, "bold"), fg="#aebbd1", bg="#101828").pack(pady=(16, 2))
        self.code_label = tk.Label(frame, font=("Consolas", 25, "bold"), fg="#84caff", bg="#101828")
        self.code_label.pack()
        self.timer_label = tk.Label(frame, font=("Segoe UI", 9), fg="#98a2b3", bg="#101828")
        self.timer_label.pack(pady=(4, 0))
        ttk.Button(frame, text="Generar un código nuevo", command=self.regenerate).pack(pady=(16, 0))
        settings = tk.LabelFrame(frame, text="Dispositivos y acceso", bg="#101828", fg="white", padx=8, pady=8)
        settings.pack(fill="x", pady=(16, 0))
        self.device_list = tk.Listbox(settings, height=5, width=42)
        self.device_list.pack()
        self.selected_device_id = None
        self.device_list.bind("<<ListboxSelect>>", self.select_device)
        buttons = tk.Frame(settings, bg="#101828"); buttons.pack(pady=6)
        for text, state in (("Confiar", "trusted"), ("Temporal", "temporary"), ("Bloquear", "blocked")):
            ttk.Button(buttons, text=text, command=lambda value=state: self.change_state(value)).pack(side="left", padx=2)
        ttk.Button(settings, text="Actualizar dispositivos", command=self.refresh_devices).pack(pady=(4, 0))
        tk.Label(settings, text="Acceso temporal (minutos):", bg="#101828", fg="#aebbd1").pack(side="left")
        self.minutes = tk.StringVar(value=str(registry.temporary_minutes()))
        self.minutes_input = tk.Spinbox(settings, from_=1, to=1440, textvariable=self.minutes, width=5, command=self.save_minutes)
        self.minutes_input.pack(side="left", padx=4)
        self.minutes_input.bind("<Return>", self.save_minutes)
        self.minutes_input.bind("<FocusOut>", self.save_minutes)
        self.refresh_devices()
        active = tk.LabelFrame(frame, text="Sesiones activas", bg="#101828", fg="white", padx=8, pady=8)
        active.pack(fill="x", pady=(12, 0))
        self.session_list = tk.Listbox(active, height=3, width=42)
        self.session_list.pack()
        self.selected_session_id = None
        self.session_list.bind("<<ListboxSelect>>", self.select_session)
        ttk.Button(active, text="Finalizar conexión seleccionada", command=self.end_session).pack(pady=(6, 0))
        self.refresh_sessions()
        self.refresh()

    def payload(self) -> str:
        details = self.pairing.current()
        return "mousephone://pair?" + urlencode({"ip": self.ip, "port": PORT, "code": details.code, "expires": int(details.expires_at), "secret": base64.b64encode(details.qr_secret).decode()})

    def regenerate(self) -> None:
        self.pairing.renew()
        self.refresh()

    def refresh(self) -> None:
        details = self.pairing.current()
        image = qrcode.make(self.payload()).resize((210, 210))
        stream = BytesIO(); image.save(stream, format="PNG")
        self.qr_image = ImageTk.PhotoImage(data=stream.getvalue())
        self.qr_label.configure(image=self.qr_image)
        self.code_label.configure(text=details.code)
        remaining = max(0, int(details.expires_at - self.pairing.clock()))
        self.timer_label.configure(text=f"Caduca en {remaining // 60}:{remaining % 60:02d}")
        self.root.after(1000, self.refresh)

    def refresh_devices(self):
        selected_id = self.selected_device_id
        self.device_list.delete(0, tk.END)
        self.device_rows = self.registry.list_devices()
        for index, (device_id, item) in enumerate(self.device_rows):
            self.device_list.insert(tk.END, f"{item['name']} · {item['state']}")
            if device_id == selected_id:
                self.device_list.selection_set(index)

    def select_device(self, _event=None):
        selection = self.device_list.curselection()
        self.selected_device_id = self.device_rows[selection[0]][0] if selection else None

    def change_state(self, state):
        if self.selected_device_id:
            self.registry.set_state(self.selected_device_id, state)
            self.refresh_devices()

    def save_minutes(self, _event=None):
        try:
            self.registry.set_temporary_minutes(int(self.minutes.get()))
            self.minutes.set(str(self.registry.temporary_minutes()))
        except ValueError:
            self.minutes.set(str(self.registry.temporary_minutes()))

    def refresh_sessions(self):
        self.render_sessions()
        self.root.after(1000, self.refresh_sessions)

    def render_sessions(self):
        selected_id = self.selected_session_id
        self.session_list.delete(0, tk.END)
        self.session_rows = self.sessions.list()
        for index, (session_id, item) in enumerate(self.session_rows):
            self.session_list.insert(tk.END, item["name"])
            if session_id == selected_id:
                self.session_list.selection_set(index)

    def select_session(self, _event=None):
        selection = self.session_list.curselection()
        self.selected_session_id = self.session_rows[selection[0]][0] if selection else None

    def end_session(self):
        if self.selected_session_id:
            self.sessions.end(self.selected_session_id)
            self.selected_session_id = None
            self.render_sessions()

    def close(self) -> None:
        self.on_close()
        self.root.destroy()


    def run(self) -> None:
        self.root.mainloop()
