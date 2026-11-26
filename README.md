# Monitor de Red

Script en **Python** que revisa si las cámaras, grabadores, routers y demás equipos de seguridad responden en la red. Lee la lista de equipos desde un CSV, los revisa todos al mismo tiempo y muestra cuáles están caídos. Si hay alguno caído, puede avisar por **Telegram**.

Lo hice para mi trabajo como técnico: en vez de abrir equipo por equipo, corro el script y en segundos sé qué hay que ir a revisar.

![Pruebas](https://github.com/Gutierrezor/monitor-red/actions/workflows/pruebas.yml/badge.svg)

```
EQUIPO              IP:PUERTO              ESTADO       TIEMPO
---------------------------------------------------------------
Cámara portería     192.168.1.50:554       EN LÍNEA     12.4 ms
Cámara parqueadero  192.168.1.51:554       CAÍDO        -
Grabador NVR        192.168.1.10:80        EN LÍNEA     3.1 ms
Router principal    192.168.1.1:80         EN LÍNEA     1.8 ms

4 equipos revisados, 1 caídos.
```

## Qué hace

- Revisa cada equipo abriendo una conexión TCP a su puerto (por ejemplo **RTSP 554** en las cámaras). Se usa TCP y no ping porque muchas redes bloquean el ping y así además se sabe que el servicio está arriba.
- Revisa los equipos **en paralelo** con hilos, así 50 equipos no tardan 50 veces más.
- Si el CSV no trae puerto, usa el común según el tipo de equipo.
- Guarda un **historial** en CSV para ver qué equipos se caen seguido.
- Avisa por **Telegram** cuando hay equipos caídos.
- Devuelve código de salida `1` si hay caídos, para usarlo en **cron** u otros scripts.
- Solo usa la librería estándar de Python: no hay que instalar nada.

## Cómo usarlo

1. Copia el ejemplo y pon tus equipos:

   ```bash
   cp dispositivos.ejemplo.csv dispositivos.csv
   ```

   ```csv
   nombre,ip,puerto,tipo
   Cámara portería,192.168.1.50,,camara
   Router principal,192.168.1.1,80,router
   ```

2. Córrelo:

   ```bash
   python monitor_red.py dispositivos.csv
   python monitor_red.py dispositivos.csv --espera 3 --historial historial.csv
   ```

### Avisos por Telegram (opcional)

Crea un bot con [@BotFather](https://t.me/BotFather), consigue tu `chat_id` y define estas variables:

```bash
export TELEGRAM_TOKEN="el-token-del-bot"
export TELEGRAM_CHAT_ID="tu-chat-id"
```

### Revisión automática con cron

Cada 5 minutos, guardando historial:

```cron
*/5 * * * * cd /ruta/monitor-red && python3 monitor_red.py dispositivos.csv --historial historial.csv
```

## Pruebas

```bash
python -m unittest discover -s tests -t .
```

Las pruebas abren un puerto local para simular un equipo que responde y uno caído, y revisan el historial y los avisos. Se corren solas en cada push con GitHub Actions.

## Tecnologías

Python 3.10+ · socket · concurrent.futures · csv · unittest · GitHub Actions

---

Hecho por **Julián Andrés Gutiérrez Ordóñez** · [LinkedIn](https://www.linkedin.com/in/julianandresgutierrez) · [Portafolio](https://portafolio-julian-psi.vercel.app/)
