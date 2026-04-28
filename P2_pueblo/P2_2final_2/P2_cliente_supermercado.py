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
DIA_ACTUAL = 1

q_pedidos_mud_supermercado = None
q_pedidos_mud_heladeria    = None   # NUEVO: cola para pedidos externos de helado

def init_mud_client(q_resp_super_mud=None, q_resp_heladeria_mud=None,
                    q_pedidos_mud_supermercado_ref=None,
                    q_pedidos_mud_heladeria_ref=None):
    global mud_socket, q_pedidos_mud_supermercado, q_pedidos_mud_heladeria
    q_pedidos_mud_supermercado = q_pedidos_mud_supermercado_ref
    q_pedidos_mud_heladeria    = q_pedidos_mud_heladeria_ref
    mud_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        mud_socket.connect((MUD_HOST, MUD_PORT))
        mud_socket.sendall(b"IDENTIFY SUPERMERCADO_HELADERIA\n")
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
                            # Gestionados por el Marketplace en el servidor
                            pass
                        elif "MUD_ACCEPT" in msg:
                            partes = msg.split("MUD_ACCEPT", 1)[1].strip().split()
                            if len(partes) >= 4:
                                producto, cantidad_str, origen, total_str = partes[0], partes[1], partes[2], partes[3]
                                try:
                                    cantidad = int(cantidad_str)
                                    total    = float(total_str)
                                except ValueError:
                                    cantidad = 0
                                    total    = 0.0
                                if cantidad > 0:
                                    print(f"\033[96m[COMERCIO MUD]\033[0m 📦 Aprobada compra ({producto}x{cantidad}) para {origen} total=${total}!")
                                    # NUEVO: pasar total_real al Suministro para pago justo
                                    sup = Suministro(producto, cantidad, "MUD_Aprobado", total_real=total)
                                    if origen == "Supermercado" and q_resp_super_mud:
                                        q_resp_super_mud.put(sup)
                                    elif origen == "Heladeria" and q_resp_heladeria_mud:
                                        q_resp_heladeria_mud.put(sup)
                                else:
                                    print(f"\033[96m[COMERCIO MUD]\033[0m ❌ Solicitud vacía para {producto}.")
                            else:
                                print(f"\033[96m[COMERCIO MUD]\033[0m ❌ MUD_ACCEPT mal formado: {msg}")

                        elif "MUD_REJECT" in msg:
                            partes = msg.split("MUD_REJECT", 1)[1].strip().split()
                            if len(partes) >= 3:
                                producto, cantidad_str, origen = partes[0], partes[1], partes[2]
                                print(f"\033[96m[COMERCIO MUD]\033[0m ❌ Rechazado lote {producto} para {origen}.")
                                sup = Suministro(producto, 0, "MUD_Rechazado")
                                if origen == "Supermercado" and q_resp_super_mud:
                                    q_resp_super_mud.put(sup)
                                elif origen == "Heladeria" and q_resp_heladeria_mud:
                                    q_resp_heladeria_mud.put(sup)

                        elif "MUD_BUY" in msg:
                            partes = msg.split("MUD_BUY", 1)[1].strip().split()
                            if len(partes) >= 3:
                                producto, cantidad_str, origen = partes[0], partes[1], partes[2]
                                try:
                                    cantidad = int(cantidad_str)
                                except Exception:
                                    cantidad = 0
                                # Supermercado atiende bebidas y conservas
                                if producto in ("bebidas", "conservas"):
                                    if q_pedidos_mud_supermercado:
                                        q_pedidos_mud_supermercado.put(Pedido(producto, cantidad, origen))
                                # Heladería atiende pedidos externos de helado (ej: Frutería)
                                elif producto == "helado":
                                    if q_pedidos_mud_heladeria:
                                        q_pedidos_mud_heladeria.put(Pedido(producto, cantidad, origen))
                                else:
                                    print(f"\033[96m[COMERCIO MUD]\033[0m 📜 MUD_BUY no gestionado aquí: {msg}")
                            else:
                                print(f"\033[96m[COMERCIO MUD]\033[0m ❌ MUD_BUY mal formado: {msg}")
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
    def __init__(self, producto: str, cantidad: int, proveedor: str, total_real: float = None):
        self.producto   = producto
        self.cantidad   = cantidad
        self.proveedor  = proveedor
        self.total_real = total_real   # NUEVO: total exacto que cobró el vendedor vía MUD
    def __str__(self):
        return f"Suministro(prod='{self.producto}', qty={self.cantidad}, de='{self.proveedor}', total={self.total_real})"

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

transacciones_realizadas = {"numero_transacciones": 0, "id_transacciones": [], "ordenes": {}}
registro_empleados = {}

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

class Supermercado(Empleador):
    def __init__(self, q_entrada: Queue, q_salida: Queue, sem: Semaphore,
                 q_pedir_helados: Queue, q_resp_helados: Queue, sem_pedir_helados: Semaphore,
                 cola_clientes: Queue, q_resp_mud: Queue, q_pedidos_mud: Queue):
        self.q_pedidos_recibidos   = q_entrada
        self.q_respuestas_enviadas = q_salida
        self.sem_ordenes           = sem
        self.q_pedir_helados       = q_pedir_helados
        self.q_resp_helados        = q_resp_helados
        self.sem_pedir_helados     = sem_pedir_helados
        self.cola_clientes         = cola_clientes
        self.q_resp_mud            = q_resp_mud
        self.q_pedidos_mud         = q_pedidos_mud

        self.caja      = Caja(150.0)
        self.lock      = Lock()
        # OPTIMIZACIÓN: conservas arranca con stock inicial (no 0)
        self.inventario = {"snacks": 20, "bebidas": 20, "helado": 5, "conservas": 5}

        self.precio_leche           = 2.20
        self.precio_helado_reventa  = 5.20
        self.precio_frutas          = 3.50
        self.precio_pan             = 5.50
        self.precio_conservas       = 4.50
        self.precio_snacks          = 3.50
        self.precio_bebidas         = 2.50
        self.compras_frutas         = {}
        self.compras_pan            = 0
        self.inicializar_empleados(3)

    def _precio_dinamico(self, producto: str, base: float) -> float:
        """Precio sube un 20% si stock < 3 (escasez), baja 10% si stock > 20 (excedente)."""
        stock = self.inventario.get(producto, 0)
        if stock < 3:
            return round(base * 1.20, 2)
        if stock > 20:
            return round(base * 0.90, 2)
        return base

    def producir_productos(self):
        while True:
            time.sleep(12)
            with self.lock:
                # Priorizar frutas más compradas para hacer conservas
                frutas_disponibles = [(f, self.inventario.get(f, 0))
                                      for f in ["apple", "banana", "orange", "grape", "cacao"]
                                      if self.inventario.get(f, 0) > 0]
                # Ordenar: primero las frutas con más stock (evita acumulación)
                frutas_disponibles.sort(key=lambda x: x[1], reverse=True)
                frutas_usadas = []
                for nombre_f, _ in frutas_disponibles:
                    if len(frutas_usadas) >= 2:
                        break
                    self.inventario[nombre_f] -= 1
                    frutas_usadas.append(nombre_f)
                if len(frutas_usadas) == 2:
                    self.inventario["conservas"] += 1
                    log_mud(f"\033[96mSupermercado\033[0m: Produjo 1 conserva usando {frutas_usadas[0]} y {frutas_usadas[1]}.")

            # Producir snacks y bebidas solo si stock bajo (anti-sobreproducción)
            with self.lock:
                s_stock = self.inventario.get("snacks", 0)
                b_stock = self.inventario.get("bebidas", 0)
                cant_s = random.randint(3, 8) if s_stock < 25 else 0
                cant_b = random.randint(3, 8) if b_stock < 25 else 0
                self.inventario["snacks"]  += cant_s
                self.inventario["bebidas"] += cant_b
            if cant_s or cant_b:
                log_mud(f"\033[96mSupermercado\033[0m: Repuso {cant_s} snacks y {cant_b} bebidas.")

            # Pedir pan solo si stock bajo
            with self.lock:
                pan_qty = self.inventario.get("pan", 0)
            if pan_qty < 5:
                send_mud(f"MUD_BUY Supermercado pan 5")
                log_mud(f"\033[96m[COMERCIO MUD]\033[0m ✉️ Súper pide 5x pan (stock={pan_qty}).")

            # Publicar oferta de conservas si hay excedente → Marketplace
            with self.lock:
                cons_stock = self.inventario.get("conservas", 0)
            if cons_stock > 10:
                send_mud(f"MUD_OFFER Supermercado conservas {cons_stock} 3.5")

    def monitor_inventario(self):
        """Pide helados a Heladería solo cuando el stock es bajo."""
        while True:
            time.sleep(12)
            with self.lock:
                helado_actual = self.inventario.get("helado", 0)

            # OPTIMIZACIÓN: solo pedir si stock < 3
            if helado_actual >= 3:
                continue

            cantidad = random.randint(2, 5)
            costo_estimado = cantidad * 3.20
            if self.caja.retirar(costo_estimado):
                pedido = Pedido("helado", cantidad, origen="Supermercado")
                self.q_pedir_helados.put(pedido)
                self.sem_pedir_helados.release()
                sup: Suministro = self.q_resp_helados.get()
                if sup.cantidad > 0:
                    with self.lock:
                        self.inventario["helado"] = self.inventario.get("helado", 0) + sup.cantidad
                    lista   = ["helado"] * sup.cantidad
                    factura = self._order_preparator(lista, {"helado": 3.20}, es_compra=True)
                    self.transaction_manager(factura, accion="monitor_inventario")
                    log_mud(f"\033[96mSupermercado\033[0m: Recibió {sup.cantidad} helados para reventa.")
                else:
                    self.caja.depositar(costo_estimado)

    def monitor_inventario_mud(self):
        while True:
            sup = self.q_resp_mud.get()
            if sup.cantidad > 0:
                costo = sup.total_real if sup.total_real is not None else sup.cantidad * 1.50
                precio_unit = costo / sup.cantidad if sup.cantidad else 0
                if self.caja.retirar(costo):
                    with self.lock:
                        if sup.producto not in self.inventario:
                            self.inventario[sup.producto] = 0
                        self.inventario[sup.producto] += sup.cantidad
                        if sup.producto in ["apple", "banana", "orange", "grape", "cacao"]:
                            self.compras_frutas[sup.producto] = self.compras_frutas.get(sup.producto, 0) + sup.cantidad
                        elif sup.producto == "pan":
                            self.compras_pan += sup.cantidad
                    lista   = [sup.producto] * sup.cantidad
                    factura = self._order_preparator(lista, {sup.producto: precio_unit}, es_compra=True)
                    self.transaction_manager(factura, accion="monitor_inventario_mud")
                    log_mud(f"\033[96mSupermercado\033[0m: Recibió {sup.cantidad}x{sup.producto} vía MUD.")
                else:
                    log_mud(f"\033[96mSupermercado\033[0m: Sin fondos para pagar envío MUD de {sup.producto}.")

    @requiere_empleado
    def _atender_cliente_final_una_vez(self, lista_deseada):
        from collections import Counter
        detalles = ", ".join([f"{v} {k}" for k, v in Counter(lista_deseada).items()])
        log_mud(f"\033[96mSupermercado\033[0m: NPC solicita comprar {detalles}.")
        articulos_vendidos = []
        with self.lock:
            for req in lista_deseada:
                if self.inventario.get(req, 0) > 0:
                    self.inventario[req] -= 1
                    articulos_vendidos.append(req)
        if articulos_vendidos:
            # OPTIMIZACIÓN: precios dinámicos según stock
            precios = {
                "leche":      self._precio_dinamico("leche",      self.precio_leche),
                "helado":     self._precio_dinamico("helado",     self.precio_helado_reventa),
                "helado_cacao": self._precio_dinamico("helado_cacao", self.precio_helado_reventa + 2.0),
                "pan":        self._precio_dinamico("pan",        self.precio_pan),
                "conservas":  self._precio_dinamico("conservas",  self.precio_conservas),
                "snacks":     self._precio_dinamico("snacks",     self.precio_snacks),
                "bebidas":    self._precio_dinamico("bebidas",    self.precio_bebidas),
            }
            for f in ["apple", "banana", "orange", "grape", "cacao"]:
                precios[f] = self._precio_dinamico(f, self.precio_frutas)
            factura = self._order_preparator(articulos_vendidos, precios, es_compra=False)
            ingreso = factura["total_revenue"]
            self.caja.depositar(ingreso)
            self.transaction_manager(factura, accion="atender_cliente_final")
            log_mud(f"\033[96mSupermercado\033[0m: Vendió al NPC -> +${ingreso:.2f}. Caja=${self.caja.dinero:.2f}")
        else:
            log_mud(f"\033[96mSupermercado\033[0m: No pudo satisfacer ningún ítem del ticket.")

    def atender_cliente_final(self):
        while True:
            lista_deseada = self.cola_clientes.get()
            self._atender_cliente_final_una_vez(lista_deseada)

    def llevar_dinero(self, caja_fuerte: CajaFuerte):
        while True:
            time.sleep(5)
            if self.caja.dinero > 200:
                exceso = self.caja.dinero - 150
                if self.caja.retirar(exceso):
                    caja_fuerte.guardar_dinero(exceso)

    def atender_pedidos_mud(self):
        """Atiende MUD_BUY de bebidas y conservas de otras tiendas."""
        while True:
            pedido: Pedido = self.q_pedidos_mud.get()
            with self.lock:
                disp   = self.inventario.get(pedido.producto, 0)
                servido = min(disp, pedido.cantidad)
                self.inventario[pedido.producto] -= servido
            if servido > 0:
                costo = self.precio_conservas if pedido.producto == "conservas" else self.precio_bebidas
                total = servido * costo
                self.caja.depositar(total)
                lista   = [pedido.producto] * servido
                factura = self._order_preparator(lista, {pedido.producto: costo}, es_compra=False)
                self.transaction_manager(factura, accion="atender_pedidos_mud")
                log_mud(f"\033[96mSupermercado\033[0m: Vendió {servido}x{pedido.producto} a {pedido.origen} vía MUD. (+${total:.2f})")
                send_mud(f"MUD_ACCEPT {pedido.producto} {servido} {pedido.origen} {int(total)}")
            else:
                send_mud(f"MUD_REJECT {pedido.producto} {pedido.cantidad} {pedido.origen}")
            self.q_pedidos_mud.task_done()

    def start(self):
        Thread(target=self.producir_productos,    daemon=True).start()
        Thread(target=self.monitor_inventario,    daemon=True).start()
        Thread(target=self.monitor_inventario_mud, daemon=True).start()
        Thread(target=self.atender_pedidos_mud,   daemon=True).start()
        Thread(target=self.atender_cliente_final, daemon=True).start()


class Heladeria(Empleador):
    def __init__(self, q_pedida_leche: Queue, q_resp_leche: Queue, sem_leche: Semaphore,
                 q_pedidos_recibidos: Queue, q_resp_enviadas: Queue, sem_ordenes_helado: Semaphore,
                 cola_clientes: Queue, q_resp_mud: Queue,
                 q_pedidos_mud_helado: Queue = None):   # NUEVO: cola de pedidos externos de helado
        self.q_pedida_leche       = q_pedida_leche
        self.q_resp_leche         = q_resp_leche
        self.sem_leche            = sem_leche
        self.q_pedidos_recibidos  = q_pedidos_recibidos
        self.q_resp_enviadas      = q_resp_enviadas
        self.sem_ordenes_helado   = sem_ordenes_helado
        self.cola_clientes        = cola_clientes
        self.q_resp_mud           = q_resp_mud
        self.q_pedidos_mud_helado = q_pedidos_mud_helado   # NUEVO

        self.caja      = Caja(80.0)
        self.lock      = Lock()
        # OPTIMIZACIÓN: arranca con stock inicial de heladopuedes hacer q la heladeria solo intente comprara cacao cuando tenga <5 de cacao y <5 helados de cacao

        self.inventario = {"leche": 20, "helado": random.randint(5, 8), "cacao": 5, "helado_cacao": 0, "pan": 0}

        self.precio_helado_mayorista = 4.20
        self.precio_helado_mostrador = 4.50
        self.precio_helado_externo   = 4.40   # NUEVO: venta MUD a otras tiendas
        self.leche_por_helado        = 2
        self.compras_frutas          = {}
        self.inicializar_empleados(3)
        self.esperando_cacao = False
        self.esperando_pan   = False
        self.ultimo_cacao_recibido = 0.0   # NUEVO: timestamp anti-spam

    def monitor_inventario_mud(self):
        while True:
            sup = self.q_resp_mud.get()
            if sup.cantidad > 0:
                if sup.total_real is not None:
                    costo = sup.total_real
                else:
                    precios_compra = {"cacao": 1.0, "pan": 6.0}
                    costo = sup.cantidad * precios_compra.get(sup.producto, 1.50)
                precio_unit = costo / sup.cantidad if sup.cantidad else 0
                if self.caja.retirar(costo):
                    with self.lock:
                        if sup.producto not in self.inventario:
                            self.inventario[sup.producto] = 0
                        self.inventario[sup.producto] += sup.cantidad
                        if sup.producto in ["apple", "banana", "orange", "grape", "cacao"]:
                            self.compras_frutas[sup.producto] = self.compras_frutas.get(sup.producto, 0) + sup.cantidad
                            if sup.producto == "cacao":
                                self.ultimo_cacao_recibido = time.time()
                    lista   = [sup.producto] * sup.cantidad
                    factura = self._order_preparator(lista, {sup.producto: precio_unit}, es_compra=True)
                    self.transaction_manager(factura, accion="monitor_inventario_mud")
                    log_mud(f"\033[94mHeladería\033[0m: Recibió {sup.cantidad}x{sup.producto} foráneo.")
                else:
                    log_mud(f"\033[94mHeladería\033[0m: Sin fondos para el cargamento de {sup.producto}.")
                self.esperando_cacao = False
                self.esperando_pan   = False
            elif sup.proveedor == "MUD_Rechazado":
                self.esperando_cacao = False
                self.esperando_pan   = False
                log_mud(f"\033[94mHeladería\033[0m: MUD rechazó compra.")

    @requiere_empleado
    def _producir_helados_una_vez(self):
        with self.lock:
            cacao  = self.inventario.get("cacao", 0)
            leche  = self.inventario.get("leche", 0)
            helados_producidos = 0

            while leche >= self.leche_por_helado and cacao > 0:
                self.inventario["leche"] -= self.leche_por_helado
                self.inventario["cacao"] -= 1
                self.inventario["helado_cacao"] = self.inventario.get("helado_cacao", 0) + 1
                helados_producidos += 1
                leche -= self.leche_por_helado
                cacao -= 1

            # Cap dinámico: día 1 demanda baja (NPC no compra helados), día 2+ sube
            cap_helado = 6 if DIA_ACTUAL <= 1 else 12
            while leche >= self.leche_por_helado and self.inventario.get("helado", 0) < cap_helado:
                self.inventario["leche"] -= self.leche_por_helado
                self.inventario["helado"] = self.inventario.get("helado", 0) + 1
                helados_producidos += 1
                leche -= self.leche_por_helado

            if helados_producidos > 0:
                log_mud(f"\033[94mHeladería\033[0m: Fabricó {helados_producidos} helados.")

            pan = self.inventario.get("pan", 0)
            if pan > 0 and self.inventario.get("conos", 0) < 20:
                conos = pan * 10
                self.inventario["pan"] = 0
                self.inventario["conos"] = self.inventario.get("conos", 0) + conos
                log_mud(f"\033[94mHeladería\033[0m: Fabricó {conos} conos usando {pan} panes.")

        # Cacao solo si bajo (<5) y helados de cacao bajo (<5) y con cooldown 30s para no spamear a Frutería
        with self.lock:
            cacao_stock  = self.inventario.get("cacao", 0)
            helado_cacao_stock = self.inventario.get("helado_cacao", 0)
            helado_stock = self.inventario.get("helado", 0) + self.inventario.get("helado_cacao", 0)

        cooldown_ok = (time.time() - self.ultimo_cacao_recibido) > 30
        if cacao_stock < 5 and helado_cacao_stock < 5 and not self.esperando_cacao and cooldown_ok:
            self.esperando_cacao = True
            send_mud(f"MUD_BUY Heladeria cacao 8")
            log_mud(f"\033[94m[COMERCIO MUD]\033[0m ✉️ Stock cacao crítico ({cacao_stock}), helado_cacao ({helado_cacao_stock}): pidiendo 8x")

        # Publicar oferta de helado si hay excedente → Marketplace
        if helado_stock > 8:
            send_mud(f"MUD_OFFER Heladeria helado {helado_stock} 3.40")

    def producir_helados(self):
        while True:
            time.sleep(5)
            self._producir_helados_una_vez()

    def producir_leche(self):
        """Produce leche periódicamente. Solo si el stock no está saturado."""
        while True:
            time.sleep(6)
            with self.lock:
                leche_actual = self.inventario.get("leche", 0)
            # OPTIMIZACIÓN: no acumular leche excesiva
            if leche_actual < 20:
                with self.lock:
                    self.inventario["leche"] += 10
                log_mud(f"\033[94mHeladería\033[0m: Produjo 10L de leche. Total: {self.inventario['leche']}L")

    def monitor_pan(self):
        """NUEVO: Heladería compra pan a Panadería (para gofres/conos). Via Marketplace."""
        while True:
            time.sleep(20)
            with self.lock:
                pan_actual = self.inventario.get("pan", 0)
            if pan_actual < 2 and not self.esperando_pan:
                self.esperando_pan = True
                # Publicar demanda en el Marketplace; el servidor auto-genera MUD_BUY si hay oferta
                send_mud(f"MUD_WANT Heladeria pan 3 6.5")
                log_mud(f"\033[94m[COMERCIO MUD]\033[0m ✉️ Heladería publica WANT de 3x pan (gofres).")

    def atender_pedidos_helado_mud(self):
        """NUEVO: Heladería vende helado a tiendas externas (ej: Frutería) vía MUD."""
        while True:
            pedido: Pedido = self.q_pedidos_mud_helado.get()
            log_mud(f"\033[94mHeladería\033[0m: Pedido externo MUD de helado: {pedido}")
            with self.lock:
                disp    = self.inventario.get("helado", 0)
                servido = min(disp, pedido.cantidad)
                self.inventario["helado"] -= servido
            if servido > 0:
                precio = self.precio_helado_externo
                total  = servido * precio
                self.caja.depositar(total)
                lista   = ["helado"] * servido
                factura = self._order_preparator(lista, {"helado": precio}, es_compra=False)
                self.transaction_manager(factura, accion="atender_pedidos_helado_mud")
                log_mud(f"\033[94mHeladería\033[0m: Vendió {servido}x helado a {pedido.origen} vía MUD. +${total:.2f}")
                send_mud(f"MUD_ACCEPT helado {servido} {pedido.origen} {int(total)}")
            else:
                send_mud(f"MUD_REJECT helado {pedido.cantidad} {pedido.origen}")
            self.q_pedidos_mud_helado.task_done()

    @requiere_empleado
    def _atender_supermercado_una_vez(self, pedido: Pedido):
        log_mud(f"\033[94mHeladería\033[0m: Atendiendo mayorista {pedido}")
        served   = 0
        entregas = {}
        with self.lock:
            if pedido.producto == "helado":
                sabores_disponibles = [s for s in self.inventario if s.startswith("helado_") and self.inventario[s] > 0]
                for sabor in sabores_disponibles:
                    if served >= pedido.cantidad:
                        break
                    usar = min(self.inventario[sabor], pedido.cantidad - served)
                    self.inventario[sabor] -= usar
                    entregas[sabor] = usar
                    served += usar
                if served < pedido.cantidad:
                    disp_gen = self.inventario.get("helado", 0)
                    extra    = min(disp_gen, pedido.cantidad - served)
                    self.inventario["helado"] -= extra
                    served += extra
            else:
                disp    = self.inventario.get(pedido.producto, 0)
                served  = min(disp, pedido.cantidad)
                self.inventario[pedido.producto] = disp - served

        if served > 0:
            sup    = Suministro(pedido.producto, served, proveedor="Heladería")
            ingreso = served * self.precio_helado_mayorista
            self.caja.depositar(ingreso)
            lista   = [pedido.producto] * served
            factura = self._order_preparator(lista, {pedido.producto: self.precio_helado_mayorista}, es_compra=False)
            self.transaction_manager(factura, accion="atender_supermercado")
            log_mud(f"\033[94mHeladería\033[0m: Mayorista {served}x{pedido.producto} -> +${ingreso:.2f}.")
            if entregas:
                log_mud(f"\033[94mHeladería\033[0m: Sabores usados: {entregas}")
            self.q_resp_enviadas.put(sup)
        else:
            self.q_resp_enviadas.put(Suministro(pedido.producto, 0, proveedor="Heladería"))

    def atender_supermercado(self):
        while True:
            self.sem_ordenes_helado.acquire()
            pedido: Pedido = self.q_pedidos_recibidos.get()
            self._atender_supermercado_una_vez(pedido)
            self.q_pedidos_recibidos.task_done()

    @requiere_empleado
    def _atender_cliente_final_una_vez(self, lista_deseada):
        from collections import Counter
        detalles = ", ".join([f"{v} {k}" for k, v in Counter(lista_deseada).items()])
        log_mud(f"\033[94mHeladería\033[0m: NPC solicita comprar {detalles}.")
        articulos_vendidos = []
        with self.lock:
            for req in lista_deseada:
                if self.inventario.get(req, 0) > 0:
                    self.inventario[req] -= 1
                    articulos_vendidos.append(req)
        if articulos_vendidos:
            precios = {a: (self.precio_helado_mostrador + 2.0 if a == "helado_cacao" else self.precio_helado_mostrador) for a in articulos_vendidos}
            factura = self._order_preparator(articulos_vendidos, precios, es_compra=False)
            ingreso = factura["total_revenue"]
            self.caja.depositar(ingreso)
            self.transaction_manager(factura, accion="atender_cliente_final")
            log_mud(f"\033[94mHeladería\033[0m: Conitos -> +${ingreso:.2f}. Caja=${self.caja.dinero:.2f}")
        else:
            log_mud(f"\033[94mHeladería\033[0m: Sin helados del sabor pedido.")

    def atender_cliente_final(self):
        while True:
            lista_deseada = self.cola_clientes.get()
            self._atender_cliente_final_una_vez(lista_deseada)

    def llevar_dinero(self, caja_fuerte: CajaFuerte):
        while True:
            time.sleep(6)
            if self.caja.dinero > 100:
                exceso = self.caja.dinero - 60
                if self.caja.retirar(exceso):
                    caja_fuerte.guardar_dinero(exceso)

    def start(self):
        Thread(target=self.producir_leche,             daemon=True).start()
        Thread(target=self.monitor_inventario_mud,     daemon=True).start()
        Thread(target=self.producir_helados,           daemon=True).start()
        Thread(target=self.atender_supermercado,       daemon=True).start()
        Thread(target=self.atender_cliente_final,      daemon=True).start()
        Thread(target=self.monitor_pan,                daemon=True).start()   # NUEVO
        if self.q_pedidos_mud_helado:
            Thread(target=self.atender_pedidos_helado_mud, daemon=True).start()  # NUEVO


MAX_NPC_POR_DIA = 15

class ClienteNPC(Thread):
    def __init__(self, q_super, q_hela):
        super().__init__(daemon=True)
        self.q_super = q_super
        self.q_hela  = q_hela
        self._dia_anterior        = DIA_ACTUAL
        self._visitas_super_hoy   = 0
        self._visitas_hela_hoy    = 0

    def _reset_si_nuevo_dia(self):
        global DIA_ACTUAL
        if DIA_ACTUAL != self._dia_anterior:
            self._dia_anterior      = DIA_ACTUAL
            self._visitas_super_hoy = 0
            self._visitas_hela_hoy  = 0

    def run(self):
        while True:
            time.sleep(random.uniform(3, 10))
            self._reset_si_nuevo_dia()
            items_super = ["snacks", "snacks", "bebidas", "bebidas", "bebidas", "snacks",
                           "helado", "helado_cacao", "pan", "conservas", "apple", "banana"]
            if self._visitas_super_hoy < MAX_NPC_POR_DIA:
                self.q_super.put([random.choice(items_super) for _ in range(random.randint(3, 6))])
                self._visitas_super_hoy += 1
            if DIA_ACTUAL >= 1:
                sabores = ["helado", "helado_cacao"]
                if self._visitas_hela_hoy < MAX_NPC_POR_DIA:
                    self.q_hela.put([random.choice(sabores) for _ in range(random.randint(1, 4))])
                    self._visitas_hela_hoy += 1

def simular_dias(s_obj, h_obj, caja_fuerte_s, caja_fuerte_h):
    dia = 1
    global DIA_ACTUAL
    riqueza_super_ayer = s_obj.caja.dinero
    riqueza_hela_ayer  = h_obj.caja.dinero

    while True: # <<--- BUCLE MODIFICADO A INFINITO
        DIA_ACTUAL = dia
        log_mud(f"\n\033[1;37m--- COMIENZA EL DÍA {dia} EN LA CALLE LAVABOCAS ---\033[0m\n")
        t_inicio = transacciones_realizadas["numero_transacciones"]
        time.sleep(25)

        log_mud(f"\n\033[1;37m--- FIN DEL DÍA {dia} ---\033[0m")
        log_mud("\033[1;32m=== REPORTE DIARIO DE COMERCIO ===\033[0m")

        banco_s = caja_fuerte_s.consultar_saldo_banco()
        banco_h = caja_fuerte_h.consultar_saldo_banco()
        fuerte_s = caja_fuerte_s.obtener_dinero()
        fuerte_h = caja_fuerte_h.obtener_dinero()

        riqueza_s_hoy = s_obj.caja.dinero + fuerte_s + banco_s
        riqueza_h_hoy = h_obj.caja.dinero + fuerte_h + banco_h

        profit_s = riqueza_s_hoy - riqueza_super_ayer
        profit_h = riqueza_h_hoy - riqueza_hela_ayer
        riqueza_super_ayer = riqueza_s_hoy
        riqueza_hela_ayer  = riqueza_h_hoy

        log_mud(f"💰 \033[96mSupermercado NET Profit:\033[0m ${profit_s:+.2f} | [Caja: ${s_obj.caja.dinero:.2f} | Fuerte: ${fuerte_s:.2f} | Banco: ${banco_s:.2f}] (Total: ${riqueza_s_hoy:.2f})")
        log_mud(f"💰 \033[94mHeladería NET Profit:\033[0m ${profit_h:+.2f} | [Caja: ${h_obj.caja.dinero:.2f} | Fuerte: ${fuerte_h:.2f} | Banco: ${banco_h:.2f}] (Total: ${riqueza_h_hoy:.2f})")
        log_mud(f"📦 \033[96mInventario Supermercado:\033[0m {s_obj.inventario}")
        log_mud(f"🍎 \033[96mCompras Supermercado Frutas:\033[0m {s_obj.compras_frutas} | Pan comprado: {s_obj.compras_pan}")
        log_mud(f"📦 \033[94mInventario Heladería:\033[0m {h_obj.inventario}")
        log_mud(f"🍓 \033[94mCompras Heladería Frutas:\033[0m {h_obj.compras_frutas}")
        t_fin = transacciones_realizadas["numero_transacciones"]
        log_mud(f"🧾 \033[92mTickets/Ordenes Operadas Hoy:\033[0m {t_fin - t_inicio}")
        log_mud("==================================\n")
        dia += 1

if __name__ == "__main__":
    ip_servidor = input("Introduce la IP del Servidor Central (Enter para 127.0.0.1): ").strip()
    if not ip_servidor:
        ip_servidor = "127.0.0.1"
    MUD_HOST = ip_servidor

    q_resp_s_mud   = Queue()
    q_resp_h_mud   = Queue()
    q_pedidos_mud_s = Queue()
    q_pedidos_mud_h = Queue()   

    init_mud_client(q_resp_s_mud, q_resp_h_mud, q_pedidos_mud_s, q_pedidos_mud_h)

    q_pedir_leche  = Queue()
    q_resp_leche   = Queue()
    sem_leche      = Semaphore(0)

    q_pedir_helados = Queue()
    q_resp_helados  = Queue()
    sem_helados     = Semaphore(0)

    q_cli_super = Queue()
    q_cli_hela  = Queue()

    supermercado = Supermercado(q_pedir_leche, q_resp_leche, sem_leche,
                                q_pedir_helados, q_resp_helados, sem_helados,
                                q_cli_super, q_resp_s_mud, q_pedidos_mud_s)

    heladeria = Heladeria(q_pedir_leche, q_resp_leche, sem_leche,
                          q_pedir_helados, q_resp_helados, sem_helados,
                          q_cli_hela, q_resp_h_mud,
                          q_pedidos_mud_helado=q_pedidos_mud_h)  

    npc = ClienteNPC(q_cli_super, q_cli_hela)
    npc.start()

    CajaSuper = CajaFuerte("supermercado")
    CajaHelad = CajaFuerte("heladeria")

    Thread(target=CajaSuper.crear_cuenta, args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaHelad.crear_cuenta, args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaSuper.enviar_dinero_banco, args=(ip_servidor,), daemon=True).start()
    Thread(target=CajaHelad.enviar_dinero_banco, args=(ip_servidor,), daemon=True).start()
    Thread(target=supermercado.llevar_dinero, args=(CajaSuper,), daemon=True).start()
    Thread(target=heladeria.llevar_dinero,    args=(CajaHelad,), daemon=True).start()

    time.sleep(1)
    supermercado.start()
    heladeria.start()

    simular_dias(supermercado, heladeria, CajaSuper, CajaHelad)