"""Barrio MUD-Pi — Integración Grupo Q

Servidor telnet basado en mud-pi que expone un barrio con dos calles:

- Calle del Ébano:  Marc (leñador) + Pedro (carpintero)
- Calle del Hierro: Jorge (minero) + Juan  (herrero)

Reutiliza las clases de P2_Grupo_Q_semana2.py (Trabajador, Jugador,
Calle, BarrioComercial) y el servidor MudServer de mudserver.py.
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


AYUDA = """Comandos disponibles:

producir <item>            → empezar a producir
parar                      → parar producción
inventario                 → ver inventario de la calle
bolsa                      → ver tu bolsa y monedas
recetas                    → ver tus recetas
precios                    → ver tus precios de producción
precio <item> <num>        → fijar precio de producción
precio_bolsa <item> <num>  → fijar precio de reventa personal
comprar <item> <num>       → comprar del taller al precio vigente
almacen                    → ver almacén total del barrio
ranking                    → ranking de calles por riqueza
riqueza                    → riqueza total del barrio
ayuda                      → mostrar este menú
salir                      → cerrar la sesión
"""

def _prompt(pid: int, jugador: Jugador) -> None:
    mud.send_message(pid, f"[{jugador.nombre}@{jugador.localizacion}] > ")

def main() -> None:
    print("Servidor Barrio MUD-Pi escuchando en puerto 1234 (telnet)...")
    try:
        while True:
            time.sleep(0.2)
            mud.update()

            # Nuevos clientes
            for pid in mud.get_new_players():
                conexiones[pid] = {"jugador": None, "calle": None}
                mud.send_message(pid, "Bienvenido al Barrio del Mercado.")
                mud.send_message(pid, "Elige personaje escribiendo su nombre:")
                mud.send_message(pid, "  marc, pedro, jorge, juan")

            # Desconexiones
            for pid in mud.get_disconnected_players():
                if pid in conexiones:
                    j = conexiones[pid].get("jugador")
                    if j is not None:
                        print(f"Cliente {pid} ({j.nombre}) desconectado.")
                    del conexiones[pid]

            # Comandos
            for pid, command, params in mud.get_commands():
                if pid not in conexiones:
                    continue

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
                        mud.send_message(
                            pid,
                            f"Ahora controlas a {jugador.nombre} en {calle.nombre}.",
                        )
                        mud.send_message(pid, "Escribe 'ayuda' para ver los comandos.")
                        _prompt(pid, jugador)
                    else:
                        mud.send_message(
                            pid,
                            "Nombre inválido. Usa: marc, pedro, jorge, juan",
                        )
                    continue

                # A partir de aquí ya tenemos jugador y calle
                cmd = command.lower()
                args = params.split() if params else []

                # ── Producción ─────────────────────────────────────
                if cmd == "producir":
                    if not args:
                        jugador.trabajador.consultar_recetas()
                        mud.send_message(pid, "Uso: producir <item>")
                    else:
                        item = args[0]
                        jugador.trabajador.asignar_tarea(item)
                    _prompt(pid, jugador)

                elif cmd == "parar":
                    jugador.trabajador.parar()
                    _prompt(pid, jugador)

                # ── Consultas ──────────────────────────────────────
                elif cmd == "inventario":
                    txt = [f"Inventario de {calle.nombre}:"]
                    with calle.cerrojo:
                        if not calle.inventario:
                            txt.append("  (vacío)")
                        else:
                            for it, cant in calle.inventario.items():
                                txt.append(f"  {it}: {cant}")
                    for line in txt:
                        mud.send_message(pid, line)
                    _prompt(pid, jugador)

                elif cmd == "bolsa":
                    mud.send_message(
                        pid,
                        f"Bolsa de {jugador.nombre} ({jugador.monedas} monedas):",
                    )
                    if not jugador.inventario:
                        mud.send_message(pid, "  (vacía)")
                    else:
                        for it, cant in jugador.inventario.items():
                            p_rev = jugador.precios_bolsa.get(it, "sin precio")
                            if isinstance(p_rev, int):
                                valor = p_rev * cant
                            else:
                                valor = "?"
                            mud.send_message(
                                pid,
                                f"  {it}: {cant} ud. | reventa: {p_rev} | valor: {valor}",
                            )
                    _prompt(pid, jugador)

                elif cmd == "recetas":
                    mud.send_message(pid, f"Recetas de {jugador.nombre}:")
                    for r in jugador.trabajador._recetas:
                        necesita = r["necesita"] if r["necesita"] else "nada"
                        mud.send_message(
                            pid,
                            f"  {r['produce']}: necesita {necesita}, tarda {r['tiempo']}s",
                        )
                    _prompt(pid, jugador)

                elif cmd == "precios":
                    mud.send_message(pid, f"Precios de {jugador.nombre}:")
                    for it, precio in jugador.trabajador.precios.items():
                        mud.send_message(pid, f"  {it}: {precio} monedas")
                    _prompt(pid, jugador)

                # ── Fijar precios ─────────────────────────────────
                elif cmd == "precio":
                    if len(args) != 2:
                        mud.send_message(pid, "Uso: precio <item> <num>")
                    else:
                        item, num = args[0], args[1]
                        try:
                            jugador.trabajador.fijar_precio(item, int(num))
                        except ValueError:
                            mud.send_message(pid, "El precio tiene que ser un entero.")
                    _prompt(pid, jugador)

                elif cmd == "precio_bolsa":
                    if len(args) != 2:
                        mud.send_message(pid, "Uso: precio_bolsa <item> <num>")
                    else:
                        item, num = args[0], args[1]
                        try:
                            jugador.fijar_precio_bolsa(item, int(num))
                        except ValueError:
                            mud.send_message(pid, "El precio tiene que ser un entero.")
                    _prompt(pid, jugador)

                # ── Comercio: comprar desde la calle ─────────────
                elif cmd == "comprar":
                    if len(args) != 2:
                        mud.send_message(pid, "Uso: comprar <item> <cantidad>")
                        _prompt(pid, jugador)
                        continue
                    item, cant_s = args
                    try:
                        cant = int(cant_s)
                    except ValueError:
                        mud.send_message(pid, "La cantidad tiene que ser un entero.")
                        _prompt(pid, jugador)
                        continue

                    # Precio: prioriza mercado de barrio, si no el trabajador
                    precio_u = barrio.obtener_precio(item, calle)
                    if precio_u is None:
                        mud.send_message(
                            pid,
                            f"No hay precio fijado para '{item}'. Usa 'precio' primero.",
                        )
                        _prompt(pid, jugador)
                        continue

                    jugador.comprar(item, cant, calle.inventario, calle.cerrojo, precio_u)
                    _prompt(pid, jugador)

                # ── Interacciones de barrio: almacén / ranking / riqueza ─
                elif cmd == "almacen":
                    almacen: dict[str, int] = {}
                    for c in barrio.calles:
                        with c.cerrojo:
                            for it, cant in c.inventario.items():
                                almacen[it] = almacen.get(it, 0) + cant
                    mud.send_message(pid, f"Almacén total de {barrio.nombre}:")
                    if not almacen:
                        mud.send_message(pid, "  (vacío)")
                    else:
                        for it, cant in almacen.items():
                            mud.send_message(pid, f"  {it}: {cant} uds (total)")
                    _prompt(pid, jugador)

                elif cmd == "ranking":
                    ranking = []
                    for c in barrio.calles:
                        total = sum(j.monedas for j in c.jugadores)
                        ranking.append((c.nombre, total))
                    ranking.sort(key=lambda x: x[1], reverse=True)
                    mud.send_message(pid, f"Ranking de calles — {barrio.nombre}:")
                    for pos, (nom_c, total) in enumerate(ranking, start=1):
                        mud.send_message(pid, f"  {pos}. {nom_c}: {total} monedas")
                    _prompt(pid, jugador)

                elif cmd == "riqueza":
                    total_barrio = 0
                    mud.send_message(pid, f"Riqueza total de {barrio.nombre}:")
                    for c in barrio.calles:
                        total_c = sum(j.monedas for j in c.jugadores)
                        total_barrio += total_c
                        mud.send_message(pid, f"  {c.nombre}: {total_c} monedas")
                        for j in c.jugadores:
                            mud.send_message(pid, f"    {j.nombre}: {j.monedas} monedas")
                    mud.send_message(pid, f"TOTAL BARRIO: {total_barrio} monedas")
                    _prompt(pid, jugador)

                # ── Miscelánea ──────────────────────────────────
                elif cmd == "ayuda":
                    for line in AYUDA.splitlines():
                        mud.send_message(pid, line)
                    _prompt(pid, jugador)

                elif cmd == "salir":
                    mud.send_message(pid, f"Hasta luego, {jugador.nombre}.")
                    conexiones[pid]["jugador"] = None
                    conexiones[pid]["calle"] = None

                else:
                    mud.send_message(
                        pid,
                        f"Comando desconocido '{cmd}'. Escribe 'ayuda' para ver los comandos.",
                    )
                    _prompt(pid, jugador)

    except KeyboardInterrupt:
        print("Cerrando servidor...")
        mud.shutdown()
        barrio.detener()

if __name__ == '__main__':
    main()