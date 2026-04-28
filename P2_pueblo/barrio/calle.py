"""
CALLE: Restaurante & Taller
===========================
Los dos negocios de la calle corren en la misma máquina
y se comunican entre sí mediante sockets locales.

Relación entre negocios:
  - El Taller le pide menús al Restaurante para sus trabajadores.
  - El Restaurante compra pan a la Panadería (otra calle, puerto 5000).
  - El Taller compra materiales al Supermercado (otra calle, puerto 5002).

Uso:
  python calle.py
"""

import threading
import time
import json
import socket

from restaurante import Restaurante
from taller import Taller


def arrancar(negocio):
    hilo = threading.Thread(target=negocio.iniciar_servidor, args=("127.0.0.1",), daemon=True)
    hilo.start()

def enviar(puerto: int, mensaje: dict) -> dict:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", puerto))
        s.send(json.dumps(mensaje).encode())
        respuesta = json.loads(s.recv(1024).decode())
        s.close()
        return respuesta
    except Exception as e:
        return {"error": str(e)}


def demo(restaurante, taller):
    print("\n" + "="*55)
    print("  DEMO: Interacción entre Restaurante y Taller")
    print("="*55)

    print("\n[1] Ponemos pan en el restaurante (simulando stock inicial)...")
    restaurante.inventario["pan"] = 5
    print(f"    → Restaurante tiene {restaurante.inventario['pan']} panes")

    print("\n[2] El taller pide 2 menús al restaurante para sus trabajadores...")
    resp = taller.pedir_menu("127.0.0.1", cantidad=2)
    print(f"    → {resp}")

    print("\n[3] El restaurante hace una tortilla con sus huevos...")
    resp = restaurante.hacer_tortilla(1)
    print(f"    → {resp}")

    print("\n[4] Estado final:")
    print(f"    Restaurante → {restaurante.inventario}")
    print(f"    Taller      → {taller.inventario}")
    print("="*55 + "\n")


def menu():
    print("""
Comandos:
  demo                        ver interacción entre los dos negocios
  res estado                  inventario del restaurante
  res bocadillo [n]           preparar n bocadillos
  res tortilla [n]            preparar n tortillas
  tal estado                  inventario del taller
  tal reparar [basica|ruedas] reparar un coche
  tal menu [n]                taller pide n menús al restaurante
  ayuda
  salir
""")


if __name__ == "__main__":
    restaurante = Restaurante(puerto=5001)
    taller      = Taller(puerto=5003)

    # Stock inicial para la demo
    restaurante.inventario["pan"] = 5

    arrancar(restaurante)
    arrancar(taller)
    time.sleep(0.5)

    print("╔══════════════════════════════════════╗")
    print("║   CALLE: Restaurante & Taller        ║")
    print("╠══════════════════════════════════════╣")
    print("║  Restaurante → 127.0.0.1:5001        ║")
    print("║  Taller      → 127.0.0.1:5003        ║")
    print("╚══════════════════════════════════════╝")

    menu()

    while True:
        try:
            cmd = input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print("\nCerrando la calle...")
            break

        if not cmd:
            continue

        if cmd[0] == "demo":
            demo(restaurante, taller)

        elif cmd[0] == "res":
            if len(cmd) < 2:
                menu()
            elif cmd[1] == "estado":
                print(restaurante.inventario)
            elif cmd[1] == "bocadillo":
                n = int(cmd[2]) if len(cmd) >= 3 else 1
                threading.Thread(target=lambda: print(restaurante.hacer_bocadillo(n))).start()
            elif cmd[1] == "tortilla":
                n = int(cmd[2]) if len(cmd) >= 3 else 1
                threading.Thread(target=lambda: print(restaurante.hacer_tortilla(n))).start()

        elif cmd[0] == "tal":
            if len(cmd) < 2:
                menu()
            elif cmd[1] == "estado":
                print(taller.inventario)
            elif cmd[1] == "reparar":
                tipo = cmd[2] if len(cmd) >= 3 else "basica"
                threading.Thread(target=lambda: print(taller.reparar_coche(tipo))).start()
            elif cmd[1] == "menu":
                n = int(cmd[2]) if len(cmd) >= 3 else 2
                threading.Thread(target=lambda: print(taller.pedir_menu("127.0.0.1", n))).start()

        elif cmd[0] == "ayuda":
            menu()

        elif cmd[0] == "salir":
            print("Cerrando la calle...")
            break

        else:
            print("Comando no reconocido. Escribe 'ayuda'.")
