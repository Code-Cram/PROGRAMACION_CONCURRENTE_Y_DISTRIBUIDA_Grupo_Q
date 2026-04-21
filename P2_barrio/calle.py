"""
La Comarca - Fase 1: Calle de los Artesanos
Herreria + Carpinteria

Uso: python calle.py
"""

import multiprocessing
import queue
import time

from catalogos import (
    CATALOGO_HERRERIA, CATALOGO_HERRERIA_INTER,
    CATALOGO_CARPINTERIA, CATALOGO_CARPINTERIA_INTER,
)
from comercio import iniciar_comercio


# --- ESTADO DEL JUGADOR ---

JUGADOR = {
    "nombre": "Aventurero",
    "monedas": 200,
    "inventario": [],
    "ubicacion": "calle",
}

contador_pedidos = 0


# --- HELPERS DE INTERFAZ ---

def limpiar_cola(cola):
    mensajes = []
    while True:
        try:
            mensajes.append(cola.get_nowait())
        except queue.Empty:
            break
    return mensajes


def mostrar_catalogo(cola_pedidos, cola_respuestas):
    cola_pedidos.put({"tipo": "ver_catalogo"})
    try:
        resp = cola_respuestas.get(timeout=10)
        if resp["tipo"] == "catalogo":
            print(f"\n  {resp['comercio']} - Catalogo:\n")
            for pid, info in resp["productos"].items():
                stock = f" [{info['disponible']} listos]" if info["disponible"] > 0 else ""
                print(f"    {pid:15s}  {info['nombre']:32s} {info['precio']:3d} monedas  ({info['tiempo']}s){stock}")
            print()
    except queue.Empty:
        print("  (El comerciante no responde...)")


def comprar_producto(cola_pedidos, cola_respuestas):
    global contador_pedidos
    producto = input("  Que quieres comprar? (id del producto): ").strip().lower()
    if not producto:
        return

    contador_pedidos += 1
    cola_pedidos.put({"tipo": "comprar", "producto": producto, "pedido_id": contador_pedidos})

    try:
        resp = cola_respuestas.get(timeout=30)
        tipo = resp["tipo"]

        if tipo == "error":
            print(f"\n  {resp['mensaje']}")

        elif tipo == "compra_exitosa":
            precio = resp["precio"]
            if JUGADOR["monedas"] >= precio:
                JUGADOR["monedas"] -= precio
                JUGADOR["inventario"].append(resp["nombre"])
                print(f"\n  {resp['mensaje']}")
                print(f"  Pagaste {precio} monedas. Te quedan {JUGADOR['monedas']}.")
            else:
                print(f"\n  No tienes suficientes monedas ({precio} necesarias, tienes {JUGADOR['monedas']}).")

        elif tipo == "pedido_aceptado":
            print(f"\n  {resp['mensaje']}")
            if input("  Quieres esperar? (s/n): ").strip().lower() == "s":
                print("  Esperando...")
                try:
                    resp2 = cola_respuestas.get(timeout=resp["tiempo"] + 5)
                    if resp2["tipo"] == "produccion_completa":
                        precio = resp2["precio"]
                        if JUGADOR["monedas"] >= precio:
                            JUGADOR["monedas"] -= precio
                            JUGADOR["inventario"].append(resp2["nombre"])
                            print(f"\n  {resp2['nombre']} listo. Pagas {precio} monedas. Te quedan {JUGADOR['monedas']}.")
                        else:
                            print(f"\n  No tienes {precio} monedas. El producto vuelve al estante.")
                except queue.Empty:
                    print("  (Tardara mas de lo esperado, vuelve luego.)")
            else:
                print("  De acuerdo, vuelve cuando este listo.")

    except queue.Empty:
        print("  (El comerciante esta ocupado...)")


def ver_inventario_comercio(cola_pedidos, cola_respuestas):
    cola_pedidos.put({"tipo": "ver_inventario"})
    try:
        resp = cola_respuestas.get(timeout=10)
        if resp["tipo"] == "inventario":
            print("\n  Inventario del comercio:")
            print("    Materias primas:")
            for m, c in resp["materias"].items():
                print(f"      {m}: {c}")
            print("    Productos terminados:")
            terminados = {p: c for p, c in resp["productos"].items() if c > 0}
            if terminados:
                for p, c in terminados.items():
                    print(f"      {p}: {c}")
            else:
                print("      (ninguno)")
            print(f"    Caja: {resp['monedas']} monedas\n")
    except queue.Empty:
        print("  (Sin respuesta...)")


def ver_estado_jugador():
    print(f"\n  {JUGADOR['nombre']}")
    print(f"  Monedas: {JUGADOR['monedas']}")
    print(f"  Ubicacion: {JUGADOR['ubicacion']}")
    print("  Inventario:", ", ".join(JUGADOR["inventario"]) if JUGADOR["inventario"] else "(vacio)")
    print()


def menu_comercio(cola_pedidos, cola_respuestas, nombre):
    OPCIONES = {
        "1": ("Ver catalogo",             lambda: mostrar_catalogo(cola_pedidos, cola_respuestas)),
        "2": ("Comprar producto",         lambda: comprar_producto(cola_pedidos, cola_respuestas)),
        "3": ("Ver inventario comercio",  lambda: ver_inventario_comercio(cola_pedidos, cola_respuestas)),
        "4": ("Ver mi estado",            ver_estado_jugador),
        "5": ("Salir a la calle",         None),
    }
    while True:
        for msg in limpiar_cola(cola_respuestas):
            if msg.get("tipo") == "produccion_completa":
                print(f"\n  *** {msg['nombre']} esta listo para recoger! ***")

        print(f"\n  --- {nombre} ---")
        for clave, (texto, _) in OPCIONES.items():
            print(f"  {clave}. {texto}")
        print()

        opcion = input("  > ").strip()
        if opcion == "5":
            JUGADOR["ubicacion"] = "calle"
            print("\n  Sales a la calle.")
            return
        if opcion in OPCIONES:
            OPCIONES[opcion][1]()
        else:
            print("  Opcion no valida.")


# --- MAIN ---

def main():
    print("La Comarca - Calle de los Artesanos")
    print("Herreria | Carpinteria\n")

    # 8 colas: 2 jugador<->herreria, 2 jugador<->carpinteria, 4 inter-comercio
    cola_ped_h  = multiprocessing.Queue()
    cola_res_h  = multiprocessing.Queue()
    cola_ped_c  = multiprocessing.Queue()
    cola_res_c  = multiprocessing.Queue()
    cola_h2c    = multiprocessing.Queue()   # herreria pide a carpinteria
    cola_rc2h   = multiprocessing.Queue()   # carpinteria responde a herreria
    cola_c2h    = multiprocessing.Queue()   # carpinteria pide a herreria
    cola_rh2c   = multiprocessing.Queue()   # herreria responde a carpinteria

    proc_h = multiprocessing.Process(
        target=iniciar_comercio,
        args=(
            "Herreria",
            CATALOGO_HERRERIA,
            CATALOGO_HERRERIA_INTER,
            {"lingote_hierro": 20, "mango_madera": 5, "tablon": 3},
            100,
            cola_ped_h, cola_res_h,
            cola_c2h, cola_rh2c,      # recibe pedidos del carpintero / responde al carpintero
            cola_h2c, cola_rc2h,      # pide al carpintero / recibe respuesta del carpintero
            {"mango_madera", "tablon"},
        ),
        daemon=True,
    )
    proc_c = multiprocessing.Process(
        target=iniciar_comercio,
        args=(
            "Carpinteria",
            CATALOGO_CARPINTERIA,
            CATALOGO_CARPINTERIA_INTER,
            {"tronco": 15, "tablon": 10, "clavos": 5, "bisagras": 2, "lingote_hierro": 0},
            80,
            cola_ped_c, cola_res_c,
            cola_h2c, cola_rc2h,      # recibe pedidos del herrero / responde al herrero
            cola_c2h, cola_rh2c,      # pide al herrero / recibe respuesta del herrero
            {"clavos", "bisagras", "lingote_hierro"},
        ),
        daemon=True,
    )

    proc_h.start()
    proc_c.start()
    print(f"Herreria abierta   (PID: {proc_h.pid})")
    print(f"Carpinteria abierta (PID: {proc_c.pid})")
    time.sleep(0.5)

    nombre = input("\n  Como te llamas? ").strip()
    if nombre:
        JUGADOR["nombre"] = nombre
    print(f"\n  Bienvenido a la Comarca, {JUGADOR['nombre']}.")
    print(f"  Llevas {JUGADOR['monedas']} monedas.")
    print(f"  Estas en la Calle de los Artesanos.")
    print(f"  A un lado esta la Herreria, al otro la Carpinteria.\n")

    DESTINOS = {
        "1": ("Herreria",    cola_ped_h, cola_res_h),
        "2": ("Carpinteria", cola_ped_c, cola_res_c),
    }

    try:
        while True:
            print("  Que quieres hacer?")
            print("  1. Entrar en la Herreria")
            print("  2. Entrar en la Carpinteria")
            print("  3. Ver mi estado")
            print("  4. Mirar alrededor")
            print("  5. Salir del juego")
            print()
            opcion = input("  > ").strip()

            if opcion in DESTINOS:
                nombre_dest, cola_p, cola_r = DESTINOS[opcion]
                JUGADOR["ubicacion"] = nombre_dest.lower()
                print(f"\n  Entras en la {nombre_dest}.")
                menu_comercio(cola_p, cola_r, nombre_dest)
                print("\n  Vuelves a la calle.\n")
            elif opcion == "3":
                ver_estado_jugador()
            elif opcion == "4":
                print("\n  Estas en la Calle de los Artesanos.")
                print("  A un lado esta la Herreria, al otro la Carpinteria.\n")
            elif opcion == "5":
                print(f"\n  Hasta pronto, {JUGADOR['nombre']}.")
                break
            else:
                print("  Opcion no valida.")

    except KeyboardInterrupt:
        pass
    finally:
        cola_ped_h.put({"tipo": "cerrar"})
        cola_ped_c.put({"tipo": "cerrar"})
        time.sleep(0.3)
        proc_h.terminate()
        proc_c.terminate()


if __name__ == "__main__":
    main()
