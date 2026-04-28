"""Barrio MUD-Pi — Integración Grupo Q

Servidor telnet basado en mud-pi que expone un barrio con dos calles:

- Calle del Ébano:  Marc (leñador) + Pedro (carpintero)
- Calle del Hierro: Jorge (minero) + Juan  (herrero)

Reutiliza las clases de P2_Grupo_Q_semana2.py (Trabajador, Jugador,
Calle, BarrioComercial) y el servidor MudServer de mudserver.py.

Correcciones respecto a la versión anterior:
  - mudserver._handle_disconnect ya no crashea con doble desconexión
  - La ayuda se envía como un solo mensaje (no línea a línea)
  - Todos los comandos están envueltos en try/except para que un error
    de un cliente no mate el servidor
  - safe_send() comprueba que el cliente siga conectado antes de enviar
"""

import time
import importlib.util
from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent

def _load_module(filename: str, module_name: str):
    """Carga un módulo Python desde un fichero concreto.
    Permite importar ficheros como 'P2_Grupo_Q_semana2.py', cuyo
    nombre no es un identificador válido para import directo.
    """
    path = BASE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {filename} como {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Cargamos las clases de tu práctica y el servidor MUD original
p2 = _load_module('P2_Grupo_Q_semana2.py', 'p2_barrio')
mud_mod = _load_module('mudserver.py', 'mudserver_mod')

Trabajador = p2.Trabajador
Jugador = p2.Jugador
Calle = p2.Calle
BarrioComercial = p2.BarrioComercial
MudServer = mud_mod.MudServer

# Calle del Ébano (Grupo Q: Marc + Pedro)
recetas_lenador = [
    {"produce": "madera", "cantidad": 1, "necesita": {}, "tiempo": 3},
]
recetas_carpintero = [
    {"produce": "tablas",  "cantidad": 1, "necesita": {"madera": 2}, "tiempo": 4},
    {"produce": "muebles", "cantidad": 1, "necesita": {"madera": 5}, "tiempo": 8},
]

t_lenador    = Trabajador(recetas_lenador,    {}, Lock(), {"madera": 3})
t_carpintero = Trabajador(recetas_carpintero, {}, Lock(),
                          {"tablas": 5, "muebles": 20})

marc  = Jugador("Marc",  t_lenador,    monedas=50)
pedro = Jugador("Pedro", t_carpintero, monedas=50)

calle_ebano = Calle("Calle del Ébano")
calle_ebano.añadir_jugador(marc)
calle_ebano.añadir_jugador(pedro)


# Calle del Hierro (Grupo: Jorge + Juan)
recetas_minero = [
    {"produce": "mineral", "cantidad": 1, "necesita": {}, "tiempo": 4},
]
recetas_herrero = [
    {"produce": "hierro",       "cantidad": 1, "necesita": {"mineral": 2}, "tiempo": 5},
    {"produce": "herramientas", "cantidad": 1, "necesita": {"hierro": 1},  "tiempo": 6},
]

t_minero  = Trabajador(recetas_minero,  {}, Lock(), {"mineral": 2})
t_herrero = Trabajador(recetas_herrero, {}, Lock(),
                       {"hierro": 8, "herramientas": 15})

jorge = Jugador("Jorge", t_minero,  monedas=50)
juan  = Jugador("Juan",  t_herrero, monedas=50)

calle_hierro = Calle("Calle del Hierro")
calle_hierro.añadir_jugador(jorge)
calle_hierro.añadir_jugador(juan)


# Barrio comercial que redistribuye recursos entre calles
barrio = BarrioComercial("Barrio del Mercado", intervalo=15)
barrio.añadir_calle(calle_ebano)
barrio.añadir_calle(calle_hierro)

# Arranca hilos de trabajadores + hilo de redistribución del barrio
barrio.iniciar()

# Mapa para localizar rápidamente la calle de cada Jugador
def calle_de(jugador: Jugador) -> Calle:
    if jugador in calle_ebano.jugadores:
        return calle_ebano
    if jugador in calle_hierro.jugadores:
        return calle_hierro
    raise ValueError(f"Jugador {jugador.nombre} no pertenece a ninguna calle conocida")

mud = MudServer()

# Estado por conexión telnet:
#   id → {"jugador": Jugador | None, "calle": Calle | None}
conexiones: dict[int, dict] = {}

# Roles disponibles para elegir al entrar
roles: dict[str, Jugador] = {
    "marc":  marc,
    "pedro": pedro,
    "jorge": jorge,
    "juan":  juan,
}


# ── AYUDA: se envía como UN solo bloque, no línea a línea ──────────
# Esto evita que el socket falle a mitad del envío y crashee el servidor.
AYUDA = (
    "Comandos disponibles:\n\r"
    "\n\r"
    "producir <item>            - empezar a producir\n\r"
    "parar                      - parar producción\n\r"
    "inventario                 - ver inventario de la calle\n\r"
    "bolsa                      - ver tu bolsa y monedas\n\r"
    "recetas                    - ver tus recetas\n\r"
    "precios                    - ver tus precios de producción\n\r"
    "precio <item> <num>        - fijar precio de producción\n\r"
    "precio_bolsa <item> <num>  - fijar precio de reventa personal\n\r"
    "comprar <item> <num>       - comprar del taller al precio vigente\n\r"
    "depositar <item> <num>     - depositar item de bolsa al taller\n\r"
    "retirar <item> <num>       - retirar item del taller a bolsa\n\r"
    "vender <item> <num> <jug>  - vender desde tu bolsa a otro jugador\n\r"
    "almacen                    - ver almacén total del barrio\n\r"
    "ranking                    - ranking de calles por riqueza\n\r"
    "riqueza                    - riqueza total del barrio\n\r"
    "decir <mensaje>            - hablar en tu calle\n\r"
    "gritar <mensaje>           - hablar en todo el barrio\n\r"
    "jugadores                  - ver quién está conectado\n\r"
    "ayuda                      - mostrar este menú\n\r"
    "salir                      - cerrar la sesión\n\r"
)


def safe_send(pid: int, message: str) -> None:
    """Envía un mensaje solo si el cliente sigue conectado."""
    if pid in mud._clients:
        mud.send_message(pid, message)


def _prompt(pid: int, jugador: Jugador) -> None:
    safe_send(pid, f"[{jugador.nombre}@{jugador.localizacion}] > ")


def broadcast_calle(calle: Calle, mensaje: str, excluir_pid: int = -1) -> None:
    """Envía mensaje a todos los conectados en una calle."""
    for pid, state in list(conexiones.items()):
        if state.get("jugador") is not None and state.get("calle") is calle and pid != excluir_pid:
            safe_send(pid, mensaje)


def broadcast_barrio(mensaje: str, excluir_pid: int = -1) -> None:
    """Envía mensaje a todos los conectados."""
    for pid, state in list(conexiones.items()):
        if state.get("jugador") is not None and pid != excluir_pid:
            safe_send(pid, mensaje)


def main() -> None:
    print("Servidor Barrio MUD-Pi escuchando en puerto 1234 (telnet)...")
    try:
        while True:
            time.sleep(0.2)
            mud.update()

            # Nuevos clientes
            for pid in mud.get_new_players():
                conexiones[pid] = {"jugador": None, "calle": None}
                safe_send(pid, "Bienvenido al Barrio del Mercado.")
                safe_send(pid, "Elige personaje escribiendo su nombre:")
                safe_send(pid, "  marc, pedro, jorge, juan")

            # Desconexiones
            for pid in mud.get_disconnected_players():
                if pid in conexiones:
                    j = conexiones[pid].get("jugador")
                    if j is not None:
                        c = conexiones[pid].get("calle")
                        broadcast_calle(c, f"** {j.nombre} se ha desconectado **", excluir_pid=pid)
                        print(f"[Servidor] {j.nombre} desconectado (pid={pid})")
                    del conexiones[pid]

            # Comandos
            for pid, command, params in mud.get_commands():
                if pid not in conexiones:
                    continue

                # ── Todo el manejo de comandos envuelto en try/except ──
                # Si un cliente se desconecta a mitad, no mata el servidor.
                try:
                    _procesar_comando(pid, command, params)
                except Exception as e:
                    print(f"[Servidor] Error procesando comando de pid={pid}: {e}")

    except KeyboardInterrupt:
        print("Cerrando servidor...")
        mud.shutdown()
        barrio.detener()


def _procesar_comando(pid: int, command: str, params: str) -> None:
    """Procesa un comando de un cliente. Separado para que el try/except
    del bucle principal capture cualquier excepción sin matar el servidor."""

    state = conexiones[pid]
    jugador = state["jugador"]
    calle = state["calle"]

    # 1) Fase de login: primer comando es el nombre del personaje
    if jugador is None:
        nombre = command.lower()
        if nombre in roles:
            jugador = roles[nombre]
            calle = calle_de(jugador)
            state["jugador"] = jugador
            state["calle"] = calle
            safe_send(pid, f"Ahora controlas a {jugador.nombre} en {calle.nombre}.")
            safe_send(pid, "Escribe 'ayuda' para ver los comandos.")
            broadcast_calle(calle, f"** {jugador.nombre} se ha conectado **", excluir_pid=pid)
            _prompt(pid, jugador)
        else:
            safe_send(pid, "Nombre inválido. Usa: marc, pedro, jorge, juan")
        return

    # A partir de aquí ya tenemos jugador y calle
    cmd = command.lower()
    args = params.split() if params else []

    # ── Producción ─────────────────────────────────────
    if cmd == "producir":
        if not args:
            lines = [f"Recetas de {jugador.nombre}:"]
            for r in jugador.trabajador._recetas:
                necesita = r["necesita"] if r["necesita"] else "nada"
                lines.append(f"  {r['produce']}: necesita {necesita}, tarda {r['tiempo']}s")
            lines.append("Uso: producir <item>")
            safe_send(pid, "\n\r".join(lines))
        else:
            item = args[0]
            jugador.trabajador.asignar_tarea(item)
            safe_send(pid, f"Intentando producir '{item}'...")
        _prompt(pid, jugador)

    elif cmd == "parar":
        jugador.trabajador.parar()
        safe_send(pid, "Producción detenida.")
        _prompt(pid, jugador)

    # ── Consultas ──────────────────────────────────────
    elif cmd == "inventario":
        lines = [f"Inventario de {calle.nombre}:"]
        with calle.cerrojo:
            if not calle.inventario:
                lines.append("  (vacío)")
            else:
                for it, cant in calle.inventario.items():
                    if cant > 0:
                        lines.append(f"  {it}: {cant}")
        if len(lines) == 1:
            lines.append("  (vacío)")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    elif cmd == "bolsa":
        lines = [f"Bolsa de {jugador.nombre} ({jugador.monedas} monedas):"]
        if not jugador.inventario:
            lines.append("  (vacía)")
        else:
            for it, cant in jugador.inventario.items():
                p_rev = jugador.precios_bolsa.get(it, "sin precio")
                if isinstance(p_rev, int):
                    valor = p_rev * cant
                else:
                    valor = "?"
                lines.append(f"  {it}: {cant} ud. | reventa: {p_rev} | valor: {valor}")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    elif cmd == "recetas":
        lines = [f"Recetas de {jugador.nombre}:"]
        for r in jugador.trabajador._recetas:
            necesita = r["necesita"] if r["necesita"] else "nada"
            lines.append(f"  {r['produce']}: necesita {necesita}, tarda {r['tiempo']}s")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    elif cmd == "precios":
        lines = [f"Precios de {jugador.nombre}:"]
        for it, precio in jugador.trabajador.precios.items():
            lines.append(f"  {it}: {precio} monedas")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    # ── Fijar precios ─────────────────────────────────
    elif cmd == "precio":
        if len(args) != 2:
            safe_send(pid, "Uso: precio <item> <num>")
        else:
            item, num = args[0], args[1]
            try:
                jugador.trabajador.fijar_precio(item, int(num))
                safe_send(pid, f"Precio de {item} fijado a {num} monedas.")
            except ValueError:
                safe_send(pid, "El precio tiene que ser un entero.")
        _prompt(pid, jugador)

    elif cmd == "precio_bolsa":
        if len(args) != 2:
            safe_send(pid, "Uso: precio_bolsa <item> <num>")
        else:
            item, num = args[0], args[1]
            try:
                jugador.fijar_precio_bolsa(item, int(num))
                safe_send(pid, f"Precio de reventa de {item} fijado a {num} monedas.")
            except ValueError:
                safe_send(pid, "El precio tiene que ser un entero.")
        _prompt(pid, jugador)

    # ── Comercio: comprar desde la calle ─────────────
    elif cmd == "comprar":
        if len(args) != 2:
            safe_send(pid, "Uso: comprar <item> <cantidad>")
            _prompt(pid, jugador)
            return
        item_c, cant_s = args
        try:
            cant = int(cant_s)
        except ValueError:
            safe_send(pid, "La cantidad tiene que ser un entero.")
            _prompt(pid, jugador)
            return

        # Buscar stock: primero en la calle actual, luego en la otra
        calle_origen = None
        if calle.inventario.get(item_c, 0) >= cant:
            calle_origen = calle
        else:
            for c in barrio.calles:
                if c is not calle and c.inventario.get(item_c, 0) >= cant:
                    calle_origen = c
                    break

        if calle_origen is None:
            safe_send(pid, f"No hay suficiente '{item_c}' en el barrio.")
            _prompt(pid, jugador)
            return

        # Precio: prioriza mercado de barrio, si no el trabajador
        precio_u = barrio.obtener_precio(item_c, calle_origen)
        if precio_u is None:
            safe_send(pid, f"No hay precio fijado para '{item_c}'. Usa 'precio' primero.")
            _prompt(pid, jugador)
            return

        if calle_origen is not calle:
            safe_send(pid, f"(Comprando de {calle_origen.nombre})")

        jugador.comprar(item_c, cant, calle_origen.inventario, calle_origen.cerrojo, precio_u)
        safe_send(pid, f"Compra procesada: {cant}x {item_c} a {precio_u} mon/ud.")
        _prompt(pid, jugador)

    # ── Vender a otro jugador ────────────────────────
    elif cmd == "vender":
        if len(args) < 3:
            safe_send(pid, "Uso: vender <item> <cantidad> <jugador>")
            _prompt(pid, jugador)
            return
        item_v, cant_s, nombre_c = args[0], args[1], args[2]
        try:
            cant_v = int(cant_s)
        except ValueError:
            safe_send(pid, "La cantidad tiene que ser un entero.")
            _prompt(pid, jugador)
            return

        res = barrio.cambiar_jugador(nombre_c)
        if res is None:
            safe_send(pid, f"Jugador '{nombre_c}' no encontrado.")
        elif res[0] is jugador:
            safe_send(pid, "No puedes venderte a ti mismo.")
        else:
            comprador_obj = res[0]
            precio_u = (jugador.precios_bolsa.get(item_v)
                        or jugador.trabajador.precios.get(item_v))
            if precio_u is None:
                safe_send(pid, f"Sin precio para '{item_v}'. Usa: precio_bolsa {item_v} <num>")
            else:
                jugador.vender(item_v, cant_v, precio_u, comprador_obj)
                coste = precio_u * cant_v
                safe_send(pid, f"Vendidos {cant_v}x {item_v} a {comprador_obj.nombre} por {coste} monedas.")
                # Notificar al comprador si está conectado
                for p2_pid, p2_state in list(conexiones.items()):
                    if p2_state.get("jugador") is comprador_obj:
                        safe_send(p2_pid, f"\n** {jugador.nombre} te ha vendido {cant_v}x {item_v} **")
        _prompt(pid, jugador)

    # ── Depositar item de bolsa al taller ────────────
    elif cmd == "depositar":
        if len(args) != 2:
            safe_send(pid, "Uso: depositar <item> <cantidad>")
            _prompt(pid, jugador)
            return
        item_d, cant_s = args
        try:
            cant_d = int(cant_s)
        except ValueError:
            safe_send(pid, "La cantidad tiene que ser un entero.")
            _prompt(pid, jugador)
            return
        with calle.cerrojo:
            if jugador.inventario.get(item_d, 0) < cant_d:
                safe_send(pid, f"No tienes suficiente {item_d} en la bolsa.")
            else:
                with jugador.cerrojo:
                    jugador.inventario[item_d] -= cant_d
                    calle.inventario[item_d] = calle.inventario.get(item_d, 0) + cant_d
                safe_send(pid, f"Has depositado {cant_d} {item_d} en el taller.")
        _prompt(pid, jugador)

    # ── Retirar item del taller a la bolsa ───────────
    elif cmd == "retirar":
        if len(args) != 2:
            safe_send(pid, "Uso: retirar <item> <cantidad>")
            _prompt(pid, jugador)
            return
        item_r, cant_s = args
        try:
            cant_r = int(cant_s)
        except ValueError:
            safe_send(pid, "La cantidad tiene que ser un entero.")
            _prompt(pid, jugador)
            return
        with calle.cerrojo:
            if calle.inventario.get(item_r, 0) < cant_r:
                safe_send(pid, f"No hay suficiente {item_r} en el taller.")
            else:
                with jugador.cerrojo:
                    calle.inventario[item_r] -= cant_r
                    jugador._añadir_a_inventario(item_r, cant_r)
                safe_send(pid, f"Has retirado {cant_r} {item_r} a tu bolsa.")
        _prompt(pid, jugador)

    # ── Comunicación ───────────────────────────────────
    elif cmd == "decir":
        if not params:
            safe_send(pid, "Uso: decir <mensaje>")
        else:
            broadcast_calle(calle, f"{jugador.nombre} dice: {params}", excluir_pid=pid)
            safe_send(pid, f"Dices: {params}")
        _prompt(pid, jugador)

    elif cmd == "gritar":
        if not params:
            safe_send(pid, "Uso: gritar <mensaje>")
        else:
            broadcast_barrio(f"[GRITO] {jugador.nombre}: {params}", excluir_pid=pid)
            safe_send(pid, f"Gritas: {params}")
        _prompt(pid, jugador)

    elif cmd == "jugadores":
        lines = ["Jugadores conectados:"]
        for p2_pid, p2_state in list(conexiones.items()):
            j2 = p2_state.get("jugador")
            c2 = p2_state.get("calle")
            if j2 is not None:
                marca = " (tú)" if p2_pid == pid else ""
                lines.append(f"  {j2.nombre} en {c2.nombre}{marca}")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    # ── Interacciones de barrio ──────────────────────
    elif cmd == "almacen":
        almacen: dict[str, int] = {}
        for c in barrio.calles:
            with c.cerrojo:
                for it, cant in c.inventario.items():
                    if cant > 0:
                        almacen[it] = almacen.get(it, 0) + cant
        lines = [f"Almacén total de {barrio.nombre}:"]
        if not almacen:
            lines.append("  (vacío)")
        else:
            for it, cant in sorted(almacen.items()):
                lines.append(f"  {it}: {cant} uds (total)")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    elif cmd == "ranking":
        ranking = []
        for c in barrio.calles:
            total = sum(j.monedas for j in c.jugadores)
            ranking.append((c.nombre, total))
        ranking.sort(key=lambda x: x[1], reverse=True)
        lines = [f"Ranking de calles — {barrio.nombre}:"]
        for pos, (nom_c, total) in enumerate(ranking, start=1):
            lines.append(f"  {pos}. {nom_c}: {total} monedas")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    elif cmd == "riqueza":
        total_barrio = 0
        lines = [f"Riqueza total de {barrio.nombre}:"]
        for c in barrio.calles:
            total_c = sum(j.monedas for j in c.jugadores)
            total_barrio += total_c
            lines.append(f"  {c.nombre}: {total_c} monedas")
            for j in c.jugadores:
                lines.append(f"    {j.nombre}: {j.monedas} monedas")
        lines.append(f"TOTAL BARRIO: {total_barrio} monedas")
        safe_send(pid, "\n\r".join(lines))
        _prompt(pid, jugador)

    # ── Miscelánea ──────────────────────────────────
    elif cmd == "ayuda":
        # Se envía como UN solo mensaje para evitar crash por socket
        safe_send(pid, AYUDA)
        _prompt(pid, jugador)

    elif cmd == "salir":
        safe_send(pid, f"Hasta luego, {jugador.nombre}.")
        broadcast_calle(calle, f"** {jugador.nombre} se ha desconectado **", excluir_pid=pid)
        conexiones[pid]["jugador"] = None
        conexiones[pid]["calle"] = None

    else:
        safe_send(pid, f"Comando desconocido '{cmd}'. Escribe 'ayuda' para ver los comandos.")
        _prompt(pid, jugador)


if __name__ == '__main__':
    main()
