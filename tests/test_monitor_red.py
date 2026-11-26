import csv
import os
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import monitor_red as mr


def servidor_de_prueba():
    """Abre un puerto local para simular un equipo que sí responde."""
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen()
    hilo = threading.Thread(target=lambda: servidor.accept(), daemon=True)
    hilo.start()
    return servidor, servidor.getsockname()[1]


def puerto_cerrado():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


class LeerDispositivosTest(unittest.TestCase):
    def test_usa_puerto_comun_si_no_viene(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("nombre,ip,puerto,tipo\nPortería,192.168.1.50,,camara\nRouter,192.168.1.1,8080,router\n")
        try:
            dispositivos = mr.leer_dispositivos(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(dispositivos[0].puerto, 554)
        self.assertEqual(dispositivos[1].puerto, 8080)


class RevisarTest(unittest.TestCase):
    def test_equipo_en_linea(self):
        servidor, puerto = servidor_de_prueba()
        try:
            resultado = mr.revisar(mr.Dispositivo("Prueba", "127.0.0.1", puerto), espera=1)
        finally:
            servidor.close()
        self.assertTrue(resultado.en_linea)
        self.assertIsNotNone(resultado.milisegundos)

    def test_equipo_caido(self):
        resultado = mr.revisar(mr.Dispositivo("Prueba", "127.0.0.1", puerto_cerrado()), espera=1)
        self.assertFalse(resultado.en_linea)
        self.assertIsNone(resultado.milisegundos)


class HistorialYAlertasTest(unittest.TestCase):
    def test_guardar_historial_con_encabezado(self):
        resultados = [mr.Resultado(mr.Dispositivo("NVR", "10.0.0.2", 80), True, 3.2)]
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "historial.csv")
            mr.guardar_historial(resultados, ruta)
            mr.guardar_historial(resultados, ruta)
            with open(ruta, encoding="utf-8") as f:
                filas = list(csv.reader(f))
        self.assertEqual(filas[0][0], "fecha")
        self.assertEqual(len(filas), 3)

    def test_mensaje_alerta(self):
        caidos = [mr.Resultado(mr.Dispositivo("Portería", "192.168.1.50", 554), False, None)]
        self.assertIn("Portería (192.168.1.50:554)", mr.mensaje_alerta(caidos))

    def test_main_devuelve_1_y_avisa_si_hay_caidos(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(f"nombre,ip,puerto\nCámara,127.0.0.1,{puerto_cerrado()}\n")
        entorno = {"TELEGRAM_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        try:
            with patch.dict(os.environ, entorno), patch.object(mr, "avisar_telegram") as aviso, \
                    patch("builtins.print"):
                codigo = mr.main([f.name, "--espera", "0.5"])
        finally:
            os.unlink(f.name)
        self.assertEqual(codigo, 1)
        aviso.assert_called_once()


if __name__ == "__main__":
    unittest.main()
