# Importamos las librerías necesarias
from typing import Dict, List
from threading import Thread, Lock, Event
import time
from abc import ABC, abstractmethod
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
        self.nombre = ""
        self._recetas = recetas
        self.inventario = inventario
        self.cerrojo = cerrojo
        self.precios = precios
        self.receta_activa = None
        self.estado = EstadoTrabajador.INACTIVO
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



# Clase base de barrio
# IMPORTANTE: En local comparten proceso, en distribuido cada Calle corre en una máquina distinta
class Barrio(ABC):
    # Iniciamos el constructor de clases
    def __init__(self, nombre: str) -> None:
        self.nombre  = nombre
        self.calles: list[Calle] = []
        self.cerrojo = Lock()
        # Hilo secundario que corre la lógica propia del barrio (mercado o economía)
        self._hilo_barrio: Thread | None = None
        self._activo = Event()
        self._activo.set()



# Definimos los métodos privados
    # Definimos la lógica del barrio
    @abstractmethod
    def _logica_barrio(self) -> None:
        """
        BarrioComercial → redistribuye recursos.
        BarrioEconomico → ajusta precios.
        """
        pass



# Definimos los métodos públicos
    # Método para añadir una calle al barrio
    def añadir_calle(self, calle: Calle) -> None:
        if len(self.calles) >= 2:
            raise ValueError(f"{self.nombre}: máximo 2 calles por barrio.")
        self.calles.append(calle)
        print(f"{calle.nombre} se une al barrio {self.nombre}.")

    # Método para iniciar al barrio
    def iniciar(self) -> None:
        for calle in self.calles:
            calle.iniciar()
        # Arranca el hilo de lógica del barrio en segundo plano
        self._hilo_barrio = Thread(target=self._logica_barrio, daemon=True)
        self._hilo_barrio.start()
        print(f"\n── {self.nombre} abierto ──")

    # Detiene el barrio y por tanto las dos calles y por tanto los 4 trabajadores
    def detener(self) -> None:
        self._activo.clear()
        for calle in self.calles:
            calle.detener()
        if self._hilo_barrio:
            self._hilo_barrio.join(timeout=5)
        print(f"\n── {self.nombre} cerrado ──")

    # Método para consultar el estado del barrio
    def consultar_estado(self) -> None:
        print(f"\n── Estado del barrio {self.nombre} ──")
        for calle in self.calles:
            calle.consultar_inventario()
            calle.consultar_jugadores()

    # Método para consultar la contabilidad de todo el conjunto del barrio
    def consultar_contabilidad(self) -> None:
        print(f"\n── Contabilidad de {self.nombre} ──")
        for calle in self.calles:
            print(f"  {calle.nombre}:")
            for jugador in calle.jugadores:
                print(f"    {jugador.nombre}: {jugador.monedas} monedas")

    # Método para hacer un ranking de las calles viendo cuál es la que más genera por barrio
    def ranking_calles(self) -> None:
        """
        Muestra las calles del barrio ordenadas por la riqueza total
        de sus jugadores (monedas acumuladas).
        """
        ranking = []
        for calle in self.calles:
            total = sum(jugador.monedas for jugador in calle.jugadores)
            ranking.append((calle.nombre, total))
        ranking.sort(key=lambda x: x[1], reverse=True)
        print(f"\n── Ranking de calles — {self.nombre} ──")
        for posicion, (nombre_calle, total) in enumerate(ranking, start=1):
            print(f"  {posicion}. {nombre_calle}: {total} monedas en total")

    # Obtenemos el total de monedas del barrio, sumando las monedas de los 4 jugadores
    def total_monedas(self) -> None:
        total_barrio = 0
        print(f"\n── Riqueza total de {self.nombre} ──")
        for calle in self.calles:
            total_calle = sum(jugador.monedas for jugador in calle.jugadores)
            total_barrio += total_calle
            print(f"  {calle.nombre}: {total_calle} monedas")
            for jugador in calle.jugadores:
                print(f"    {jugador.nombre}: {jugador.monedas} monedas")
        print(f"  ────────────────────────")
        print(f"  TOTAL BARRIO: {total_barrio} monedas")

    # Método para cambiar jugadores entre las distintas calles
    def cambiar_jugador(self, nombre: str) -> "tuple[Jugador, Calle] | None":
        nombre = nombre.lower().strip("[]")
        for calle in self.calles:
            for jugador in calle.jugadores:
                if jugador.nombre.lower() == nombre:
                    return jugador, calle
        print(f"No existe ningún jugador llamado '{nombre}' en {self.nombre}.")
        return None

    # Método para obtener precios
    def obtener_precio(self, item: str, calle_origen: "Calle") -> "int | None":
        """Devuelve el precio vigente del item en la calle origen."""
        for jugador in calle_origen.jugadores:
            if item in jugador.trabajador.precios:
                return jugador.trabajador.precios[item]
        return None

    # Método para ver todo el almacenamiento del barrio
    def consultar_almacen(self) -> None:
        almacen: dict[str, int] = {}
        for calle in self.calles:
            with calle.cerrojo:
                for item, cantidad in calle.inventario.items():
                    almacen[item] = almacen.get(item, 0) + cantidad
        print(f"\n── Almacén de {self.nombre} ──")
        if not almacen:
            print("  (vacío)")
        else:
            for item, cantidad in almacen.items():
                # Desglose por calle debajo de cada item
                print(f"  {item}: {cantidad} (total)")
                for calle in self.calles:
                    parcial = calle.inventario.get(item, 0)
                    if parcial > 0:
                        print(f"    {calle.nombre}: {parcial}")



# Iniciamos la clase Barrio Comercial
class BarrioComercial(Barrio):
    # Iniciamos el constructor de clases
    def __init__(self, nombre: str, intervalo: int = 15) -> None:
        super().__init__(nombre)
        self.intervalo        = intervalo  # segundos entre ciclos de redistribución
        self.umbral_exceso: int = 5
        self.precios_mercado: dict[str, int] = {}



# Definimos los métodos privados
    # Definimos la lógica del barrio
    def _logica_barrio(self) -> None:
        while self._activo.is_set():
            time.sleep(self.intervalo)
            self._redistribuir_recursos()

    # Método para redistribuir los recursos entre las distintas calles
    def _redistribuir_recursos(self) -> None:
        if len(self.calles) < 2:
            return
        calle_a, calle_b = self.calles
        # Abrimos todos los cerrojos
        with self.cerrojo:
            with calle_a.cerrojo:
                with calle_b.cerrojo:
                    # Snapshot para que los dos bucles lean el estado inicial
                    snap_a = dict(calle_a.inventario)
                    snap_b = dict(calle_b.inventario)
                    # A → B
                    for item in snap_a:
                        exceso_a  = snap_a[item] - self.umbral_exceso
                        deficit_b = self.umbral_exceso - snap_b.get(item, 0)
                        if exceso_a > 0 and deficit_b > 0:
                            transferir = min(exceso_a, deficit_b)
                            calle_a.inventario[item] -= transferir
                            calle_b.inventario[item] = calle_b.inventario.get(item, 0) + transferir
                            print(f"[Mercado {self.nombre}] {transferir} {item}: "
                                  f"{calle_a.nombre} → {calle_b.nombre}.")
                    # B → A
                    for item in snap_b:
                        exceso_b  = snap_b[item] - self.umbral_exceso
                        deficit_a = self.umbral_exceso - snap_a.get(item, 0)
                        if exceso_b > 0 and deficit_a > 0:
                            transferir = min(exceso_b, deficit_a)
                            calle_b.inventario[item] -= transferir
                            calle_a.inventario[item] = calle_a.inventario.get(item, 0) + transferir
                            print(f"[Mercado {self.nombre}] {transferir} {item}: "
                                  f"{calle_b.nombre} → {calle_a.nombre}.")



    # Método para consultar el mercado y los distintos objetos que tiene el barrio
    def consultar_mercado(self) -> None:
        print(f"\n── Mercado de {self.nombre} (umbral exceso: {self.umbral_exceso}) ──")
        for calle in self.calles:
            calle.consultar_inventario()

    # Método para fijar los precios del mercado del barrio
    def fijar_precio_mercado(self, item: str, precio: int) -> None:
        """Fija un precio centralizado de mercado para un item."""
        self.precios_mercado[item] = precio
        print(f"[Mercado {self.nombre}] Precio de mercado de {item}: {precio} monedas.")

    # Método para obtener los precios del mercado del barrio
    def obtener_precio(self, item: str, calle_origen: "Calle") -> "int | None":
        """Precio de mercado tiene prioridad. Si no existe, usa el del trabajador."""
        if item in self.precios_mercado:
            return self.precios_mercado[item]
        return super().obtener_precio(item, calle_origen)



# Iniciamos la clase Barrio Económico
class BarrioEconomico(Barrio):
    """
    Cada N segundos ajusta precios según oferta:
      - stock > umbral_alto  → baja precio (exceso de oferta)
      - stock < umbral_bajo  → sube precio (escasez)
    """
    # Definimos el constructor de clases
    def __init__(self, nombre: str, intervalo: int = 20) -> None:
        super().__init__(nombre)
        self.intervalo    = intervalo
        self.umbral_alto: int  = 10    # más de 10 → baja precio
        self.umbral_bajo: int  = 2     # menos de 2 → sube precio
        self.variacion: float  = 0.2   # 20% de variación por ciclo
        self.precio_max: int   = 50    # techo para evitar escalada infinita por escasez
        # Solo ajustamos precios de items que alguna vez tuvieron stock > 0
        self._items_vistos: set[str] = set()



# Definimos los métodos privados
    # Definimos la lógica económica del barrio
    def _logica_barrio(self) -> None:
        while self._activo.is_set():
            time.sleep(self.intervalo)
            self._registrar_items_con_stock()
            self._ajustar_precios()

    # Registra los items que actualmente tienen stock > 0 para no penalizar
    # items que nunca se han producido
    def _registrar_items_con_stock(self) -> None:
        for calle in self.calles:
            with calle.cerrojo:
                for item, cantidad in calle.inventario.items():
                    if cantidad > 0:
                        self._items_vistos.add(item)

    # Ajustamos el precio de los productos incluidos en el barrio
    def _ajustar_precios(self) -> None:
        # Abrimos los cerrojos y modificamos los precios
        for calle in self.calles:
            with calle.cerrojo:
                for jugador in calle.jugadores:
                    for item, precio_actual in jugador.trabajador.precios.items():
                        # Solo actuamos sobre items que alguna vez tuvieron stock
                        if item not in self._items_vistos:
                            continue
                        stock = calle.inventario.get(item, 0)
                        if stock > self.umbral_alto:
                            nuevo_precio = max(1, int(precio_actual * (1 - self.variacion)))
                            jugador.trabajador.precios[item] = nuevo_precio
                            print(
                                f"[Economía {self.nombre}] "
                                f"Exceso de {item} ({stock} uds.) → "
                                f"precio {precio_actual} → {nuevo_precio} monedas."
                            )
                        elif stock < self.umbral_bajo:
                            nuevo_precio = min(self.precio_max,
                                               int(precio_actual * (1 + self.variacion)))
                            jugador.trabajador.precios[item] = nuevo_precio
                            print(
                                f"[Economía {self.nombre}] "
                                f"Escasez de {item} ({stock} uds.) → "
                                f"precio {precio_actual} → {nuevo_precio} monedas."
                            )



# Definimos el nuevo mud
# Generamos el mud para que corra el juego
def mud(jugador_activo: Jugador, calle: Calle, barrio: "Barrio | None" = None) -> None:
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
almacen                                → ver almacén del barrio
cambiar [jugador]                      → cambiar de jugador activo
ranking                                → ranking de calles por riqueza
riqueza                                → riqueza total del barrio
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
            if barrio:
                barrio.detener()
            else:
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
        elif comando == "comprar":
            if len(partes) < 3:
                print("Uso: comprar [item] [cantidad]")
            else:
                try:
                    item_c = partes[1].strip("[]")
                    cant_c = int(partes[2])

                    calle_origen = None

                    # 1. Busca stock en la calle actual
                    if calle.inventario.get(item_c, 0) >= cant_c:
                        calle_origen = calle

                    # 2. Si no, busca en el resto del barrio
                    if calle_origen is None and barrio:
                        for c in barrio.calles:
                            if c is calle:
                                continue
                            if c.inventario.get(item_c, 0) >= cant_c:
                                calle_origen = c
                                break

                    if calle_origen is None:
                        print(f"No hay suficiente '{item_c}' disponible en el barrio.")
                    else:
                        # Obtiene el precio según el tipo de barrio
                        if barrio:
                            precio_u = barrio.obtener_precio(item_c, calle_origen)
                        else:
                            precio_u = None
                            for j in calle_origen.jugadores:
                                if item_c in j.trabajador.precios:
                                    precio_u = j.trabajador.precios[item_c]
                                    break

                        if precio_u is None:
                            print(f"No hay precio fijado para '{item_c}'. "
                                  f"Usa: precio {item_c} [num]")
                        else:
                            if calle_origen is not calle:
                                print(f"(Comprando de {calle_origen.nombre})")
                            jugador_activo.comprar(item_c, cant_c,
                                                   calle_origen.inventario,
                                                   calle_origen.cerrojo,
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

                    comprador_obj = None
                    if barrio:
                        res = barrio.cambiar_jugador(nombre_c)
                        if res:
                            comprador_obj = res[0]
                    else:
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

        # Parte de las peticiones del MUD, para recibir la ayuda
        elif comando == "ayuda":
            print(ayuda)

        # Parte de las peticiones del MUD, para salir del juego
        elif comando == "salir":
            print(f"\nHasta luego, {jugador_activo.nombre}.")
            if barrio:
                barrio.detener()
            else:
                calle.detener()
            break

        # Parte de las peticiones del MUD, para cambiar de jugador activo
        elif comando == "cambiar":
            if len(partes) < 2:
                # Lista todos los jugadores: del barrio si existe, si no de la calle
                if barrio:
                    print("Jugadores disponibles en el barrio:")
                    for c in barrio.calles:
                        marca = " ◄ (aquí)" if c.nombre == calle.nombre else ""
                        print(f"  [{c.nombre}]{marca}")
                        for j in c.jugadores:
                            print(f"    {j.nombre} | {j.estado.name} | {j.monedas} monedas")
                else:
                    print("Jugadores disponibles:")
                    for j in calle.jugadores:
                        print(f"  {j.nombre} | {j.estado.name} | {j.monedas} monedas")
                print("Uso: cambiar [nombre]")
            else:
                if barrio:
                    resultado = barrio.cambiar_jugador(partes[1])
                    if resultado is not None:
                        jugador_activo, calle = resultado  # ← actualiza AMBAS
                        print(f"Ahora controlas a {jugador_activo.nombre} "
                              f"en {calle.nombre}.")
                else:
                    resultado = calle.cambiar_jugador(partes[1])
                    if resultado is not None:
                        jugador_activo = resultado
                        print(f"Ahora controlas a {jugador_activo.nombre}.")

        # Parte de las consultas del MUD, para ver el ranking de calles
        elif comando == "ranking":
            if barrio:
                barrio.ranking_calles()
            else:
                print("No estás en un barrio todavía.")

        # Parte de las consultas del MUD, para ver la riqueza total del barrio
        elif comando == "riqueza":
            if barrio:
                barrio.total_monedas()
            else:
                jugador_activo.consultar_bolsa()

        # Parte de las consultas del MUD, para ver todos los objetos de un barrio
        elif comando == "almacen":
            if barrio:
                barrio.consultar_almacen()
            else:
                print("No estás en un barrio todavía.")

        # Control de errores, para cuando el comando sea desconocido
        else:
            print(f"Comando '{comando}' desconocido. Escribe 'ayuda' para ver los comandos.")


# EJEMPLO GENERADO CON IA
# EJEMPLO PARA LA SEMANA 2
if __name__ == "__main__":


    # ── Calle del Ébano (madera / carpintería) ──
    recetas_lenador = [
        {"produce": "madera", "cantidad": 1, "necesita": {}, "tiempo": 3}
    ]
    recetas_carpintero = [
        {"produce": "tablas",  "cantidad": 1, "necesita": {"madera": 2}, "tiempo": 4},
        {"produce": "muebles", "cantidad": 1, "necesita": {"madera": 5}, "tiempo": 8},
    ]
    t_lenador    = Trabajador(recetas_lenador,    {}, Lock(), {"madera": 3})
    t_carpintero = Trabajador(recetas_carpintero, {}, Lock(), {"tablas": 5, "muebles": 20})
    marc  = Jugador("Marc",  t_lenador,    monedas=50)
    pedro = Jugador("Pedro", t_carpintero, monedas=50)
    calle_ebano = Calle("Calle del Ébano")
    calle_ebano.añadir_jugador(marc)
    calle_ebano.añadir_jugador(pedro)


    # ── Calle del Hierro (minería / herrería) ──
    recetas_minero = [
        {"produce": "mineral", "cantidad": 1, "necesita": {}, "tiempo": 4}
    ]
    recetas_herrero = [
        {"produce": "hierro",       "cantidad": 1, "necesita": {"mineral": 2}, "tiempo": 5},
        {"produce": "herramientas", "cantidad": 1, "necesita": {"hierro": 1},  "tiempo": 6},
    ]
    t_minero  = Trabajador(recetas_minero,  {}, Lock(), {"mineral": 2})
    t_herrero = Trabajador(recetas_herrero, {}, Lock(), {"hierro": 8, "herramientas": 15})
    Juan    = Jugador("Juan",    t_minero,  monedas=50)
    Jorge = Jugador("Jorge", t_herrero, monedas=50)
    calle_hierro = Calle("Calle del Hierro")
    calle_hierro.añadir_jugador(Juan)
    calle_hierro.añadir_jugador(Jorge)


    # ── Barrio Comercial ──
    barrio = BarrioComercial("Barrio del Mercado", intervalo=15)
    barrio.añadir_calle(calle_ebano)
    barrio.añadir_calle(calle_hierro)
    barrio.iniciar()


    # ── MUD: Marc arranca el juego ──
    mud(marc, calle_ebano, barrio)
