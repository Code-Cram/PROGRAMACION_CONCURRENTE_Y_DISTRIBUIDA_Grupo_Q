"""
PUEBLO: El Rincón — Juego Terminal Distribuido
==============================================
Integra 2 barrios (10 comercios) con un Economato central vía Pyro5 RMI.

Uso:
  python pueblo.py

Requisitos:
  pip install Pyro5
"""

import sys
import os
import time
import threading
import Pyro5.api
import Pyro5.server

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')

from economato import Economato
from barrio_rmi import BarrioRMI
from tiendas_comarca import crear_comarca
from tiendas_avenida import crear_avenida

# ─────────────────────────────────────────────────────────────────────────────
# PYRO5: ARRANQUE DE SERVICIOS
# ─────────────────────────────────────────────────────────────────────────────

_pyro_daemon = None

def arrancar_nameserver():
    """Arranca el Pyro5 Name Server en un hilo daemon."""
    import Pyro5.nameserver
    try:
        Pyro5.nameserver.start_ns_loop(host="localhost", port=9090)
    except OSError:
        pass  # Ya estaba levantado


def _esperar_nameserver(intentos=10):
    """Espera a que el Name Server esté listo."""
    for i in range(intentos):
        try:
            ns = Pyro5.api.locate_ns(host="localhost", port=9090)
            return ns
        except Exception:
            time.sleep(0.5)
    return None


def registrar_en_pyro(obj, nombre):
    """Registra un objeto en el daemon Pyro5 y en el Name Server."""
    global _pyro_daemon
    try:
        ns = _esperar_nameserver()
        if not ns:
            print(f"  [WARN] Name Server no disponible para '{nombre}'")
            return None
        if _pyro_daemon is None:
            _pyro_daemon = Pyro5.server.Daemon()
            threading.Thread(target=_pyro_daemon.requestLoop, daemon=True).start()
        uri = _pyro_daemon.register(obj)
        ns.register(nombre, uri)
        return str(uri)
    except Exception as e:
        print(f"[ERROR PYRO] No se pudo registrar '{nombre}': {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# INTER-BARRIO: COMERCIO AUTOMÁTICO
# ─────────────────────────────────────────────────────────────────────────────

def comercio_inter_barrio(tiendas_comarca, tiendas_avenida, economato):
    """
    Hilo daemon que gestiona las transacciones automáticas entre barrios.
    Cada cierto tiempo, las tiendas compran lo que necesitan del otro barrio.
    """
    while True:
        time.sleep(15)
        try:
            # Carpintería (LavaCejas) necesita clavos/bisagras de Herrería (LavaBocas)
            carp = tiendas_comarca["carpinteria"]
            with carp.lock:
                pocos_clavos = carp.inventario.get("clavos", 0) < 3
                pocas_bisagras = carp.inventario.get("bisagras", 0) < 2
            if pocos_clavos:
                r = economato.comprar_inter_barrio(
                    "La Calle LavaCejas.carpinteria", "La Calle LavaBocas", "clavos", 5)
                if "ok" in r:
                    with carp.lock:
                        carp.inventario["clavos"] = carp.inventario.get("clavos", 0) + 5
                        carp.caja -= r["precio_final"]
                    print(f"  [INTER-BARRIO] Carpintería compró clavos a Herrería (+5)")
            if pocas_bisagras:
                r = economato.comprar_inter_barrio(
                    "La Calle LavaCejas.carpinteria", "La Calle LavaBocas", "bisagras", 2)
                if "ok" in r:
                    with carp.lock:
                        carp.inventario["bisagras"] = carp.inventario.get("bisagras", 0) + 2
                        carp.caja -= r["precio_final"]
                    print(f"  [INTER-BARRIO] Carpintería compró bisagras a Herrería (+2)")

            # Herrería (LavaBocas) necesita mango_madera de Carpintería (LavaCejas)
            herr = tiendas_avenida["herreria"]
            with herr.lock:
                pocos_mangos = herr.inventario.get("mango_madera", 0) < 2
            if pocos_mangos:
                r = economato.comprar_inter_barrio(
                    "La Calle LavaBocas.herreria", "La Calle LavaCejas", "mango_madera", 3)
                if "ok" in r:
                    with herr.lock:
                        herr.inventario["mango_madera"] = herr.inventario.get("mango_madera", 0) + 3
                        herr.caja -= r["precio_final"]
                    print(f"  [INTER-BARRIO] Herrería compró mangos a Carpintería (+3)")

            # Restaurante (LavaCejas) compra frutas de Frutería (LavaBocas)
            rest = tiendas_comarca["restaurante"]
            r = economato.comprar_inter_barrio(
                "La Calle LavaCejas.restaurante", "La Calle LavaBocas", "apple", 3)
            if "ok" in r:
                with rest.lock:
                    rest.inventario["apple"] = rest.inventario.get("apple", 0) + 3
                    rest.caja -= r["precio_final"]

        except Exception as e:
            pass  # Silenciar errores del hilo de fondo


# ─────────────────────────────────────────────────────────────────────────────
# MAPA DE LOCALIZACIONES
# ─────────────────────────────────────────────────────────────────────────────

def construir_mapa(tiendas_comarca, tiendas_avenida):
    """Construye el mapa de localizaciones del juego."""
    mapa = {
        "plaza": {
            "nombre": "Plaza Mayor — Economato Central",
            "descripcion": (
                "Estás en la Plaza Mayor del pueblo El Rincón.\n"
                "El Economato Central gestiona el comercio entre barrios.\n"
                "A un lado ves el barrio de La Calle LavaCejas, al otro La Calle LavaBocas.\n"
                "\n  Salidas: lavacejas, lavabocas"
            ),
            "salidas": {"lavacejas": "comarca", "lavabocas": "avenida"},
            "tienda": None,
        },
        "comarca": {
            "nombre": "Barrio La Calle LavaCejas",
            "descripcion": (
                "Estás en el barrio La Calle LavaCejas. Un barrio animado\n"
                "donde el pan va del horno a la mesa y los coches se reparan.\n"
                "\n  Comercios: panaderia, restaurante, supermercado, taller, carpinteria"
                "\n  Salidas: plaza"
            ),
            "salidas": {
                "plaza": "plaza",
                "panaderia": "comarca_panaderia",
                "restaurante": "comarca_restaurante",
                "supermercado": "comarca_supermercado",
                "taller": "comarca_taller",
                "carpinteria": "comarca_carpinteria",
            },
            "tienda": None,
        },
        "avenida": {
            "nombre": "Barrio La Calle LavaBocas",
            "descripcion": (
                "Estás en el barrio La Calle LavaBocas. Frutas frescas, helados\n"
                "artesanales y el golpeteo del martillo de la Herrería.\n"
                "\n  Comercios: fruteria, heladeria, supermercado, herreria, panaderia"
                "\n  Salidas: plaza"
            ),
            "salidas": {
                "plaza": "plaza",
                "fruteria": "avenida_fruteria",
                "heladeria": "avenida_heladeria",
                "supermercado": "avenida_supermercado",
                "herreria": "avenida_herreria",
                "panaderia": "avenida_panaderia",
            },
            "tienda": None,
        },
    }

    # Generar localizaciones de tiendas de La Calle LavaCejas
    for clave, tienda in tiendas_comarca.items():
        loc_id = f"comarca_{clave}"
        barrio_key = "comarca"
        mapa[loc_id] = {
            "nombre": tienda.nombre,
            "descripcion": tienda.descripcion + "\n\n  Salidas: barrio (volver al barrio)",
            "salidas": {"barrio": barrio_key, "salir": barrio_key,
                        "atras": barrio_key, "plaza": "plaza"},
            "tienda": tienda,
            "barrio": "La Calle LavaCejas",
        }

    # Generar localizaciones de tiendas de La Calle LavaBocas
    for clave, tienda in tiendas_avenida.items():
        loc_id = f"avenida_{clave}"
        barrio_key = "avenida"
        mapa[loc_id] = {
            "nombre": tienda.nombre,
            "descripcion": tienda.descripcion + "\n\n  Salidas: barrio (volver al barrio)",
            "salidas": {"barrio": barrio_key, "salir": barrio_key,
                        "atras": barrio_key, "plaza": "plaza"},
            "tienda": tienda,
            "barrio": "La Calle LavaBocas",
        }

    return mapa


# ─────────────────────────────────────────────────────────────────────────────
# JUEGO TERMINAL
# ─────────────────────────────────────────────────────────────────────────────

AYUDA = """
  Comandos disponibles:
  ─────────────────────────────────────────────────────────
  mirar                           - ver dónde estás
  ir <lugar>                      - moverte entre localizaciones
  catalogo                        - productos de la tienda actual
  catalogo pueblo                 - catálogo de TODO el pueblo
  comprar <producto> <cantidad>   - comprar producto local
  importar <producto> <cantidad>  - comprar de OTRO barrio (Pyro5 RMI)
  estado                          - tu inventario y dinero
  economato                       - resumen del economato central
  historial                       - historial de transacciones inter-barrio
  ayuda                           - ver este mensaje
  salir                           - salir del juego
"""


def juego(mapa, economato):
    """Bucle principal del juego terminal."""

    jugador = {
        "nombre": "",
        "monedas": 100.0,
        "inventario": {},
        "ubicacion": "plaza",
    }

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           PUEBLO Villaviciosa De Ron — Juego Terminal                ║")
    print("║       2 barrios · 10 comercios · Economato Pyro5 RMI      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    nombre = input("  ¿Cómo te llamas, viajero? > ").strip()
    if not nombre:
        nombre = "Aventurero"
    jugador["nombre"] = nombre

    print(f"\n  ¡Bienvenido al pueblo, {nombre}!")
    print(f"  Llevas {jugador['monedas']} monedas.")
    print("  Escribe 'ayuda' para ver los comandos.\n")

    loc = mapa[jugador["ubicacion"]]
    print(f"  [{loc['nombre']}]")
    print(f"  {loc['descripcion']}\n")

    while True:
        try:
            cmd_raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  ¡Hasta pronto!")
            break

        if not cmd_raw:
            continue

        partes = cmd_raw.split()
        cmd = partes[0].lower()
        args = partes[1:]
        loc = mapa[jugador["ubicacion"]]

        # ── MIRAR ────────────────────────────────────────────────────
        if cmd in ("mirar", "look", "m"):
            print(f"\n  [{loc['nombre']}]")
            print(f"  {loc['descripcion']}\n")

        # ── IR ───────────────────────────────────────────────────────
        elif cmd in ("ir", "go", "ve"):
            if not args:
                print("  ¿A dónde? Salidas:", ", ".join(loc["salidas"].keys()))
                continue
            destino = args[0].lower()
            if destino in loc["salidas"]:
                jugador["ubicacion"] = loc["salidas"][destino]
                nueva_loc = mapa[jugador["ubicacion"]]
                print(f"\n  [{nueva_loc['nombre']}]")
                print(f"  {nueva_loc['descripcion']}\n")
            else:
                print(f"  No puedes ir a '{destino}'. Salidas: {', '.join(loc['salidas'].keys())}")

        # ── CATÁLOGO ─────────────────────────────────────────────────
        elif cmd in ("catalogo", "catálogo", "cat"):
            if args and args[0].lower() == "pueblo":
                print("\n  ╔═══ CATÁLOGO GLOBAL DEL PUEBLO ═══╗")
                cat_global = economato.catalogo_global()
                for barrio_n, cat in cat_global.items():
                    print(f"\n  ── {barrio_n} ──")
                    if isinstance(cat, dict) and "error" not in cat:
                        for prod, info in cat.items():
                            print(f"    {prod:20s} {info['precio']:6.2f}€  "
                                  f"[{info['stock']} uds] ({info['tienda']})")
                    else:
                        print(f"    (sin datos)")
                print()
            else:
                tienda = loc.get("tienda")
                if tienda:
                    cat = tienda.catalogo()
                    print(f"\n  Catálogo — {tienda.nombre}:")
                    print(f"  {'Producto':20s} {'Precio':>8s}  {'Stock':>6s}")
                    print(f"  {'─'*38}")
                    for prod, info in cat.items():
                        if prod in tienda.precios_venta:
                            print(f"  {prod:20s} {info['precio']:7.2f}€  "
                                  f"[{info['stock']:4d}]")
                    print()
                else:
                    print("  No hay tienda aquí. Entra en un comercio primero.")

        # ── COMPRAR ──────────────────────────────────────────────────
        elif cmd == "comprar":
            tienda = loc.get("tienda")
            if not tienda:
                print("  No hay tienda aquí. Entra en un comercio primero.")
                continue
            if len(args) < 2:
                print("  Uso: comprar <producto> <cantidad>")
                continue
            producto = args[0].lower()
            try:
                cantidad = int(args[1])
            except ValueError:
                print("  La cantidad debe ser un número.")
                continue

            cat = tienda.catalogo()
            if producto not in tienda.precios_venta:
                print(f"  '{producto}' no se vende aquí.")
                continue
            precio_total = tienda.precios_venta[producto] * cantidad
            if jugador["monedas"] < precio_total:
                print(f"  No tienes suficiente dinero. Cuesta {precio_total:.2f}€"
                      f" y tienes {jugador['monedas']:.2f}€.")
                continue

            resultado = tienda.vender(producto, cantidad)
            if "ok" in resultado:
                jugador["monedas"] -= resultado["total"]
                jugador["inventario"][producto] = (
                    jugador["inventario"].get(producto, 0) + cantidad)
                print(f"  ✓ Comprados {cantidad}x {producto} por {resultado['total']:.2f}€."
                      f" Te quedan {jugador['monedas']:.2f}€.")
            else:
                print(f"  ✗ {resultado.get('error', 'Error')}")

        # ── IMPORTAR (compra inter-barrio vía Pyro5 RMI) ────────────
        elif cmd == "importar":
            if len(args) < 2:
                print("  Uso: importar <producto> <cantidad>")
                print("  Compra un producto del OTRO barrio vía Economato (Pyro5 RMI).")
                continue
            producto = args[0].lower()
            try:
                cantidad = int(args[1])
            except ValueError:
                print("  La cantidad debe ser un número.")
                continue

            # Determinar barrio actual y barrio contrario
            barrio_actual = loc.get("barrio", "")
            if not barrio_actual:
                # Estamos en plaza o hub de barrio, deducir del contexto
                ub = jugador["ubicacion"]
                if ub.startswith("comarca"):
                    barrio_actual = "La Calle LavaCejas"
                elif ub.startswith("avenida"):
                    barrio_actual = "La Calle LavaBocas"
                else:
                    print("  Debes estar en un barrio o tienda para importar.")
                    continue

            barrio_otro = "La Calle LavaBocas" if barrio_actual == "La Calle LavaCejas" else "La Calle LavaCejas"
            comprador_id = f"{barrio_actual}.{jugador['nombre']}"

            print(f"  Solicitando {cantidad}x {producto} de {barrio_otro} vía Economato (RMI)...")
            resultado = economato.comprar_inter_barrio(
                comprador_id, barrio_otro, producto, cantidad)

            if "ok" in resultado:
                precio = resultado["precio_final"]
                if jugador["monedas"] >= precio:
                    jugador["monedas"] -= precio
                    jugador["inventario"][producto] = (
                        jugador["inventario"].get(producto, 0) + cantidad)
                    print(f"  ✓ Importados {cantidad}x {producto} de {barrio_otro}.")
                    print(f"    Precio: {resultado['total']:.2f}€ + "
                          f"comisión: {resultado['comision']:.2f}€ = "
                          f"{precio:.2f}€")
                    print(f"    Te quedan {jugador['monedas']:.2f}€.")
                else:
                    print(f"  ✗ No tienes {precio:.2f}€ (tienes {jugador['monedas']:.2f}€).")
            else:
                print(f"  ✗ {resultado.get('error', 'Error')}")

        # ── ESTADO ───────────────────────────────────────────────────
        elif cmd == "estado":
            print(f"\n  {jugador['nombre']}")
            print(f"  Monedas: {jugador['monedas']:.2f}€")
            print(f"  Ubicación: {loc['nombre']}")
            inv = jugador["inventario"]
            if inv:
                print("  Inventario:")
                for p, c in inv.items():
                    print(f"    {p}: {c}")
            else:
                print("  Inventario: (vacío)")
            print()

        # ── ECONOMATO ────────────────────────────────────────────────
        elif cmd == "economato":
            resumen = economato.resumen()
            print(f"\n  ╔═══ ECONOMATO CENTRAL ═══╗")
            print(f"  Barrios: {', '.join(resumen['barrios_registrados'])}")
            print(f"  Transacciones totales: {resumen['num_transacciones']}")
            print(f"  Comisiones recaudadas: {resumen['comision_total']:.2f}€")
            if resumen["cuentas"]:
                print(f"  Cuentas:")
                for c, s in resumen["cuentas"].items():
                    print(f"    {c}: {s:.2f}€")
            print()

        # ── HISTORIAL ────────────────────────────────────────────────
        elif cmd == "historial":
            hist = economato.historial()
            if not hist:
                print("  No hay transacciones inter-barrio todavía.")
            else:
                print(f"\n  Historial de transacciones inter-barrio:")
                print(f"  {'─'*60}")
                for i, t in enumerate(hist[-10:], 1):  # últimas 10
                    print(f"  {i}. [{t['timestamp']}] {t['comprador']} ← "
                          f"{t['cantidad']}x{t['producto']} de {t['barrio_vendedor']} "
                          f"({t['precio_final']:.2f}€)")
                print()

        # ── AYUDA ────────────────────────────────────────────────────
        elif cmd in ("ayuda", "help", "?"):
            print(AYUDA)

        # ── SALIR ────────────────────────────────────────────────────
        elif cmd in ("salir", "quit", "exit"):
            print(f"\n  ¡Hasta pronto, {jugador['nombre']}! El pueblo te espera.")
            break

        # ── DESCONOCIDO ──────────────────────────────────────────────
        else:
            print(f"  No entiendo '{cmd}'. Escribe 'ayuda' para ver los comandos.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n  Iniciando Pueblo Villaviciosa De Ron...")
    print("  ─────────────────────────────")

    # 1) Arrancar Name Server Pyro5
    print("  [1/5] Arrancando Pyro5 Name Server...")
    threading.Thread(target=arrancar_nameserver, daemon=True).start()
    time.sleep(1.5)

    # 2) Crear tiendas de cada barrio
    print("  [2/5] Creando tiendas...")
    tiendas_comarca = crear_comarca()
    tiendas_avenida = crear_avenida()

    # 3) Arrancar producción automática
    print("  [3/5] Iniciando producción automática...")
    for t in tiendas_comarca.values():
        t.iniciar_produccion()
    for t in tiendas_avenida.values():
        t.iniciar_produccion()

    # 4) Registrar barrios en Pyro5
    print("  [4/5] Registrando barrios en Pyro5 RMI...")
    economato = Economato()
    barrio1_rmi = BarrioRMI("La Calle LavaCejas", tiendas_comarca)
    barrio2_rmi = BarrioRMI("La Calle LavaBocas", tiendas_avenida)

    uri_eco = registrar_en_pyro(economato, "pueblo.economato")
    uri_b1 = registrar_en_pyro(barrio1_rmi, "pueblo.barrio.comarca")
    uri_b2 = registrar_en_pyro(barrio2_rmi, "pueblo.barrio.avenida")

    if uri_b1:
        economato.registrar_barrio("La Calle LavaCejas", uri_b1)
    if uri_b2:
        economato.registrar_barrio("La Calle LavaBocas", uri_b2)

    # 5) Arrancar comercio inter-barrio automático
    print("  [5/5] Iniciando comercio inter-barrio...")
    threading.Thread(
        target=comercio_inter_barrio,
        args=(tiendas_comarca, tiendas_avenida, economato),
        daemon=True
    ).start()

    time.sleep(0.5)
    print("\n  ✓ Pueblo listo. ¡A jugar!\n")

    # Construir mapa y lanzar el juego
    mapa = construir_mapa(tiendas_comarca, tiendas_avenida)
    juego(mapa, economato)


if __name__ == "__main__":
    main()