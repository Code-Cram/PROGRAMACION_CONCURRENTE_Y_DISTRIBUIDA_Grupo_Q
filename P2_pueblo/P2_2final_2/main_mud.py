import time
import subprocess
import os
import sys
import socket
import json
import threading

# IMPORTAMOS LA NUEVA LÓGICA DEL SERVIDOR MUD
from mudserver import MudServer

class Banco:
    def __init__(self):
        self.__cuentas = {}

    def escuchar(self):
        HOST = '0.0.0.0'
        PORT = 45000
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                s.listen()
                print("\033[36m[BANCO CENTRAL]\033[0m Escuchando en el puerto 45000 para sincronización JSON...")
                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024).decode()
                        if data:
                            try:
                                operacion = json.loads(data)
                                if operacion["tipo"] == "transferencia":
                                    if operacion["cuenta"] in self.__cuentas:
                                        self.__cuentas[operacion["cuenta"]] += operacion["cantidad"]
                                        time.sleep(1)
                                        conn.send(f"Recibido OK. Saldo en bóveda: ${self.__cuentas[operacion['cuenta']]}".encode('utf-8'))
                                elif operacion["tipo"] == "crear cuenta":
                                    self.__cuentas[operacion["nombre cuenta"]] = 0
                                    conn.send("Cuenta creada OK.".encode('utf-8'))
                                elif operacion["tipo"] == "retirada":
                                    if self.__cuentas.get(operacion["cuenta"], 0) >= operacion["cantidad"]:
                                        self.__cuentas[operacion["cuenta"]] -= operacion["cantidad"]
                                        conn.send(f"Retirada OK. Quedan: ${self.__cuentas[operacion['cuenta']]}".encode('utf-8'))
                                elif operacion["tipo"] == "consultar":
                                    cantidad = self.__cuentas.get(operacion["cuenta"], 0)
                                    conn.send(str(cantidad).encode('utf-8'))
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"No se pudo iniciar el banco en el puerto 45000: {e}")


class Marketplace:
    def __init__(self):
        self._ofertas  = {}   # producto -> {tienda: (cantidad, precio)}
        self._demandas = {}   # producto -> {tienda: (cantidad, max_precio)}
        self._lock = threading.Lock()

    def procesar_oferta(self, tienda, producto, cantidad, precio):
        with self._lock:
            self._ofertas.setdefault(producto, {})[tienda] = (cantidad, precio)
            print(f"[{time.strftime('%H:%M:%S')}] \033[33m[MARKETPLACE]\033[0m OFERTA: {tienda} → {cantidad}x{producto} @ ${precio}")
            return self._intentar_match(producto, tienda)

    def procesar_demanda(self, tienda, producto, cantidad, max_precio):
        with self._lock:
            self._demandas.setdefault(producto, {})[tienda] = (cantidad, max_precio)
            print(f"[{time.strftime('%H:%M:%S')}] \033[33m[MARKETPLACE]\033[0m DEMANDA: {tienda} → {cantidad}x{producto} max ${max_precio}")
            return self._intentar_match(producto, tienda)

    def _intentar_match(self, producto, tienda_origen):
        vendedores  = self._ofertas.get(producto, {})
        compradores = self._demandas.get(producto, {})
        for vendedor, (cant_v, precio_v) in list(vendedores.items()):
            for comprador, (cant_c, max_p) in list(compradores.items()):
                if comprador == vendedor:
                    continue
                if precio_v <= max_p and cant_v > 0 and cant_c > 0:
                    cantidad_match = min(cant_v, cant_c)
                    print(f"[{time.strftime('%H:%M:%S')}] \033[32m[MARKETPLACE MATCH]\033[0m "
                          f"{comprador} compra {cantidad_match}x{producto} de {vendedor} @ ${precio_v}")
                    del self._demandas[producto][comprador]
                    nueva_cant = cant_v - cantidad_match
                    if nueva_cant <= 0:
                        del self._ofertas[producto][vendedor]
                    else:
                        self._ofertas[producto][vendedor] = (nueva_cant, precio_v)
                    return (vendedor, comprador, producto, cantidad_match, precio_v)
        return None

# -------------------------------------------------------------------
# SERVIDOR TCP RELAY ADAPTADO AL MUDSERVER
# -------------------------------------------------------------------

MUD_PORT = 1234
_marketplace = Marketplace()

# --- MAPA EXTENDIDO ---
mapa_mud = {
    "plaza": {
        "desc": "\033[1;36m[Plaza Central]\033[0m El corazón del comercio.\nSalidas: norte (Frutería), sur (Supermercado), este (Panadería), oeste (Heladería).",
        "salidas": {"norte": "fruteria", "sur": "supermercado", "este": "panaderia", "oeste": "heladeria"},
        "tienda": None,
        "productos": {}
    },
    "fruteria": {
        "desc": "\033[1;33m[Frutería La Huerta]\033[0m Fruta fresca de temporada.\nSalidas: sur (Plaza).",
        "salidas": {"sur": "plaza"},
        "tienda": "FRUTERIA_PANADERIA",
        "productos": {"apple": 1.0, "orange": 1.25, "grape": 1.5, "cacao": 1.25}
    },
    "supermercado": {
        "desc": "\033[1;34m[Supermercado Lavabocas]\033[0m De todo un poco.\nSalidas: norte (Plaza).",
        "salidas": {"norte": "plaza"},
        "tienda": "SUPERMERCADO_HELADERIA",
        "productos": {"snacks": 3.5, "bebidas": 2.5, "conservas": 4.5}
    },
    "panaderia": {
        "desc": "\033[1;35m[Panadería El Trigo]\033[0m Pan caliente y bollos.\nSalidas: oeste (Plaza).",
        "salidas": {"oeste": "plaza"},
        "tienda": "FRUTERIA_PANADERIA", # Misma conexión que frutería
        "productos": {"pan": 3.5}
    },
    "heladeria": {
        "desc": "\033[1;34m[Heladería El Polo]\033[0m Helados artesanales.\nSalidas: este (Plaza).",
        "salidas": {"este": "plaza"},
        "tienda": "SUPERMERCADO_HELADERIA", # Misma conexión que súper
        "productos": {"helado": 4.5, "helado_cacao": 6.5}
    }
}

def run_server():
    mud = MudServer(port=MUD_PORT)
    print(f"Servidor MUD iniciado en puerto {MUD_PORT}.")
    
    nombres_clientes = {}
    tipo_cliente = {}        
    ubicacion_jugadores = {} 
    jugadores_dinero = {} # Cartera de los humanos

    def _broadcast(msg):
        for cid in nombres_clientes:
            mud.send_message(cid, msg)

    while True:
        mud.update()

        for client_id in mud.get_new_players():
            nombres_clientes[client_id] = f"Jugador_{client_id[:4]}"
            tipo_cliente[client_id] = "jugador"
            ubicacion_jugadores[client_id] = "plaza"
            jugadores_dinero[client_id] = 50.0 # Dinero inicial
            mud.send_message(client_id, "\033[1;32mBienvenido. Comandos: mirar, ir, productos, comprar <item> <cantidad>, dinero, decir.\033[0m")

        for client_id in mud.get_disconnected_players():
            nombres_clientes.pop(client_id, None)
            tipo_cliente.pop(client_id, None)
            ubicacion_jugadores.pop(client_id, None)
            jugadores_dinero.pop(client_id, None)

        for client_id, command, params in mud.get_commands():
            if command == "IDENTIFY":
                nombres_clientes[client_id] = params.strip()
                tipo_cliente[client_id] = "tienda"
                continue

            # --- COMANDOS JUGADOR ---
            if tipo_cliente.get(client_id) == "jugador":
                comando_low = command.lower()
                loc = ubicacion_jugadores[client_id]
                
                if comando_low == "dinero":
                    mud.send_message(client_id, f"Tienes $\033[1;32m{jugadores_dinero[client_id]:.2f}\033[0m en tu cartera.")

                elif comando_low == "productos":
                    prods = mapa_mud[loc]["productos"]
                    if prods:
                        lista = "\n".join([f"- {k}: ${v:.2f}" for k, v in prods.items()])
                        mud.send_message(client_id, f"Productos disponibles en esta zona:\n{lista}")
                    else:
                        mud.send_message(client_id, "No hay productos a la venta aquí.")

                elif comando_low == "mirar":
                    mud.send_message(client_id, mapa_mud[loc]["desc"])

                elif comando_low == "ir":
                    dir = params.strip().lower()
                    if dir in mapa_mud[loc]["salidas"]:
                        ubicacion_jugadores[client_id] = mapa_mud[loc]["salidas"][dir]
                        mud.send_message(client_id, mapa_mud[ubicacion_jugadores[client_id]]["desc"])
                    else:
                        mud.send_message(client_id, "No puedes ir hacia allá.")

                elif comando_low == "comprar":
                    partes_compra = params.strip().lower().split()
                    
                    if not partes_compra:
                        mud.send_message(client_id, "Especifica qué quieres comprar. Ej: comprar pan 2")
                        continue
                        
                    item = partes_compra[0]
                    cantidad = 1 # Cantidad por defecto si el usuario no pone número
                    
                    # Si el usuario escribió una segunda palabra, intentamos que sea la cantidad
                    if len(partes_compra) > 1:
                        try:
                            cantidad = int(partes_compra[1])
                            if cantidad <= 0:
                                mud.send_message(client_id, "La cantidad debe ser mayor que 0.")
                                continue
                        except ValueError:
                            mud.send_message(client_id, "La cantidad debe ser un número. Ej: comprar pan 2")
                            continue

                    # Comprobamos si el producto se vende aquí
                    if item in mapa_mud[loc]["productos"]:
                        precio_unitario = mapa_mud[loc]["productos"][item]
                        coste_total = precio_unitario * cantidad
                        
                        # Comprobamos si el jugador tiene dinero para pagar el total
                        if jugadores_dinero[client_id] >= coste_total:
                            # ¡Avisamos a las tiendas con la cantidad correcta!
                            _broadcast(f"MUD_BUY {nombres_clientes[client_id]} {item} {cantidad}")
                            mud.send_message(client_id, f"Intentando comprar {cantidad}x {item} (Total: ${coste_total:.2f}). Esperando al tendero...")
                        else:
                            mud.send_message(client_id, f"No tienes dinero suficiente. Cuesta ${coste_total:.2f} y tienes ${jugadores_dinero[client_id]:.2f}.")
                    else:
                        mud.send_message(client_id, "Ese producto no está aquí.")
                
                elif comando_low == "decir":
                    _broadcast(f"\033[36m{nombres_clientes[client_id]} dice:\033[0m {params}")
                continue
# --- LÓGICA TIENDAS ---
            if command == "MUD_ACCEPT":
                partes = params.split() # item, qty, cliente, total
                if len(partes) >= 4:
                    # Si el comprador es un humano, le restamos el dinero
                    for cid, nom in nombres_clientes.items():
                        if nom == partes[2] and tipo_cliente.get(cid) == "jugador":
                            total = float(partes[3])
                            cantidad_comprada = partes[1]
                            producto = partes[0]
                            jugadores_dinero[cid] -= total
                            mud.send_message(cid, f"\033[1;32mCompra completada: {cantidad_comprada}x {producto}. Gastaste ${total:.2f}.\033[0m")
                _broadcast(f"{command} {params}")
                
            # --- ¡ESTAS SON LAS LÍNEAS QUE FALTABAN! ---
            elif command in ["MUD_REJECT", "MUD_OFFER", "MUD_WANT", "MUD_BUY", "MUD_SELL"]:
                _broadcast(f"{command} {params}")

        time.sleep(0.01)
if __name__ == "__main__":
    print("La Avenida MUY NORMAL- MEGA SIMULACIÓN COMBINADA (Versión MUD Distribuida + Marketplace)")
    print("================================================================================")
    print("Este módulo es el CENTRO que rutea mensajes y gestiona el Marketplace.")
    print("Opciones:")
    print("  1 - Iniciar SOLO servidor MUD")
    print("  2 - Iniciar servidor MUD + Lanzar ambos clientes en ventanas nuevas")
    print("================================================================================")

    op = input("Opción (1/2): ").strip()

    if op == "2":
        try:
            print("Lanzando procesos...")
            if os.name == 'nt':
                subprocess.Popen(["python", "P2_cliente_fruteria.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                subprocess.Popen(["python", "P2_cliente_supermercado.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(["python", "P2_cliente_fruteria.py"])
                subprocess.Popen(["python", "P2_cliente_supermercado.py"])
        except Exception as e:
            print(f"Error al lanzar subprocesos: {e}")

    banco_central = Banco()
    threading.Thread(target=banco_central.escuchar, daemon=True).start()

    run_server()