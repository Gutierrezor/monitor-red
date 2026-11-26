"""
Monitor de red para equipos de seguridad.

Lee una lista de equipos (cámaras, grabadores, routers...) desde un CSV,
revisa al mismo tiempo si cada uno responde en su puerto y muestra un
resumen. Si algo está caído puede avisar por Telegram.

Uso:
    python monitor_red.py dispositivos.csv
    python monitor_red.py dispositivos.csv --historial historial.csv --espera 3
"""

import argparse
import csv
import json
import os
import socket
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

PUERTOS_COMUNES = {
    "camara": 554,   # RTSP
    "nvr": 80,
    "dvr": 80,
    "router": 80,
    "alarma": 4370,
}


@dataclass
class Dispositivo:
    nombre: str
    ip: str
    puerto: int
    tipo: str = ""


@dataclass
class Resultado:
    dispositivo: Dispositivo
    en_linea: bool
    milisegundos: float | None


def leer_dispositivos(ruta):
    """Lee el CSV. Si no trae puerto, usa el común según el tipo."""
    dispositivos = []
    with open(ruta, newline="", encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            tipo = (fila.get("tipo") or "").strip().lower()
            puerto = (fila.get("puerto") or "").strip()
            dispositivos.append(
                Dispositivo(
                    nombre=fila["nombre"].strip(),
                    ip=fila["ip"].strip(),
                    puerto=int(puerto) if puerto else PUERTOS_COMUNES.get(tipo, 80),
                    tipo=tipo,
                )
            )
    return dispositivos


def revisar(dispositivo, espera=2.0):
    """Intenta abrir una conexión TCP y mide cuánto se demora."""
    inicio = time.perf_counter()
    try:
        with socket.create_connection((dispositivo.ip, dispositivo.puerto), timeout=espera):
            pass
    except OSError:
        return Resultado(dispositivo, False, None)
    return Resultado(dispositivo, True, round((time.perf_counter() - inicio) * 1000, 1))


def revisar_todos(dispositivos, espera=2.0, hilos=20):
    """Revisa todos en paralelo para no esperar uno por uno."""
    with ThreadPoolExecutor(max_workers=hilos) as grupo:
        return list(grupo.map(lambda d: revisar(d, espera), dispositivos))


def mostrar_tabla(resultados):
    ancho = max([len(r.dispositivo.nombre) for r in resultados] + [6])
    print(f"{'EQUIPO'.ljust(ancho)}  {'IP:PUERTO'.ljust(21)}  ESTADO       TIEMPO")
    print("-" * (ancho + 45))
    for r in resultados:
        direccion = f"{r.dispositivo.ip}:{r.dispositivo.puerto}"
        estado = "EN LÍNEA" if r.en_linea else "CAÍDO"
        tiempo = f"{r.milisegundos} ms" if r.milisegundos is not None else "-"
        print(f"{r.dispositivo.nombre.ljust(ancho)}  {direccion.ljust(21)}  {estado.ljust(11)}  {tiempo}")
    caidos = sum(not r.en_linea for r in resultados)
    print(f"\n{len(resultados)} equipos revisados, {caidos} caídos.")


def guardar_historial(resultados, ruta):
    """Agrega una línea por equipo al CSV de historial (sirve para ver caídas repetidas)."""
    nuevo = not os.path.exists(ruta)
    ahora = datetime.now().isoformat(timespec="seconds")
    with open(ruta, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if nuevo:
            escritor.writerow(["fecha", "nombre", "ip", "puerto", "en_linea", "milisegundos"])
        for r in resultados:
            d = r.dispositivo
            escritor.writerow([ahora, d.nombre, d.ip, d.puerto, int(r.en_linea), r.milisegundos or ""])


def mensaje_alerta(caidos):
    lineas = [f"⚠️ {len(caidos)} equipo(s) caído(s):"]
    lineas += [f"• {r.dispositivo.nombre} ({r.dispositivo.ip}:{r.dispositivo.puerto})" for r in caidos]
    return "\n".join(lineas)


def avisar_telegram(texto, token, chat_id):
    """Envía el aviso con la API de bots de Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    datos = urllib.parse.urlencode({"chat_id": chat_id, "text": texto}).encode()
    with urllib.request.urlopen(url, data=datos, timeout=10) as respuesta:
        return json.load(respuesta).get("ok", False)


def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Revisa si los equipos de seguridad responden en la red.")
    parser.add_argument("archivo", help="CSV con columnas nombre, ip, puerto (opcional), tipo (opcional)")
    parser.add_argument("--espera", type=float, default=2.0, help="segundos de espera por equipo")
    parser.add_argument("--historial", help="CSV donde guardar cada revisión")
    opciones = parser.parse_args(argumentos)

    resultados = revisar_todos(leer_dispositivos(opciones.archivo), opciones.espera)
    mostrar_tabla(resultados)

    if opciones.historial:
        guardar_historial(resultados, opciones.historial)

    caidos = [r for r in resultados if not r.en_linea]
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if caidos and token and chat_id:
        try:
            avisar_telegram(mensaje_alerta(caidos), token, chat_id)
            print("Aviso enviado por Telegram.")
        except OSError as error:
            print(f"No se pudo enviar el aviso por Telegram: {error}", file=sys.stderr)

    # Código de salida 1 si hay caídos: sirve para usarlo en cron o en otros scripts.
    return 1 if caidos else 0


if __name__ == "__main__":
    sys.exit(main())
