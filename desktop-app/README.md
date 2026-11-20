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

> Al iniciarse se abre una ventana con un código temporal, QR y estado TLS. El código rota cada cinco minutos y cambia al reiniciar el servicio. Antes de la primera conexión, instala en el móvil la CA local que abre el botón **Abrir certificado para el móvil**. Cierra el servidor cerrando la ventana o con `Ctrl+C`.
