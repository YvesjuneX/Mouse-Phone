"""Interfaz local de Windows para mostrar el emparejamiento actual."""
from io import BytesIO
import tkinter as tk
from tkinter import ttk
import os
from urllib.parse import urlencode
import base64

import qrcode
from PIL import ImageTk

from mouse_phone.config.settings import PORT
from mouse_phone.security.pairing import PairingManager


class DesktopWindow:
    def __init__(self, ip: str, pairing: PairingManager, on_close):
        self.ip, self.pairing, self.on_close = ip, pairing, on_close
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

    def close(self) -> None:
        self.on_close()
        self.root.destroy()


    def run(self) -> None:
        self.root.mainloop()
