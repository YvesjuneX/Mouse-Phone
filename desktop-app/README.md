# Aplicación de escritorio

Servidor Python para Windows que recibe órdenes desde el móvil en la Wi-Fi local y mueve el cursor.

## Inicio

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Permite el acceso de Python en el Firewall de Windows si aparece el aviso. El programa mostrará una IP, por ejemplo `192.168.1.25`; introdúcela en la aplicación móvil. Ambos dispositivos deben estar en la misma red Wi-Fi.

> Este prototipo no incluye autenticación ni cifrado: úsalo solo en una red de confianza. Cierra el servidor con `Ctrl+C`.
