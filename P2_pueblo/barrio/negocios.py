"""
BARRIO: La Comarca (sin zona peatonal - todo en coche)
======================================================
Negocios:
  - Panadería     puerto 5000  (panaderia.py)
  - Restaurante   puerto 5001  (restaurante.py)
  - Supermercado  puerto 5002  (super.py)
  - Taller        puerto 5003  (taller.py)

Interacciones:
  Panadería   → Supermercado : pide harina y huevos
  Restaurante → Panadería    : compra pan
  Restaurante → Supermercado : compra ingredientes (huevos, leche)
  Taller      → Supermercado : compra materiales (aceite_motor, tornillos, ruedas)

Uso:
  python negocios.py
"""

import threading
import time
import json
import socket

from panaderia import Panaderia
from super import Supermercado
from restaurante import Restaurante
from taller import Taller


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# DEMO DE INTERACCIONES
# ─────────────────────────────────────────────────────────────────────────────

def demo(panaderia, restaurante, supermercado, taller):
    print("\n" + "="*55)
    print("  DEMO: Interacciones entre negocios del barrio")
    print("="*55)

    print("\n[1] Panadería hace pan (necesita huevos → pide al supermercado si faltan)")
    resp = panaderia.hacer_pan(3)
    print(f"    → {resp}")

    time.sleep(0.5)

    print("\n[2] Restaurante compra pan a la panadería")
    resp = restaurante.pedir_pan("127.0.0.1", 2)
    print(f"    → {resp}")

    time.sleep(0.5)

    print("\n[3] Restaurante compra huevos al supermercado")
    resp = restaurante.pedir_ingrediente("127.0.0.1", "huevos", 4)
    print(f"    → {resp}")

    time.sleep(0.5)

    print("\n[4] Taller pide menús al restaurante para sus trabajadores")
    restaurante.inventario["pan"] = max(restaurante.inventario.get("pan", 0), 3)
    resp = taller.pedir_menu("127.0.0.1", cantidad=2)
    print(f"    → {resp}")

    time.sleep(0.5)

    print("\n[5] Taller compra aceite_motor al supermercado")
    resp = taller.pedir_material("127.0.0.1", "aceite_motor", 3)
    print(f"    → {resp}")

    time.sleep(0.5)

    print("\n[6] Estado final de todos los negocios:")
    print(f"    Panadería    → {panaderia.inventario}")
    print(f"    Restaurante  → {restaurante.inventario}")
    print(f"    Supermercado → {supermercado.inventario}")
    print(f"    Taller       → {taller.inventario}")
    print("="*55 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# MENÚ
# ─────────────────────────────────────────────────────────────────────────────

def menu():
    print("""
Comandos disponibles:
  demo                          ejecutar demo de interacciones
  pan estado                    inventario de la panadería
  pan hacer <n>                 fabricar n panes
  res estado                    inventario del restaurante
  res bocadillo                 restaurante hace 1 bocadillo
  res tortilla                  restaurante hace 1 tortilla
  res pan <n>                   restaurante pide n panes a panadería
  super estado                  inventario del supermercado
  taller estado                 inventario del taller
  taller reparar [basica|ruedas]  reparar un coche
  ayuda                         mostrar este menú
  salir
""")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Añadir materiales de taller al inventario del supermercado
    supermercado = Supermercado(puerto=5002)
    supermercado.inventario.update({
        "aceite_motor": 20,
        "tornillos": 100,
        "ruedas": 8
    })

    panaderia   = Panaderia(puerto=5000)
    restaurante = Restaurante(puerto=5001)
    taller      = Taller(puerto=5003)

    # Arrancar los 4 servidores en hilos daemon
    arrancar(panaderia)
    arrancar(supermercado)
    arrancar(restaurante)
    arrancar(taller)
    time.sleep(0.5)

    print("╔══════════════════════════════════════════╗")
    print("║     BARRIO: La Comarca (todo en coche)   ║")
    print("╠══════════════════════════════════════════╣")
    print("║  Panadería    → 127.0.0.1:5000           ║")
    print("║  Restaurante  → 127.0.0.1:5001           ║")
    print("║  Supermercado → 127.0.0.1:5002           ║")
    print("║  Taller       → 127.0.0.1:5003           ║")
    print("╚══════════════════════════════════════════╝")

    menu()

    while True:
        try:
            cmd = input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print("\nCerrando el barrio...")
            break

        if not cmd:
            continue

        if cmd[0] == "demo":
            demo(panaderia, restaurante, supermercado, taller)

        elif cmd[0] == "pan":
            if len(cmd) < 2:
                menu()
            elif cmd[1] == "estado":
                print(panaderia.inventario)
            elif cmd[1] == "hacer" and len(cmd) >= 3:
                t = threading.Thread(target=lambda: print(panaderia.hacer_pan(int(cmd[2]))))
                t.start()

        elif cmd[0] == "res":
            if len(cmd) < 2:
                menu()
            elif cmd[1] == "estado":
                print(restaurante.inventario)
            elif cmd[1] == "bocadillo":
                t = threading.Thread(target=lambda: print(restaurante.hacer_bocadillo(1)))
                t.start()
            elif cmd[1] == "tortilla":
                t = threading.Thread(target=lambda: print(restaurante.hacer_tortilla(1)))
                t.start()
            elif cmd[1] == "pan" and len(cmd) >= 3:
                t = threading.Thread(target=lambda: print(restaurante.pedir_pan("127.0.0.1", int(cmd[2]))))
                t.start()

        elif cmd[0] == "super":
            if len(cmd) >= 2 and cmd[1] == "estado":
                print(supermercado.inventario)

        elif cmd[0] == "taller":
            if len(cmd) < 2:
                menu()
            elif cmd[1] == "estado":
                print(taller.inventario)
            elif cmd[1] == "reparar":
                tipo = cmd[2] if len(cmd) >= 3 else "basica"
                t = threading.Thread(target=lambda: print(taller.reparar_coche(tipo)))
                t.start()

        elif cmd[0] == "ayuda":
            menu()

        elif cmd[0] == "salir":
            print("Cerrando el barrio...")
            break

        else:
            print("Comando no reconocido. Escribe 'ayuda' para ver los comandos.")
