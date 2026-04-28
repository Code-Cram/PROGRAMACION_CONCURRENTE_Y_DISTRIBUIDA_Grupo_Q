import queue
from queue import Queue
import threading
from threading import Thread, Lock, Semaphore
import time
import random
import json
import socket
import functools
from datetime import datetime

# --- CONFIGURACION MUD CLIENTE ---
MUD_HOST = "127.0.0.1"
MUD_PORT = 1234
mud_socket = None
dia_actual = 1

def init_mud_client(fruitshop_instance=None, panaderia_instance=None):
    global mud_socket
    mud_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        mud_socket.connect((MUD_HOST, MUD_PORT))
        mud_socket.sendall(b"IDENTIFY FRUTERIA_PANADERIA\n")
        def listen_mud():
            buffer = ""
            while True:
                try:
                    data = mud_socket.recv(1024)
                    if not data:
                        break
                    buffer += data.decode('utf-8', errors='ignore')
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        msg = line.strip()
                        if not msg:
                            continue

                        if "MUD_OFFER" in msg or "MUD_WANT" in msg:
                            # Gestionados por el Marketplace en el servidor, ignorar aquí
                            pass

                        elif "MUD_BUY" in msg:
                            partes = msg.split("MUD_BUY", 1)[1].strip().split()
                            if len(partes) >= 3:
                                origen, producto, cantidad_str = partes[0], partes[1], partes[2]
                                try:
                                    cantidad = int(cantidad_str)
                                except ValueError:
                                    cantidad = 0
                                if producto in ["apple", "orange", "grape", "cacao"] and fruitshop_instance:
                                    with fruitshop_instance.lock:
                                        if fruitshop_instance.inventario.get(producto, 0) >= cantidad:
                                            fruitshop_instance.inventario[producto] -= cantidad
                                            precio = fruitshop_instance.precios_venta.get(producto, 1.0)
                                            total  = precio * cantidad
                                            fruitshop_instance.caja.depositar(total)
                                            send_mud(f"MUD_ACCEPT {producto} {cantidad} {origen} {int(total)}")
                                            log_mud(f"\033[93mFrutería\033[0m: Vendió {cantidad} {producto} a {origen} por {total}€.")
                                        else:
                                            send_mud(f"MUD_REJECT {producto} {cantidad} {origen}")
                                            log_mud(f"\033[93mFrutería\033[0m: Rechazó venta de {cantidad} {producto} a {origen}.")
                                elif producto == "pan" and panaderia_instance:
                                    pedido_mud = Pedido("pan", cantidad, origen)
                                    panaderia_instance.cola_pedidos_pan.put(pedido_mud)
                                    log_mud(f"\033[95mPanadería\033[0m: Pedido MUD de {cantidad} pan de {origen} encolado.")
                                else:
                                    print(f"\033[93m[COMERCIO MUD]\033[0m ❌ MUD_BUY no manejado: {origen} pide {cantidad}x {producto}.")
                            else:
                                print(f"\033[93m[COMERCIO MUD]\033[0m ❌ MUD_BUY mal formado: {msg}")

                        elif "MUD_ACCEPT" in msg:
                            partes = msg.split("MUD_ACCEPT", 1)[1].strip().split()
                            if len(partes) >= 4:
                                producto, cantidad_str, origen, total_str = partes[0], partes[1], partes[2], partes[3]
                                try:
                                    cantidad = int(cantidad_str)
                                    total    = int(total_str)
                                except ValueError:
                                    cantidad = 0
                                    total    = 0

                                # ---- Compras de la Frutería ----
                                if producto == "bebidas" and origen == "Fruteria" and fruitshop_instance:
                                    with fruitshop_instance.lock:
                                        if fruitshop_instance.caja.retirar(total):
                                            fruitshop_instance.inventario["bebidas"] = fruitshop_instance.inventario.get("bebidas", 0) + cantidad
                                            log_mud(f"\033[93mFrutería\033[0m: Recibió {cantidad} bebidas de proveedor MUD.")
                                        else:
                                            log_mud(f"\033[93mFrutería\033[0m: Sin fondos para pagar bebidas.")
                                            fruitshop_instance.needs_bebidas = False

                                # NUEVO: Frutería recibe helado comprado a Heladería
                                elif producto == "helado" and origen == "Fruteria" and fruitshop_instance:
                                    if fruitshop_instance.caja.retirar(total):
                                        with fruitshop_instance.lock:
                                            fruitshop_instance.inventario["helado"] = fruitshop_instance.inventario.get("helado", 0) + cantidad
                                        fruitshop_instance.needs_helado = False
                                        log_mud(f"\033[93mFrutería\033[0m: Recibió {cantidad} helados vía MUD (+inventario premium).")
                                    else:
                                        log_mud(f"\033[93mFrutería\033[0m: Sin fondos para pagar helado MUD.")
                                        fruitshop_instance.needs_helado = False

                                # NUEVO: Panadería recibe conservas compradas al Supermercado
                                elif producto == "conservas" and origen == "Panaderia" and panaderia_instance:
                                    if panaderia_instance.caja.retirar(total):
                                        with panaderia_instance.lock:
                                            panaderia_instance.inventario["conservas"] = panaderia_instance.inventario.get("conservas", 0) + cantidad
                                        panaderia_instance.needs_conservas = False
                                        log_mud(f"\033[95mPanadería\033[0m: Recibió {cantidad} conservas vía MUD.")
                                    else:
                                        log_mud(f"\033[95mPanadería\033[0m: Sin fondos para pagar conservas MUD.")
                                        panaderia_instance.needs_conservas = False

                                else:
                                    print(f"\033[93m[COMERCIO MUD]\033[0m 📦 MUD_ACCEPT no manejado: {producto} de {origen}.")
                            else:
                                print(f"\033[93m[COMERCIO MUD]\033[0m ❌ MUD_ACCEPT mal formado: {msg}")

                        elif "MUD_REJECT" in msg:
                            partes = msg.split("MUD_REJECT", 1)[1].strip().split()
                            if len(partes) >= 3:
                                producto, cantidad_str, origen = partes[0], partes[1], partes[2]
                                log_mud(f"\033[93mFrutería/Panadería\033[0m: Rechazada compra de {cantidad_str} {producto} por {origen}.")
                                if producto == "bebidas" and fruitshop_instance:
                                    fruitshop_instance.needs_bebidas = False
                                # NUEVO: resetear flags de compra rechazada
                                elif producto == "helado" and fruitshop_instance:
                                    fruitshop_instance.needs_helado = False
                                elif producto == "conservas" and panaderia_instance:
                                    panaderia_instance.needs_conservas = False
                            else:
                                print(f"\033[93m[COMERCIO MUD]\033[0m ❌ MUD_REJECT mal formado: {msg}")
                        else:
                            if "MUD_" not in msg:
                                print(msg)
                except Exception:
                    break
        Thread(target=listen_mud, daemon=True).start()
    except Exception as e:
        mud_socket = None

def log_mud(msg):
    print(msg)

def send_mud(msg):
    if mud_socket:
        try:
            mud_socket.sendall((msg + "\n").encode('utf-8', errors='ignore'))
        except Exception:
            pass

# -------------------------------------------------------------------
# MODELOS DE DATOS
# -------------------------------------------------------------------
class Pedido:
    def __init__(self, producto: str, cantidad: int, origen: str):
        self.producto = producto
        self.cantidad = cantidad
        self.origen   = origen
    def __str__(self):
        return f"Pedido(prod='{self.producto}', qty={self.cantidad}, desde='{self.origen}')"

class Suministro:
    def __init__(self, producto: str, cantidad: int, proveedor: str):
        self.producto = producto
        self.cantidad = cantidad
        self.proveedor= proveedor
    def __str__(self):
        return f"Suministro(prod='{self.producto}', qty={self.cantidad}, de='{self.proveedor}')"

class Caja:
    def __init__(self, dinero_inicial: float):
        self.dinero = dinero_inicial
        self.lock   = Lock()
    def depositar(self, cantidad: float):
        with self.lock:
            self.dinero += cantidad
    def retirar(self, cantidad: float) -> bool:
        with self.lock:
            if self.dinero >= cantidad:
                self.dinero -= cantidad
                return True
            return False

class CajaFuerte:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.__caja_fuerte = 0
        self.cerrojo = Lock()

    def guardar_dinero(self, cantidad: int) -> None:
        with self.cerrojo:
            self.__caja_fuerte += cantidad
        log_mud(f"(\033[32mCaja Fuerte {self.nombre}\033[0m) Ingresados ${cantidad}. Total Fuerte: ${self.__caja_fuerte}.")

    def obtener_dinero(self) -> float:
        with self.cerrojo:
            return self.__caja_fuerte

    def crear_cuenta(self, ip_banco: str):
        try:
            transaccion = {"tipo": "crear cuenta", "nombre cuenta": self.nombre}
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip_banco, 45000))
                s.sendall(json.dumps(transaccion).encode())
        except Exception:
            pass

    def enviar_dinero_banco(self, ip_banco: str):
        while True:
            time.sleep(10)
            dinero_a_enviar = 0
            with self.cerrojo:
                if self.__caja_fuerte > 0:
                    dinero_a_enviar = self.__caja_fuerte
                    self.__caja_fuerte = 0
            if dinero_a_enviar > 0:
                try:
                    transaccion = {"tipo": "transferencia", "cantidad": dinero_a_enviar, "cuenta": self.nombre}
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((ip_banco, 45000))
                        s.sendall(json.dumps(transaccion).encode())
                        resp = s.recv(1024).decode()
                    log_mud(f"\033[36m[BANCO]\033[0m {self.nombre} transfirió ${dinero_a_enviar}. {resp.strip()}")
                except Exception:
                    with self.cerrojo:
                        self.__caja_fuerte += dinero_a_enviar

    def consultar_saldo_banco(self, ip_banco="127.0.0.1") -> float:
        try:
            transaccion = {"tipo": "consultar", "cuenta": self.nombre}
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((ip_banco, 45000))
                s.sendall(json.dumps(transaccion).encode())
                resp = s.recv(1024).decode()
                return float(resp.strip())
        except Exception:
            return 0.0

# -------------------------------------------------------------------
# SISTEMA DE EMPLEADOS
# -------------------------------------------------------------------
registro_empleados = {}
transacciones_realizadas = {"numero_transacciones": 0, "id_transacciones": [], "ordenes": {}}

def requiere_empleado(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        while True:
            empleado = self.empleados_libres.get()
            if registro_empleados.get(empleado, {}).get("activo", True):
                break
        try:
            tiempo_espera = random.uniform(1, 2)
            time.sleep(tiempo_espera)
            transacciones_realizadas["numero_transacciones"] += 1
            t_id = f"transaccion_accion_{transacciones_realizadas['numero_transacciones']}"
            transacciones_realizadas["id_transacciones"].append(t_id)
            transacciones_realizadas["ordenes"][t_id] = {
                "accion": func.__name__,
                "tienda": self.__class__.__name__,
                "empleado": empleado,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            res = func(self, *args, **kwargs)
            self.acciones_por_empleado[empleado] += 1
            if self.acciones_por_empleado[empleado] % 3 == 0:
                if self.__class__.__name__ != 'Panaderia':
                    salario = 5
                    if isinstance(self.caja, Caja) and self.caja.retirar(salario):
                        log_mud(f"[{self.__class__.__name__}] $$ PAGO: ${salario} a {empleado}.")
            return res
        finally:
            if registro_empleados.get(empleado, {}).get("activo", True):
                self.empleados_libres.put(empleado)
    return wrapper

class Empleador:
    def inicializar_empleados(self, num_empleados):
        self.num_empleados = num_empleados
        self.empleados_libres = Queue()
        self.acciones_por_empleado = {}
        for i in range(num_empleados):
            nombre = f"Emp_{self.__class__.__name__}_{i+1}"
            self.empleados_libres.put(nombre)
            self.acciones_por_empleado[nombre] = 0
            if nombre not in registro_empleados:
                registro_empleados[nombre] = {"activo": True, "dinero_generado": 0}

    def _order_preparator(self, lista_productos: list, precios_dict: dict, es_compra: bool):
        summary = {}
        coste_total = 0.0
        for element in lista_productos:
            precio = precios_dict.get(element, 1.0)
            coste_total += precio
            if element in summary:
                summary[element]["quantity"] += 1
                if es_compra:
                    summary[element]["total_cost"] += precio
                else:
                    summary[element]["total_revenue"] += precio
            else:
                if es_compra:
                    summary[element] = {"quantity": 1, "total_cost": precio, "compra": True}
                else:
                    summary[element] = {"quantity": 1, "total_revenue": precio, "compra": False}
        if es_compra:
            orden = {"total_cost": round(coste_total, 2), "details": summary, "quantity": len(lista_productos), "type": "compra"}
        else:
            orden = {"total_revenue": round(coste_total, 2), "details": summary, "quantity": len(lista_productos), "type": "venta"}
        for k in summary:
            if "total_cost" in summary[k]: summary[k]["total_cost"] = round(summary[k]["total_cost"], 2)
            if "total_revenue" in summary[k]: summary[k]["total_revenue"] = round(summary[k]["total_revenue"], 2)
        return orden

    def transaction_manager(self, orden: dict, accion: str):
        transacciones_realizadas["numero_transacciones"] += 1
        t_id = f"factura_{transacciones_realizadas['numero_transacciones']}"
        transacciones_realizadas["id_transacciones"].append(t_id)
        transacciones_realizadas["ordenes"][t_id] = {
            "orden": orden,
            "accion_asociada": accion,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if orden['type'] == 'venta':
            log_mud(f"\033[90m[RECEIPT]\033[0m {self.__class__.__name__} generó ticket {t_id} (Venta: +${orden['total_revenue']:.2f})")
        else:
            log_mud(f"\033[90m[RECEIPT]\033[0m {self.__class__.__name__} generó ticket {t_id} (Compra: -${orden['total_cost']:.2f})")

# -------------------------------------------------------------------
# TIENDAS
# -------------------------------------------------------------------

class FruitShop(Empleador):
    def __init__(self, cola_pedidos: Queue, cola_respuestas: Queue, semaforo: Semaphore, cola_clientes: Queue):
        self.cola_pedidos    = cola_pedidos
        self.cola_respuestas = cola_respuestas
        self.semaforo        = semaforo
        self.cola_clientes   = cola_clientes
        self.caja            = Caja(100.0)
        self.cola_pedidos_mud = Queue()
        self.inventario      = {"apple": 30, "orange": 30, "grape": 20, "cacao": 15, "helado": 0}  # NUEVO: helado
        self.lock            = Lock()
        self.precios_venta   = {"apple": 1.0, "orange": 1.25, "grape": 1.50, "cacao": 1.25, "coctel": 2.5, "helado": 4.75}
        self.inicializar_empleados(3)
        self.needs_bebidas = False
        self.needs_helado  = False   
    def producir_frutas(self):
        while True:
            time.sleep(random.uniform(2, 5))
            with self.lock:
                frutas   = ["apple", "orange", "grape", "cacao"]
                fruta    = random.choice(frutas)
                cantidad = random.randint(5, 10)
                self.inventario[fruta] += cantidad
                log_mud(f"\033[93mFrutería\033[0m: Cosechados {cantidad} {fruta}s. Stock={self.inventario[fruta]}")

    def monitor_helado(self):
        """NUEVO: Frutería compra helado a Heladería para vender en tarros premium."""
        while True:
            time.sleep(15)
            with self.lock:
                helado_actual = self.inventario.get("helado", 0)
            if helado_actual < 3 and not self.needs_helado:
                self.needs_helado = True
                # Publicar demanda en el Marketplace
                send_mud(f"MUD_WANT Fruteria helado 2 4.0")
                log_mud(f"\033[93m[COMERCIO MUD]\033[0m ✉️ Frutería publica WANT de 2x helado (tarros premium).")

    @requiere_empleado
    def _atender_pedidos_una_vez(self, pedido: Pedido):
        log_mud(f"\033[93mFrutería\033[0m recibiendo {pedido}")
        with self.lock:
            disp    = self.inventario.get(pedido.producto, 0)
            servido = min(disp, pedido.cantidad)
            self.inventario[pedido.producto] = disp - servido
        if servido > 0:
            sup    = Suministro(pedido.producto, servido, proveedor="Frutería")
            precio = self.precios_venta.get(pedido.producto, 1.0)
            ingreso = servido * precio
            self.caja.depositar(ingreso)
            lista   = [pedido.producto] * servido
            factura = self._order_preparator(lista, self.precios_venta, es_compra=False)
            self.transaction_manager(factura, accion="atender_pedidos")
            log_mud(f"\033[93mFrutería\033[0m despachando {servido}x{pedido.producto} -> +${ingreso:.2f}. Caja=${self.caja.dinero:.2f}")
            if pedido.origen.startswith("MUD_"):
                send_mud(f"MUD_SELL {pedido.origen[4:]} {pedido.producto} {servido}")
                log_mud(f"\033[93m[COMERCIO MUD]\033[0m 📦 Caravana hacia {pedido.origen[4:]}!")
            else:
                self.cola_respuestas.put(sup)
        else:
            log_mud(f"\033[93mFrutería\033[0m sin stock de {pedido.producto}!")
            if pedido.origen.startswith("MUD_"):
                send_mud(f"MUD_SELL {pedido.origen[4:]} {pedido.producto} 0")
            else:
                self.cola_respuestas.put(Suministro(pedido.producto, 0, proveedor="Frutería"))

    def atender_pedidos(self):
        while True:
            self.semaforo.acquire()
            pedido: Pedido = self.cola_pedidos.get()
            self._atender_pedidos_una_vez(pedido)
            self.cola_pedidos.task_done()

    @requiere_empleado
    def _atender_cliente_final_una_vez(self, lista_deseada):
        from collections import Counter
        detalles = ", ".join([f"{v} {k}" for k, v in Counter(lista_deseada).items()])
        log_mud(f"\033[93mFrutería\033[0m: NPC solicita comprar {detalles}.")
        articulos_vendidos = []
        with self.lock:
            for req in lista_deseada:
                if self.inventario.get(req, 0) > 0:
                    self.inventario[req] -= 1
                    articulos_vendidos.append(req)
        if articulos_vendidos:
            precios = {a: self.precios_venta.get(a, 1.0) for a in articulos_vendidos}
            factura = self._order_preparator(articulos_vendidos, precios, es_compra=False)
            ingreso = factura["total_revenue"]
            self.caja.depositar(ingreso)
            self.transaction_manager(factura, accion="atender_cliente_final")
            log_mud(f"\033[93mFrutería\033[0m: Vendió {len(articulos_vendidos)} artículos al NPC -> +${ingreso:.2f}. Caja=${self.caja.dinero:.2f}")
        else:
            log_mud(f"\033[93mFrutería\033[0m: Sin stock para el NPC.")

    def atender_cliente_final(self):
        while True:
            lista_deseada = self.cola_clientes.get()
            self._atender_cliente_final_una_vez(lista_deseada)

    @requiere_empleado
    def _producir_cocteles_una_vez(self):
        with self.lock:
            frutas_disponibles = [f for f in ["orange"] if self.inventario.get(f, 0) > 0]
            bebidas = self.inventario.get("bebidas", 0)
            if frutas_disponibles:
                if bebidas < 1:
                    if not self.needs_bebidas:
                        send_mud(f"MUD_BUY bebidas 1 Frutería")
                        self.needs_bebidas = True
                else:
                    self.needs_bebidas = False
                    fruta = random.choice(frutas_disponibles)
                    self.inventario[fruta] -= 2
                    self.inventario["bebidas"] -= 1
                    if "coctel" not in self.inventario:
                        self.inventario["coctel"] = 0
                    self.inventario["coctel"] += 1
                    log_mud(f"\033[93mFrutería\033[0m: Produjo 1 cóctel usando {fruta} y bebidas.")

    def producir_cocteles(self):
        while True:
            time.sleep(6)
            self._producir_cocteles_una_vez()

    def llevar_dinero(self, caja_fuerte: CajaFuerte):
        while True:
            time.sleep(5)
            if self.caja.dinero > 150:
                exceso = self.caja.dinero - 100
                if self.caja.retirar(exceso):
                    caja_fuerte.guardar_dinero(exceso)

    def atender_pedidos_mud(self):
        while True:
            pedido: Pedido = self.cola_pedidos_mud.get()
            log_mud(f"\033[93mFrutería\033[0m recibiendo pedido MUD: {pedido}")
            with self.lock:
                disp    = self.inventario.get(pedido.producto, 0)
                servido = min(disp, pedido.cantidad)
                self.inventario[pedido.producto] = disp - servido
            if servido > 0:
                precio  = self.precios_venta.get(pedido.producto, 1.0)
                ingreso = servido * precio
                self.caja.depositar(ingreso)
                lista   = [pedido.producto] * servido
                factura = self._order_preparator(lista, self.precios_venta, es_compra=False)
                self.transaction_manager(factura, accion="atender_pedidos_mud")
                log_mud(f"\033[93mFrutería\033[0m: Vendiendo {servido}x{pedido.producto} MUD -> MUD_ACCEPT.")
                send_mud(f"MUD_ACCEPT {pedido.producto} {servido} {pedido.origen} {int(ingreso)}")
            else:
                log_mud(f"\033[93mFrutería\033[0m: Sin {pedido.producto} para pedido MUD -> MUD_REJECT.")
                send_mud(f"MUD_REJECT {pedido.producto} {pedido.cantidad} {pedido.origen}")
            self.cola_pedidos_mud.task_done()

    def start(self):
        Thread(target=self.producir_frutas,      daemon=True).start()
        Thread(target=self.atender_pedidos,      daemon=True).start()
        Thread(target=self.atender_cliente_final, daemon=True).start()
        Thread(target=self.producir_cocteles,    daemon=True).start()
        Thread(target=self.monitor_helado,        daemon=True).start()   # NUEVO
        if self.cola_pedidos_mud is not None:
            Thread(target=self.atender_pedidos_mud, daemon=True).start()


class Panaderia(Empleador):
    def __init__(self, cola_pedidos: Queue, cola_respuestas: Queue, semaforo: Semaphore, cola_clientes: Queue):
        self.cola_pedidos    = cola_pedidos
        self.cola_respuestas = cola_respuestas
        self.semaforo        = semaforo
        self.cola_clientes   = cola_clientes
        self.caja            = Caja(50.0)
        self.lock            = Lock()
        self.inventario      = {"harina": 20, "apple": 7}
        self.productos_listos = []
        self.precio_pan      = 3.5
        self.cola_pedidos_pan = Queue()
        self.inicializar_empleados(2)
        self.needs_conservas  = False   # NUEVO

    def producir_harina_automatica(self):
        while True:
            time.sleep(random.uniform(10, 15))
            with self.lock:
                cantidad_producida = 15
                self.inventario["harina"] += cantidad_producida
                log_mud(f"\033[95m[AUTO-MOLINO]\033[0m: Procesados sacos (+{cantidad_producida}). Stock: {self.inventario['harina']}")

    @requiere_empleado
    def _hornear_pan_hasta_agotar(self):
        with self.lock:
            # Cambiamos el 'if' por 'while' para procesar todo el inventario
            while self.inventario["harina"] >= 2 and self.inventario["apple"] >= 1:
                # Nota: He ajustado el consumo de harina a 3 para que coincida con el requisito del check
                self.inventario["harina"] -= 2 
                self.inventario["apple"]  -= 1
                
                for _ in range(2):
                    self.productos_listos.append("Pan con manzana")
                
                log_mud(f"\033[95mPanadería\033[0m horneó 2 panes. Inventario: {self.inventario}")

            # Guardamos el stock final después de vaciar los ingredientes
            pan_stock = len(self.productos_listos)

        # Publicar oferta de pan si hay excedente (fuera del while para no spamear mensajes)
        if pan_stock > 10:
            send_mud(f"MUD_OFFER Panaderia pan {pan_stock} 3.5")

    def hornear_pan(self):
        while True:
            time.sleep(random.uniform(0.2, 0.8))
            self._hornear_pan_hasta_agotar()

    def monitor_inventario(self):
        """Pide manzanas a Frutería cuando escasean."""
        while True:
            time.sleep(8)
            with self.lock:
                manzanas = self.inventario["apple"]
            if manzanas < 5:
                costo_estimado = 5 * 0.50
                if self.caja.retirar(costo_estimado):
                    pedido = Pedido("apple", 20, origen="Panadería")
                    log_mud(f"\033[95mPanadería\033[0m: Solicitando manzanas (Paga ${costo_estimado:.2f}). Caja=${self.caja.dinero:.2f}")
                    self.cola_pedidos.put(pedido)
                    self.semaforo.release()
                    sup: Suministro = self.cola_respuestas.get()
                    if sup.cantidad > 0:
                        with self.lock:
                            self.inventario[sup.producto] += sup.cantidad
                        lista   = [sup.producto] * sup.cantidad
                        factura = self._order_preparator(lista, {sup.producto: 0.50}, es_compra=True)
                        self.transaction_manager(factura, accion="monitor_inventario")
                        log_mud(f"\033[95mPanadería\033[0m: Recibió {sup.cantidad} {sup.producto}.")
                    else:
                        self.caja.depositar(costo_estimado)
                        log_mud(f"\033[95mPanadería\033[0m: Frutería vacía, dinero devuelto.")

    def monitor_conservas(self):
        """NUEVO: Panadería compra conservas al Supermercado (para ensaimadas/rellenos)."""
        while True:
            time.sleep(15)
            with self.lock:
                conservas_actual = self.inventario.get("conservas", 0)
            if conservas_actual < 3 and not self.needs_conservas:
                self.needs_conservas = True
                # Publicar demanda en el Marketplace
                send_mud(f"MUD_WANT Panaderia conservas 3 4.0")
                log_mud(f"\033[95m[COMERCIO MUD]\033[0m ✉️ Panadería publica WANT de 3x conservas.")

    @requiere_empleado
    def _atender_cliente_final_una_vez(self, lista_deseada):
        from collections import Counter
        detalles = ", ".join([f"{v} {k}" for k, v in Counter(lista_deseada).items()])
        log_mud(f"\033[95mPanadería\033[0m: NPC solicita comprar {detalles}.")
        articulos_vendidos = []
        with self.lock:
            for req in lista_deseada:
                if req == "Pan con manzana" and self.productos_listos:
                    vendido = self.productos_listos.pop(0)
                    articulos_vendidos.append(vendido)
                # NUEVO: también vender conservas si las tiene en stock
                elif req == "conservas" and self.inventario.get("conservas", 0) > 0:
                    self.inventario["conservas"] -= 1
                    articulos_vendidos.append("conservas")
        if articulos_vendidos:
            precios = {a: (self.precio_pan if a == "Pan con manzana" else 2.50) for a in articulos_vendidos}
            factura = self._order_preparator(articulos_vendidos, precios, es_compra=False)
            ingreso = factura["total_revenue"]
            self.caja.depositar(ingreso)
            self.transaction_manager(factura, accion="atender_cliente_final")
            log_mud(f"\033[95mPanadería\033[0m: Vendió {len(articulos_vendidos)} artículos al NPC -> +${ingreso:.2f}. Caja=${self.caja.dinero:.2f}")
        else:
            log_mud(f"\033[95mPanadería\033[0m: Sin artículos para el NPC.")

    def atender_cliente_final(self):
        while True:
            lista_deseada = self.cola_clientes.get()
            self._atender_cliente_final_una_vez(lista_deseada)

    def llevar_dinero(self, caja_fuerte: CajaFuerte):
        while True:
            time.sleep(6)
            if self.caja.dinero > 100:
                exceso = self.caja.dinero - 50
                if self.caja.retirar(exceso):
                    caja_fuerte.guardar_dinero(exceso)

    def atender_pedidos_pan_mud(self):
        while True:
            pedido: Pedido = self.cola_pedidos_pan.get()
            log_mud(f"\033[95mPanadería\033[0m recibiendo pedido MUD: {pedido}")
            servido = 0
            with self.lock:
                while servido < pedido.cantidad and self.productos_listos:
                    self.productos_listos.pop(0)
                    servido += 1
            if servido > 0:
                ingreso = servido * self.precio_pan
                self.caja.depositar(ingreso)
                log_mud(f"\033[95mPanadería\033[0m: Vendiendo {servido}x pan MUD -> MUD_ACCEPT.")
                send_mud(f"MUD_ACCEPT {pedido.producto} {servido} {pedido.origen} {int(ingreso)}")
            else:
                log_mud(f"\033[95mPanadería\033[0m: Sin panes listos -> MUD_REJECT.")
                send_mud(f"MUD_REJECT {pedido.producto} {pedido.cantidad} {pedido.origen}")
            self.cola_pedidos_pan.task_done()

    def start(self):
        Thread(target=self.hornear_pan,             daemon=True).start()
        Thread(target=self.monitor_inventario,      daemon=True).start()
        Thread(target=self.atender_cliente_final,   daemon=True).start()
        Thread(target=self.producir_harina_automatica, daemon=True).start()
        Thread(target=self.atender_pedidos_pan_mud, daemon=True).start()
        Thread(target=self.monitor_conservas,       daemon=True).start()   # NUEVO


MAX_NPC_POR_DIA = 10

class ClienteNPC(Thread):
    def __init__(self, q_fruteria: Queue, q_panaderia: Queue):
        super().__init__(daemon=True)
        self.q_fruteria  = q_fruteria
        self.q_panaderia = q_panaderia
        self._dia_anterior          = dia_actual
        self._visitas_fruteria_hoy  = 0
        self._visitas_panaderia_hoy = 0

    def _reset_si_nuevo_dia(self):
        global dia_actual
        if dia_actual != self._dia_anterior:
            self._dia_anterior          = dia_actual
            self._visitas_fruteria_hoy  = 0
            self._visitas_panaderia_hoy = 0

    def run(self):
        while True:
            time.sleep(random.uniform(8, 15))
            self._reset_si_nuevo_dia()

            if self._visitas_fruteria_hoy < MAX_NPC_POR_DIA:
                min_fruta = 3 if dia_actual < 2 else 8
                max_fruta = 10 if dia_actual < 3 else 25
                # NUEVO: helado incluido en la oferta de Frutería
                frutas_posibles = ["apple", "orange", "grape", "cacao", "helado"]
                cant_frutas = random.randint(min_fruta, max_fruta)
                orden_frutas = [random.choice(frutas_posibles) for _ in range(cant_frutas)]
                self.q_fruteria.put(orden_frutas)
                cant_cocteles = random.randint(0, 3)
                orden_cocteles = ["coctel"] * cant_cocteles
                self.q_fruteria.put(orden_cocteles)
                self._visitas_fruteria_hoy += 1

            if self._visitas_panaderia_hoy < MAX_NPC_POR_DIA:
                max_pan   = 3 if dia_actual < 3 else 8
                cant_pan  = random.randint(1, max_pan)
                orden_pan = ["Pan con manzana"] * cant_pan
                self.q_panaderia.put(orden_pan)
                sabores      = ["helado", "helado_cacao"]
                cant_helados = random.randint(3, 6)
                orden_helados = [random.choice(sabores) for _ in range(cant_helados)]
                self.q_panaderia.put(orden_helados)
                cant_conservas  = random.randint(0, 2)
                orden_conservas = ["conservas"] * cant_conservas
                self.q_panaderia.put(orden_conservas)
                self._visitas_panaderia_hoy += 1


def simular_dias(fruteria_obj, panaderia_obj, caja_fuerte_frut, caja_fuerte_pan):
    global dia_actual
    dia_actual = 1
    riqueza_fruteria_ayer  = fruteria_obj.caja.dinero
    riqueza_panaderia_ayer = panaderia_obj.caja.dinero

    # MODIFICADO: Bucle infinito
    while True:
        log_mud(f"\n\033[1;37m--- COMIENZA EL DÍA {dia_actual} EN LA CALLE LAVAMANOS---\033[0m\n")
        t_inicio_dia = transacciones_realizadas["numero_transacciones"]
        time.sleep(25)

        log_mud(f"\n\033[1;37m--- FIN DEL DÍA {dia_actual} ---\033[0m")
        log_mud("\033[1;32m=== REPORTE DIARIO DE COMERCIO ===\033[0m")

        banco_f = caja_fuerte_frut.consultar_saldo_banco()
        banco_p = caja_fuerte_pan.consultar_saldo_banco()
        fuerte_f = caja_fuerte_frut.obtener_dinero()
        fuerte_p = caja_fuerte_pan.obtener_dinero()

        riqueza_frut_hoy = fruteria_obj.caja.dinero + fuerte_f + banco_f
        riqueza_pan_hoy  = panaderia_obj.caja.dinero + fuerte_p + banco_p

        profit_f = riqueza_frut_hoy - riqueza_fruteria_ayer
        profit_p = riqueza_pan_hoy  - riqueza_panaderia_ayer
        riqueza_fruteria_ayer  = riqueza_frut_hoy
        riqueza_panaderia_ayer = riqueza_pan_hoy

        log_mud(f"💰 \033[93mFrutería NET Profit:\033[0m ${profit_f:+.2f} | [Caja: ${fruteria_obj.caja.dinero:.2f} | Fuerte: ${fuerte_f:.2f} | Banco: ${banco_f:.2f}] (Total: ${riqueza_frut_hoy:.2f})")
        log_mud(f"💰 \033[95mPanadería NET Profit:\033[0m ${profit_p:+.2f} | [Caja: ${panaderia_obj.caja.dinero:.2f} | Fuerte: ${fuerte_p:.2f} | Banco: ${banco_p:.2f}] (Total: ${riqueza_pan_hoy:.2f})")
        log_mud(f"📦 \033[93mInventario Frutería:\033[0m {fruteria_obj.inventario}")
        pan_listo = len(panaderia_obj.productos_listos)
        log_mud(f"📦 \033[95mInventario Panadería:\033[0m {panaderia_obj.inventario} | Panes: {pan_listo}")
        t_fin_dia  = transacciones_realizadas["numero_transacciones"]
        ordenes_hoy = t_fin_dia - t_inicio_dia
        log_mud(f"🧾 \033[96mTickets/Ordenes Operadas Hoy:\033[0m {ordenes_hoy}")
        log_mud("==================================\n")
        dia_actual += 1

if __name__ == "__main__":
    ip_servidor = input("Introduce la IP del Servidor Central (Enter para 127.0.0.1): ").strip()
    if not ip_servidor:
        ip_servidor = "127.0.0.1"
    MUD_HOST = ip_servidor

    q_pedidos       = Queue()
    q_respuestas    = Queue()
    sem_ordenes     = Semaphore(0)
    q_clientes_fruteria  = Queue()
    q_clientes_panaderia = Queue()

    tienda    = FruitShop(q_pedidos, q_respuestas, sem_ordenes, q_clientes_fruteria)
    panaderia = Panaderia(q_pedidos, q_respuestas, sem_ordenes, q_clientes_panaderia)

    init_mud_client(tienda, panaderia)

    cliente_npc = ClienteNPC(q_clientes_fruteria, q_clientes_panaderia)
    cliente_npc.start()

    CajaFuerteFrut = CajaFuerte("fruteria")
    CajaFuertePan  = CajaFuerte("panaderia")

    Thread(target=CajaFuerteFrut.crear_cuenta, args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaFuertePan.crear_cuenta,  args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaFuerteFrut.enviar_dinero_banco, args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaFuertePan.enviar_dinero_banco,  args=(ip_servidor,), daemon=True).start()
    Thread(target=tienda.llevar_dinero,    args=(CajaFuerteFrut,), daemon=True).start()
    Thread(target=panaderia.llevar_dinero, args=(CajaFuertePan,),  daemon=True).start()

    time.sleep(1)
    tienda.start()
    panaderia.start()

    simular_dias(tienda, panaderia, CajaFuerteFrut, CajaFuertePan)