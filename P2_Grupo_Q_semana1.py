# Importamos las librerías necesarias
from typing import Dict, List
from threading import Thread, Lock, Event
import time
from enum import Enum, auto



# Pasamos a crear la clase Trabajador y la clase que verifica su estado:
class EstadoTrabajador(Enum):
    INACTIVO    = auto()
    PRODUCIENDO = auto()



# Hay que tener en cuenta que Trabajador hereda de Thread
class Trabajador(Thread):
    # Iniciamos el constructor de clases
    def __init__(self, recetas: List[Dict], inventario: Dict[str, int],
                 cerrojo: Lock, precios: dict[str, int]) -> None:
        super().__init__(daemon=True)  # El trabajador desaparece cuando acaba el juego
        # Condición de recetas, para no saturar la memoria
        if len(recetas) > 3:
            raise ValueError("máximo 3 recetas permitidas.")
        # Definición de los atributos
        self.nombre        = ""
        self._recetas      = recetas
        self.inventario    = inventario
        self.cerrojo       = cerrojo
        self.precios       = precios
        self.receta_activa = None
        self.estado        = EstadoTrabajador.INACTIVO
        # Añadimos un último atributo para asegurar el flujo de los hilos
        self._activo = Event()
        self._activo.set()



# Definimos métodos privados para la correcta implementación del objeto trabajador
    # Método para comprobar si hay suficientes recursos para crear un objeto
    def _tiene_recursos(self, necesidades: dict[str, int]) -> bool:
        for recurso, cantidad in necesidades.items():
            if self.inventario.get(recurso, 0) < cantidad:
                return False
        return True

    # Método para reducir los recursos del almacén del trabajador
    def _consumir_recursos(self, necesidades: dict[str, int]) -> None:
        for recurso, cantidad in necesidades.items():
            self.inventario[recurso] -= cantidad



# Definimos los métodos públicos generales de la clase Trabajador:
    # Asignamos la tarea del hilo
    def asignar_tarea(self, nombre_producto: str) -> None:
        for receta in self._recetas:
            if receta["produce"] == nombre_producto:
                self.receta_activa = receta
                self.estado        = EstadoTrabajador.PRODUCIENDO
                print(f"{self.nombre} empieza a producir {nombre_producto}.")
                return
        print(f"{self.nombre} no puede producir '{nombre_producto}'.")

    # Paramos la tarea asignada
    def parar(self) -> None:
        self.estado        = EstadoTrabajador.INACTIVO
        self.receta_activa = None
        print(f"{self.nombre} ha parado la producción.")

    # Método para fijar el precio de los items del trabajador
    def fijar_precio(self, producto: str, precio: int) -> None:
        if producto in self.precios:
            self.precios[producto] = precio
            print(f"El precio de {producto} ahora es {precio} monedas.")
        else:
            print(f"{self.nombre} no vende '{producto}'.")

    # Método para eliminar el stock del inventario del jugador
    def eliminar_stock(self, producto: str, cantidad: int) -> None:
        with self.cerrojo:
            if self.inventario.get(producto, 0) >= cantidad:
                self.inventario[producto] -= cantidad
                print(f"{self.nombre} elimina {cantidad} {producto} de su inventario.")
            else:
                print(f"No hay suficiente stock de {producto} para eliminar.")

    # Método para consultar las recetas del jugador
    def consultar_recetas(self) -> None:
        print(f"\n── Recetas de {self.nombre} ──")
        for receta in self._recetas:
            necesita = receta["necesita"] if receta["necesita"] else "nada"
            print(f"  {receta['produce']}: necesita {necesita}, tarda {receta['tiempo']}s")

    # Método para consultar los precios de los productos
    def consultar_precios(self) -> dict[str, int]:
        return dict(self.precios)

    # Detenemos el hilo para limpiar el resultado final
    def detener(self) -> None:
        self._activo.clear()
        self.receta_activa = None

    # Método que crea todo el algoritmo de la clase trabajador
    def run(self) -> None:
        # Si el trabajador está en activo
        while self._activo.is_set():
            # El trabajador intenta producir
            # CORRECCIÓN: receta_activa se lee dentro del cerrojo para evitar
            # la carrera de datos con asignar_tarea()/parar() del hilo principal.
            with self.cerrojo:
                receta = self.receta_activa
                hay_recursos = False
                if receta is not None:
                    hay_recursos = self._tiene_recursos(receta["necesita"])
                    if hay_recursos:
                        self._consumir_recursos(receta["necesita"])
            if receta is None:
                time.sleep(0.5)
                continue
            if not hay_recursos:
                time.sleep(0.5)
                continue
            print(f"{self.nombre} produciendo {receta['produce']}")
            time.sleep(receta["tiempo"])
            # Se notifica del item creado
            with self.cerrojo:
                self.inventario[receta["produce"]] += receta["cantidad"]
                print(f"[{self.nombre}] +{receta['cantidad']} {receta['produce']}.")
            # Esperamos
            time.sleep(1)



# Pasamos a crear la clase Jugador y la clase que verifica su estado:
class EstadoJugador(Enum):
    INACTIVO    = auto()
    PRODUCIENDO = auto()
    VIAJANDO    = auto()
    DESCANSANDO = auto()
    EN_TIENDA   = auto()



# Definimos la clase Jugador
class Jugador:
    # Iniciamos el constructor de clases
    def __init__(self, nombre: str, trabajador: Trabajador, monedas: int = 50) -> None:
        self.nombre      = nombre
        self.trabajador  = trabajador
        self.monedas     = monedas
        self.inventario: dict[str, int] = {}
        self.cerrojo     = Lock()
        self.estado      = EstadoJugador.DESCANSANDO
        self.localizacion: str = "desconocida"
        self.trabajador.nombre = self.nombre
        # precios_bolsa: precios de reventa personales del jugador,
        # independientes del precio de producción del trabajador
        self.precios_bolsa: dict[str, int] = {}



# Definimos los métodos privados de la clase
    # Definimos el método de añadir elementos al inventario del jugador
    def _añadir_a_inventario(self, item: str, cantidad: int, precio_compra: int = 0) -> None:
        self.inventario[item] = self.inventario.get(item, 0) + cantidad
        # Fija el precio de reventa inicial al precio de compra si no existe aún
        if item not in self.precios_bolsa and precio_compra > 0:
            self.precios_bolsa[item] = precio_compra



# Definimos los métodos públicos de la clase
    # Definimos el método de compra de productos
    # El jugador retira items del inventario de la calle y paga al contado.
    # Se adquieren con el cerrojo de la calle primero y el del jugador después
    # para evitar deadlocks.
    def comprar(self, item: str, cantidad: int,
                inventario_calle: dict, cerrojo_calle: Lock,
                precio_unitario: int) -> None:
        coste_total = precio_unitario * cantidad
        with cerrojo_calle:
            if inventario_calle.get(item, 0) < cantidad:
                print(f"{self.nombre}: no hay suficiente {item} en la tienda.")
                return
            with self.cerrojo:
                if self.monedas < coste_total:
                    print(f"{self.nombre}: monedas insuficientes ({self.monedas}/{coste_total}).")
                    return
                inventario_calle[item] -= cantidad
                self.monedas           -= coste_total
                self._añadir_a_inventario(item, cantidad, precio_unitario)
        print(f"{self.nombre} compra {cantidad} x {item} por {coste_total} monedas.")
        print(f"  (precio de reventa inicial: {precio_unitario} mon/ud.)")

    # Definimos el método que fija el precio de la bolsa
    def fijar_precio_bolsa(self, item: str, precio: int) -> None:
        if item in self.inventario and self.inventario[item] > 0:
            self.precios_bolsa[item] = precio
            print(f"{self.nombre}: precio de reventa de {item} → {precio} monedas/ud.")
        else:
            print(f"{self.nombre} no tiene '{item}' en su bolsa.")

    # Definimos el método que hace una consulta a la bolsa
    def consultar_bolsa(self) -> None:
        with self.cerrojo:
            print(f"\n── Bolsa de {self.nombre} ({self.monedas} monedas) ──")
            if not self.inventario:
                print("  (vacía)")
            for item, cantidad in self.inventario.items():
                precio_rev = self.precios_bolsa.get(item, "sin precio")
                valor      = precio_rev * cantidad if isinstance(precio_rev, int) else "?"
                print(f"  {item}: {cantidad} ud. | reventa: {precio_rev} mon/ud. | valor: {valor} mon.")

    # Definimos el método para vender productos
    # Venta directa entre jugadores: el vendedor cede items de su bolsa
    # y recibe monedas. Orden de cerrojos: vendedor → comprador.
    def vender(self, item: str, cantidad: int, precio_unitario: int, comprador: "Jugador") -> None:
        coste_total = precio_unitario * cantidad
        # Primero el cerrojo del vendedor, luego el del comprador
        with self.cerrojo:
            if self.inventario.get(item, 0) < cantidad:
                print(f"{self.nombre}: no tienes suficiente {item} para vender.")
                return
            with comprador.cerrojo:
                if comprador.monedas < coste_total:
                    print(f"{comprador.nombre} no tiene monedas suficientes.")
                    return
                # Transacción completa
                self.inventario[item] -= cantidad
                self.monedas          += coste_total
                comprador.monedas     -= coste_total
                comprador._añadir_a_inventario(item, cantidad, precio_unitario)
        print(f"{self.nombre} vende {cantidad}x {item} a {comprador.nombre} por {coste_total} monedas.")



# Definimos la clase Calle compuesta por dos jugadores
class Calle:
    # Definimos el constructor de clases
    def __init__(self, nombre: str) -> None:
        self.nombre     = nombre
        self.jugadores: list[Jugador] = []
        self.inventario: dict[str, int] = {}
        self.cerrojo    = Lock()



# Definimos los métodos privados de la clase Calle
    # Método para actualizar el inventario de la calle,
    # compuesto por el inventario de los dos jugadores que se encuentran en la calle
    def _actualizar_inventario(self, trabajador: Trabajador) -> None:
        for receta in trabajador._recetas:
            producto = receta["produce"]
            if producto not in self.inventario:
                self.inventario[producto] = 0
            for ingrediente in receta["necesita"]:
                if ingrediente not in self.inventario:
                    self.inventario[ingrediente] = 0



# Definimos los métodos públicos
    # Método para añadir un jugador a la calle
    def añadir_jugador(self, jugador: Jugador) -> None:
        if len(self.jugadores) >= 2:
            raise ValueError(f"{self.nombre}: máximo 2 jugadores por calle.")
        # Asignamos el inventario y cerrojo de la calle al trabajador del jugador
        jugador.trabajador.inventario = self.inventario
        jugador.trabajador.cerrojo    = self.cerrojo
        jugador.localizacion          = self.nombre
        self._actualizar_inventario(jugador.trabajador)
        self.jugadores.append(jugador)
        print(f"{jugador.nombre} se une a {self.nombre}.")

    # Método para iniciar todos los hilos de la calle
    def iniciar(self) -> None:
        for jugador in self.jugadores:
            jugador.trabajador.start()
        print(f"\n── {self.nombre} abierta ──")

    # Detenemos todos los procesos de la calle, deteniendo los hilos
    def detener(self) -> None:
        for jugador in self.jugadores:
            jugador.trabajador.detener()
        for jugador in self.jugadores:
            jugador.trabajador.join(timeout=10)  # ← no bloquea si el sleep es largo
        print(f"\n── {self.nombre} cerrada ──")

    # Método para consultar el inventario de la calle
    def consultar_inventario(self) -> None:
        with self.cerrojo:
            print(f"\n── Inventario de {self.nombre} ──")
            if not self.inventario:
                print(f"  La calle {self.nombre} no tiene productos disponibles")
            for item, cantidad in self.inventario.items():
                print(f"  {item}: {cantidad}")

    # Método para consultar los jugadores que se hallan en la calle
    def consultar_jugadores(self) -> None:
        print(f"\n── Jugadores en {self.nombre} ──")
        for jugador in self.jugadores:
            print(f"  {jugador.nombre} | {jugador.estado.name} | {jugador.monedas} monedas")

    # Método para switchear entre jugadores
    def cambiar_jugador(self, nombre: str) -> "Jugador | None":
        nombre = nombre.lower().strip("[]")
        for jugador in self.jugadores:
            if jugador.nombre.lower() == nombre:
                return jugador
        print(f"No existe ningún jugador llamado '{nombre}' en {self.nombre}.")
        return None



# Definimos el MUD para que corra el juego
def mud(jugador_activo: Jugador, calle: Calle) -> None:
    # Mensaje de ayuda del juego con los distintos comandos
    ayuda = """
COMANDOS:


NO ES NECESARIO PONER COMILLAS NI SÍMBOLOS DE APERTURA Y CIERRE


producir [item]                        → empezar a producir
parar                                  → parar producción
inventario                             → ver inventario de la calle
bolsa                                  → ver tu bolsa y monedas
recetas                                → ver tus recetas
precios                                → ver tus precios de producción
precio [item] [num]                    → fijar precio de producción
precio_bolsa [item] [num]              → fijar precio de reventa personal
comprar [item] [num]                   → comprar item de la calle
vender [item] [num] [jugador]          → vender desde tu bolsa (pide confirmación)
depositar [item] [num]                 → depositar item de la bolsa al taller
retirar [item] [num]                   → retirar item del taller a la bolsa
eliminar [item] [num]                  → eliminar stock de la calle
cambiar [jugador]                      → cambiar de jugador activo
ayuda                                  → mostrar este menú
salir                                  → cerrar el juego
"""
    # Mensaje de inicio del juego
    print(f"\nBienvenido a {calle.nombre}, {jugador_activo.nombre}.")
    print(ayuda)

    # Se genera el bucle MUD
    while True:
        try:
            entrada = input(f"[{jugador_activo.nombre}] > ").strip().lower()
        except KeyboardInterrupt:
            print("\nInterrupción, cerrando...")
            calle.detener()
            break

        # En el caso de que no haya inputs se prosigue
        if not entrada:
            continue
        partes  = entrada.split()
        comando = partes[0]

        # Parte de la producción del MUD, para empezar a producir
        if comando == "producir":
            if len(partes) < 2:
                jugador_activo.trabajador.consultar_recetas()
                print("Uso: producir [item]")
            else:
                item = partes[1].strip("[]")
                jugador_activo.trabajador.asignar_tarea(item)
                jugador_activo.estado = EstadoJugador.PRODUCIENDO

        # Parte de la producción del MUD, para pararla concretamente
        elif comando == "parar":
            jugador_activo.trabajador.parar()
            jugador_activo.estado = EstadoJugador.DESCANSANDO

        # Parte de las consultas del MUD, para consultar el inventario
        elif comando == "inventario":
            calle.consultar_inventario()

        # Parte de las consultas del MUD, para consultar la bolsa
        elif comando == "bolsa":
            jugador_activo.consultar_bolsa()

        # Parte de las consultas del MUD, para consultar las recetas
        elif comando == "recetas":
            jugador_activo.trabajador.consultar_recetas()

        # Parte de las consultas del MUD, para consultar los precios
        elif comando == "precios":
            precios = jugador_activo.trabajador.consultar_precios()
            print(f"\n── Precios de {jugador_activo.trabajador.nombre} ──")
            for item, precio in precios.items():
                print(f"  {item}: {precio} monedas")

        # Parte de las peticiones del MUD, para fijar precios de producción
        elif comando == "precio":
            if len(partes) < 3:
                print("Uso: precio [item] [num]")
            else:
                try:
                    jugador_activo.trabajador.fijar_precio(partes[1].strip("[]"), int(partes[2]))
                except ValueError:
                    print("El precio tiene que ser un número entero.")

        # Parte de las consultas del MUD, para ver el precio de la bolsa
        elif comando == "precio_bolsa":
            if len(partes) < 3:
                print("Uso: precio_bolsa [item] [num]")
            else:
                try:
                    jugador_activo.fijar_precio_bolsa(partes[1].strip("[]"), int(partes[2]))
                except ValueError:
                    print("El precio tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para comprar elementos
        # Busca el precio en los trabajadores de la calle
        elif comando == "comprar":
            if len(partes) < 3:
                print("Uso: comprar [item] [cantidad]")
            else:
                try:
                    item_c = partes[1].strip("[]")
                    cant_c = int(partes[2])
                    if calle.inventario.get(item_c, 0) < cant_c:
                        print(f"No hay suficiente '{item_c}' en la calle.")
                    else:
                        # Busca el precio en los trabajadores de la calle
                        precio_u = None
                        for j in calle.jugadores:
                            if item_c in j.trabajador.precios:
                                precio_u = j.trabajador.precios[item_c]
                                break
                        if precio_u is None:
                            print(f"No hay precio fijado para '{item_c}'. "
                                  f"Usa: precio {item_c} [num]")
                        else:
                            jugador_activo.comprar(item_c, cant_c,
                                                   calle.inventario,
                                                   calle.cerrojo,
                                                   precio_u)
                except ValueError:
                    print("La cantidad tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para vender elementos
        elif comando == "vender":
            if len(partes) < 4:
                print("Uso: vender [item] [cantidad] [comprador]")
            else:
                try:
                    item_v      = partes[1].strip("[]")
                    cant_v      = int(partes[2])
                    nombre_c    = partes[3].strip("[]")
                    comprador_obj = calle.cambiar_jugador(nombre_c)
                    if comprador_obj is None:
                        print(f"No se encontró al jugador '{nombre_c}'.")
                    elif comprador_obj is jugador_activo:
                        print("No puedes venderte a ti mismo.")
                    else:
                        # Precio de bolsa tiene prioridad sobre precio del trabajador
                        precio_u = (jugador_activo.precios_bolsa.get(item_v)
                                    or jugador_activo.trabajador.precios.get(item_v))
                        if precio_u is None:
                            print(f"Sin precio para '{item_v}'. "
                                  f"Usa: precio_bolsa {item_v} [num]")
                        else:
                            coste = precio_u * cant_v
                            print(f"\n{jugador_activo.nombre} ofrece {cant_v} x {item_v} "
                                  f"a {comprador_obj.nombre} por {coste} monedas.")
                            # ── Confirmación del comprador ──
                            try:
                                resp = input(f"[{comprador_obj.nombre}] ¿Aceptas? (s/n) > ").strip().lower()
                            except KeyboardInterrupt:
                                resp = "n"
                            if resp == "s":
                                jugador_activo.vender(item_v, cant_v, precio_u, comprador_obj)
                            else:
                                print(f"{comprador_obj.nombre} rechazó la oferta.")
                except ValueError:
                    print("La cantidad tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para depositar items de la bolsa al taller
        elif comando == "depositar":
            if len(partes) < 3:
                print("Uso: depositar [item] [cantidad]")
            else:
                try:
                    item_d = partes[1].strip("[]")
                    cant_d = int(partes[2])
                    # CORRECCIÓN: orden calle → jugador, coherente con comprar()
                    # para evitar inversión de locks que podría causar deadlock.
                    with calle.cerrojo:
                        if jugador_activo.inventario.get(item_d, 0) < cant_d:
                            print(f"No tienes suficiente {item_d} en la bolsa.")
                        else:
                            with jugador_activo.cerrojo:
                                jugador_activo.inventario[item_d] -= cant_d
                                calle.inventario[item_d] = calle.inventario.get(item_d, 0) + cant_d
                            print(f"Has depositado {cant_d} {item_d} en el taller.")
                except ValueError:
                    print("La cantidad tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para retirar items del taller a la bolsa
        elif comando == "retirar":
            if len(partes) < 3:
                print("Uso: retirar [item] [cantidad]")
            else:
                try:
                    item_r = partes[1].strip("[]")
                    cant_r = int(partes[2])
                    with calle.cerrojo:
                        if calle.inventario.get(item_r, 0) < cant_r:
                            print(f"No hay suficiente {item_r} en el taller.")
                        else:
                            with jugador_activo.cerrojo:
                                calle.inventario[item_r] -= cant_r
                                jugador_activo._añadir_a_inventario(item_r, cant_r)
                            print(f"Has retirado {cant_r} {item_r} a tu bolsa.")
                except ValueError:
                    print("La cantidad tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para eliminar stock
        elif comando == "eliminar":
            if len(partes) < 3:
                print("Uso: eliminar [item] [cantidad]")
            else:
                try:
                    jugador_activo.trabajador.eliminar_stock(partes[1].strip("[]"), int(partes[2]))
                except ValueError:
                    print("La cantidad tiene que ser un número entero.")

        # Parte de las peticiones del MUD, para cambiar de jugador activo
        elif comando == "cambiar":
            if len(partes) < 2:
                print("Jugadores disponibles:")
                for j in calle.jugadores:
                    print(f"  {j.nombre} | {j.estado.name} | {j.monedas} monedas")
                print("Uso: cambiar [nombre]")
            else:
                resultado = calle.cambiar_jugador(partes[1])
                if resultado is not None:
                    jugador_activo = resultado
                    print(f"Ahora controlas a {jugador_activo.nombre}.")

        # Parte de las peticiones del MUD, para recibir la ayuda
        elif comando == "ayuda":
            print(ayuda)

        # Parte de las peticiones del MUD, para salir del juego
        elif comando == "salir":
            print(f"\nHasta luego, {jugador_activo.nombre}.")
            calle.detener()
            break

        # Control de errores, para cuando el comando sea desconocido
        else:
            print(f"Comando '{comando}' desconocido. Escribe 'ayuda' para ver los comandos.")


# EJEMPLO GENERADO CON IA
# EJEMPLO PARA LA SEMANA 1
if __name__ == "__main__":


    # Recetas
    recetas_lenador = [
        {"produce": "madera", "cantidad": 1, "necesita": {}, "tiempo": 3}
    ]
    recetas_carpintero = [
        {"produce": "tablas",              "cantidad": 1, "necesita": {"madera": 2}, "tiempo": 4},
        {"produce": "muebles",             "cantidad": 1, "necesita": {"madera": 5}, "tiempo": 8},
        {"produce": "moldes_herramientas", "cantidad": 1, "necesita": {"madera": 1}, "tiempo": 2}
    ]


    # Trabajadores
    t_lenador    = Trabajador(recetas_lenador,    {}, Lock(), {"madera": 3})
    t_carpintero = Trabajador(recetas_carpintero, {}, Lock(),
                              {"tablas": 5, "muebles": 20, "moldes_herramientas": 8})


    # Jugadores
    marc  = Jugador("Marc",  t_lenador,    monedas=50)
    pedro = Jugador("Pedro", t_carpintero, monedas=50)


    # Calle
    calle = Calle("Calle del Ébano")
    calle.añadir_jugador(marc)
    calle.añadir_jugador(pedro)
    calle.iniciar()


    # Cada jugador entra al MUD en su propia terminal
    # Para probar en una sola máquina lanzamos el MUD con marc
    mud(marc, calle)
