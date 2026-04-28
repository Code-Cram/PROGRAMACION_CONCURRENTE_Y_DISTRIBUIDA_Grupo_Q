"""
MUD: El Barrio - La Comarca
=============================
Motor basado en mud-pi (MudServer).
Conéctate con: telnet localhost 1234

Este MUD representa el barrio completo con 4 negocios distribuidos:
  - Panadería     (puerto 5000)
  - Restaurante   (puerto 5001)
  - Supermercado  (puerto 5002)
  - Taller        (puerto 5003)

Localizaciones del MUD:
  plaza → restaurante → cocina
        → taller
        → supermercado
        → panaderia

Comandos disponibles:
  mirar              - ver descripción del lugar actual
  ir <lugar>         - moverse entre localizaciones
  estado             - inventario del negocio actual
  carta              - carta del restaurante
  bocadillo          - hacer un bocadillo (en restaurante)
  tortilla           - hacer una tortilla (en restaurante)
  reparar <tipo>     - reparar coche: basica|ruedas (en taller)
  menu <n>           - taller pide menús al restaurante (en taller)
  comprar <producto> <n> - comprar al supermercado (en supermercado)
  pan <n>            - hacer pan (en panadería)
  ayuda              - ver este mensaje
  salir              - desconectarse

Interacciones distribuidas (entre calles):
  Restaurante → pide pan a Panadería (socket :5000)
  Restaurante → pide huevos a Supermercado (socket :5002)
  Taller      → pide materiales a Supermercado (socket :5002)
  Panadería   → pide harina/huevos a Supermercado (socket :5002)

Uso:
  python mud_barrio.py
"""

import time
import threading
from mudserver import MudServer
from panaderia import Panaderia
from restaurante import Restaurante
from super import Supermercado
from taller import Taller


# ─────────────────────────────────────────────────────────────────────────────
# MAPA DEL BARRIO
# ─────────────────────────────────────────────────────────────────────────────

LOCALIZACIONES = {
    "plaza": {
        "nombre": "Plaza del Barrio - La Comarca",
        "descripcion": (
            "Estás en la Plaza Central de La Comarca. Un barrio tranquilo con mucho carácter.\n"
            "A tu alrededor ves cuatro negocios que trabajan codo con codo.\n"
            "Aquí la economía fluye: el pan va del horno a la mesa, los coches se reparan\n"
            "y el supermercado abastece a todos.\n"
            "Salidas: restaurante, taller, supermercado, panaderia"
        ),
        "salidas": {
            "restaurante": "restaurante",
            "taller": "taller",
            "supermercado": "supermercado",
            "panaderia": "panaderia",
            "panadería": "panaderia"
        }
    },
    "restaurante": {
        "nombre": "Restaurante El Rincón",
        "descripcion": (
            "Estás en el Restaurante El Rincón. Mesas con manteles de cuadros,\n"
            "olor a cocina casera y el murmullo de la radio de fondo.\n"
            "El pan viene fresco de la Panadería cada mañana.\n"
            "Comandos aquí: carta, bocadillo, tortilla, estado\n"
            "Salidas: plaza, taller"
        ),
        "salidas": {
            "plaza": "plaza", "taller": "taller",
            "afuera": "plaza", "salir": "plaza"
        }
    },
    "taller": {
        "nombre": "Taller Mecánico El Piston",
        "descripcion": (
            "Estás en el Taller Mecánico El Piston. Olor a aceite, coches en los elevadores\n"
            "y cajas de herramientas por doquier.\n"
            "Los materiales llegan del Supermercado, y los trabajadores comen en el Restaurante.\n"
            "Comandos aquí: reparar basica, reparar ruedas, menu <n>, estado\n"
            "Salidas: plaza, restaurante"
        ),
        "salidas": {
            "plaza": "plaza", "restaurante": "restaurante",
            "afuera": "plaza", "salir": "plaza"
        }
    },
    "supermercado": {
        "nombre": "Supermercado La Despensa",
        "descripcion": (
            "Estás en el Supermercado La Despensa. Estanterías repletas de productos\n"
            "que abastecen a todos los negocios del barrio.\n"
            "La Panadería pide harina y huevos, el Restaurante compra ingredientes,\n"
            "el Taller se surte de aceite y tornillos.\n"
            "Comandos aquí: comprar <producto> <cantidad>, estado\n"
            "Salidas: plaza"
        ),
        "salidas": {"plaza": "plaza", "afuera": "plaza", "salir": "plaza"}
    },
    "panaderia": {
        "nombre": "Panadería El Horno",
        "descripcion": (
            "Estás en la Panadería El Horno. El calor del horno llega desde la trastienda\n"
            "y el olor a pan recién hecho impregna el ambiente.\n"
            "Cada mañana el Restaurante recoge su pedido aquí.\n"
            "Comandos aquí: pan <n>, estado\n"
            "Salidas: plaza"
        ),
        "salidas": {"plaza": "plaza", "afuera": "plaza", "salir": "plaza"}
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DEL JUEGO
# ─────────────────────────────────────────────────────────────────────────────

jugadores = {}   # id -> {"nombre": str, "lugar": str}


def bienvenida(mud, id_jugador):
    mud.send_message(id_jugador, "\r\n" + "="*54)
    mud.send_message(id_jugador, "   ¡Bienvenido al MUD: El Barrio - La Comarca!")
    mud.send_message(id_jugador, "="*54)
    mud.send_message(id_jugador, "¿Cómo te llamas, viajero?")


def enviar_descripcion(mud, id_jugador):
    lugar = jugadores[id_jugador]["lugar"]
    loc = LOCALIZACIONES[lugar]
    mud.send_message(id_jugador, "\r\n[" + loc["nombre"] + "]")
    mud.send_message(id_jugador, loc["descripcion"])


# ─────────────────────────────────────────────────────────────────────────────
# PROCESADO DE COMANDOS
# ─────────────────────────────────────────────────────────────────────────────

def procesar_comando(mud, id_jugador, cmd, params,
                     panaderia, restaurante, supermercado, taller):
    jugador = jugadores.get(id_jugador)
    if not jugador:
        return

    # Asignación de nombre al entrar
    if not jugador["nombre"]:
        nombre = cmd.strip()
        if not nombre:
            mud.send_message(id_jugador, "Por favor, dime tu nombre.")
            return
        jugador["nombre"] = nombre
        mud.send_message(id_jugador, f"\r\n¡Bienvenido, {nombre}! Disfruta del barrio.")
        enviar_descripcion(mud, id_jugador)
        return

    lugar = jugador["lugar"]

    # ── MIRAR ──────────────────────────────────────────────────────────────
    if cmd in ("mirar", "look", "l", "m"):
        enviar_descripcion(mud, id_jugador)

    # ── MOVERSE ────────────────────────────────────────────────────────────
    elif cmd in ("ir", "go", "mover", "ve"):
        destino = params.strip().lower()
        salidas = LOCALIZACIONES[lugar]["salidas"]
        if destino in salidas:
            jugador["lugar"] = salidas[destino]
            enviar_descripcion(mud, id_jugador)
        else:
            mud.send_message(id_jugador, f"No puedes ir a '{destino}' desde aquí.")
            mud.send_message(id_jugador, "Salidas: " + ", ".join(salidas.keys()))

    # ── AYUDA ──────────────────────────────────────────────────────────────
    elif cmd in ("ayuda", "help", "?"):
        mud.send_message(id_jugador, "\r\nComandos disponibles:")
        mud.send_message(id_jugador, "  mirar                    - describir el lugar actual")
        mud.send_message(id_jugador, "  ir <lugar>               - moverte entre localizaciones")
        mud.send_message(id_jugador, "  estado                   - inventario del negocio actual")
        mud.send_message(id_jugador, "  carta                    - ver carta (en restaurante)")
        mud.send_message(id_jugador, "  bocadillo                - hacer bocadillo (en restaurante)")
        mud.send_message(id_jugador, "  tortilla                 - hacer tortilla (en restaurante)")
        mud.send_message(id_jugador, "  reparar <basica|ruedas>  - reparar coche (en taller)")
        mud.send_message(id_jugador, "  menu <n>                 - pedir menús al restaurante (en taller)")
        mud.send_message(id_jugador, "  comprar <producto> <n>   - comprar al supermercado")
        mud.send_message(id_jugador, "  pan <n>                  - hacer pan (en panadería)")
        mud.send_message(id_jugador, "  ayuda                    - ver este mensaje")
        mud.send_message(id_jugador, "  salir                    - desconectarse")

    # ── ESTADO ─────────────────────────────────────────────────────────────
    elif cmd == "estado":
        negocios = {
            "restaurante": restaurante,
            "taller": taller,
            "supermercado": supermercado,
            "panaderia": panaderia
        }
        negocio = negocios.get(lugar)
        if negocio:
            mud.send_message(id_jugador, f"\r\nInventario — {LOCALIZACIONES[lugar]['nombre']}:")
            for k, v in negocio.inventario.items():
                mud.send_message(id_jugador, f"  {k}: {v}")
        else:
            mud.send_message(id_jugador, "Estás en la plaza, no hay inventario aquí.")

    # ── CARTA ──────────────────────────────────────────────────────────────
    elif cmd == "carta":
        if lugar == "restaurante":
            mud.send_message(id_jugador, "\r\nCarta del Restaurante El Rincón:")
            mud.send_message(id_jugador, "  Bocadillo  → 4€  (necesita pan de la Panadería)")
            mud.send_message(id_jugador, "  Tortilla   → 6€  (necesita 2 huevos del Supermercado)")
        else:
            mud.send_message(id_jugador, "La carta solo está disponible en el restaurante.")

    # ── BOCADILLO ──────────────────────────────────────────────────────────
    elif cmd == "bocadillo":
        if lugar == "restaurante":
            mud.send_message(id_jugador, "El cocinero se pone manos a la obra...")
            def hacer():
                resp = restaurante.hacer_bocadillo(1)
                if "ok" in resp:
                    mud.send_message(id_jugador, f"✓ {resp['ok']} — ¡Buen provecho!")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('error', 'Error')} (pidiendo pan a la Panadería...)")
            threading.Thread(target=hacer, daemon=True).start()
        else:
            mud.send_message(id_jugador, "Ve al restaurante para pedir un bocadillo.")

    # ── TORTILLA ───────────────────────────────────────────────────────────
    elif cmd == "tortilla":
        if lugar == "restaurante":
            mud.send_message(id_jugador, "El cocinero empieza a batir los huevos...")
            def hacer():
                resp = restaurante.hacer_tortilla(1)
                if "ok" in resp:
                    mud.send_message(id_jugador, f"✓ {resp['ok']}")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('error', 'Error')} (pidiendo huevos al Supermercado...)")
            threading.Thread(target=hacer, daemon=True).start()
        else:
            mud.send_message(id_jugador, "Ve al restaurante para pedir una tortilla.")

    # ── REPARAR ────────────────────────────────────────────────────────────
    elif cmd == "reparar":
        if lugar == "taller":
            tipo = params.strip().lower() or "basica"
            if tipo not in ("basica", "ruedas"):
                mud.send_message(id_jugador, "Tipos: basica (50€) | ruedas (120€)")
                return
            precios = {"basica": 50, "ruedas": 120}
            mud.send_message(id_jugador, f"Reparación '{tipo}' iniciada — {precios[tipo]}€")
            def reparar():
                resp = taller.reparar_coche(tipo)
                if "ok" in resp:
                    mud.send_message(id_jugador, f"✓ {resp['ok']}")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('error', 'Faltan materiales')} (pidiendo al Supermercado...)")
            threading.Thread(target=reparar, daemon=True).start()
        else:
            mud.send_message(id_jugador, "Ve al taller para reparar un coche.")

    # ── MENU (taller → restaurante) ────────────────────────────────────────
    elif cmd in ("menu", "menú"):
        if lugar == "taller":
            try:
                cantidad = int(params.strip()) if params.strip() else 2
            except ValueError:
                cantidad = 2
            mud.send_message(id_jugador, f"El taller pide {cantidad} menú(s) al Restaurante El Rincón...")
            def pedir():
                resp = taller.pedir_menu("127.0.0.1", cantidad)
                if resp.get("ok"):
                    mud.send_message(id_jugador, f"✓ {resp['ok']} — Total: {resp.get('precio','?')}€")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('error', 'Sin respuesta del restaurante')}")
            threading.Thread(target=pedir, daemon=True).start()
        else:
            mud.send_message(id_jugador, "El comando 'menu' está disponible en el taller.")

    # ── COMPRAR (supermercado) ─────────────────────────────────────────────
    elif cmd == "comprar":
        if lugar == "supermercado":
            partes = params.strip().split()
            if len(partes) < 2:
                mud.send_message(id_jugador, "Uso: comprar <producto> <cantidad>")
                mud.send_message(id_jugador, "Productos: harina, huevos, leche, manzanas, azucar, aceite_motor, tornillos, ruedas")
                return
            producto = partes[0]
            try:
                cantidad = int(partes[1])
            except ValueError:
                mud.send_message(id_jugador, "La cantidad debe ser un número.")
                return
            mud.send_message(id_jugador, f"Comprando {cantidad}x {producto}...")
            def comprar():
                resp = supermercado.vender_producto(producto, cantidad)
                if resp.get("estado") == "ok":
                    mud.send_message(id_jugador, f"✓ {resp['mensaje']}")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('mensaje', 'Error')}")
            threading.Thread(target=comprar, daemon=True).start()
        else:
            mud.send_message(id_jugador, "Ve al supermercado para comprar productos.")

    # ── PAN (panadería) ────────────────────────────────────────────────────
    elif cmd == "pan":
        if lugar == "panaderia":
            try:
                cantidad = int(params.strip()) if params.strip() else 3
            except ValueError:
                cantidad = 3
            mud.send_message(id_jugador, f"El panadero empieza a hornear {cantidad} pan(es)...")
            def hornear():
                resp = panaderia.hacer_pan(cantidad)
                if "ok" in resp:
                    mud.send_message(id_jugador, f"✓ {resp['ok']}")
                else:
                    mud.send_message(id_jugador, f"✗ {resp.get('error', 'Error')} (pidiendo ingredientes al Supermercado...)")
            threading.Thread(target=hornear, daemon=True).start()
        else:
            mud.send_message(id_jugador, "Ve a la panadería para hacer pan.")

    # ── SALIR ──────────────────────────────────────────────────────────────
    elif cmd in ("salir", "quit", "exit", "bye", "adios", "adiós"):
        nombre = jugador["nombre"]
        mud.send_message(id_jugador, f"¡Hasta pronto, {nombre}! La Comarca te espera.")

    # ── DESCONOCIDO ────────────────────────────────────────────────────────
    else:
        mud.send_message(id_jugador, f"No entiendo '{cmd}'. Escribe 'ayuda' para ver los comandos.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Inicializar negocios con stock inicial
    supermercado = Supermercado(puerto=5002)
    supermercado.inventario.update({
        "aceite_motor": 20, "tornillos": 100, "ruedas": 8
    })

    panaderia   = Panaderia(puerto=5000)
    restaurante = Restaurante(puerto=5001)
    taller      = Taller(puerto=5003)

    panaderia.inventario["huevos"] = 10   # stock inicial
    restaurante.inventario["pan"] = 5

    # Arrancar los 4 servidores de sockets (interacciones entre calles)
    threading.Thread(target=panaderia.iniciar_servidor,   args=("0.0.0.0",), daemon=True).start()
    threading.Thread(target=supermercado.iniciar_servidor, args=("0.0.0.0",), daemon=True).start()
    threading.Thread(target=restaurante.iniciar_servidor,  args=("0.0.0.0",), daemon=True).start()
    threading.Thread(target=taller.iniciar_servidor,       args=("0.0.0.0",), daemon=True).start()
    time.sleep(0.3)

    # Arrancar el motor MUD (mud-pi)
    mud = MudServer()

    print("╔══════════════════════════════════════════════╗")
    print("║      MUD: El Barrio - La Comarca             ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  Panadería    → 0.0.0.0:5000                ║")
    print("║  Restaurante  → 0.0.0.0:5001                ║")
    print("║  Supermercado → 0.0.0.0:5002                ║")
    print("║  Taller       → 0.0.0.0:5003                ║")
    print("║  MUD Telnet   → 0.0.0.0:1234                ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  Conéctate: telnet localhost 1234            ║")
    print("╚══════════════════════════════════════════════╝")

    while True:
        mud.update()

        for id_jugador in mud.get_new_players():
            jugadores[id_jugador] = {"nombre": "", "lugar": "plaza"}
            bienvenida(mud, id_jugador)

        for id_jugador in mud.get_disconnected_players():
            jugador = jugadores.pop(id_jugador, None)
            if jugador and jugador["nombre"]:
                print(f"[MUD] {jugador['nombre']} se ha desconectado.")

        for id_jugador, cmd, params in mud.get_commands():
            procesar_comando(mud, id_jugador, cmd, params,
                             panaderia, restaurante, supermercado, taller)

        time.sleep(0.1)
