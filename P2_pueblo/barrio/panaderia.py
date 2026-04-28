import socket
import json
import threading
import time

class Negocio:

    def __init__(self, nombre: str, puerto: int) -> None:
        self.nombre = nombre
        self.puerto = puerto
        self.inventario = {}


    # SERVIDOR
    def iniciar_servidor(self, host: str = "0.0.0.0") -> None:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, self.puerto))
        servidor.listen()

        print(f"{self.nombre} escuchando en {host}:{self.puerto}")

        while True:
            conn, addr = servidor.accept()
            hilo = threading.Thread(target=self.manejar_cliente, args=(conn,))
            hilo.start()

    def manejar_cliente(self, conn: socket.socket) -> None:
        data = conn.recv(1024).decode()
        mensaje = json.loads(data)

        respuesta = self.procesar_mensaje(mensaje)

        conn.send(json.dumps(respuesta).encode())
        conn.close()


    # MÉTODO A SOBRESCRIBIR
    def procesar_mensaje(self, mensaje: str) -> dict:
        return {"error": "No implementado"}


    # CLIENTE (enviar mensajes)
    def enviar_mensaje(self, ip: str, puerto: int, mensaje: str) -> dict:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, puerto))

            s.send(json.dumps(mensaje).encode())
            respuesta = json.loads(s.recv(1024).decode())

            s.close()
            return respuesta

        except Exception as e:
            return {"error": str(e)}

class Panaderia(Negocio):

    def __init__(self, puerto: int = 5000) -> None:
        super().__init__("Panaderia", puerto)

        self.inventario = {
            "harina": 10,
            "pan": 0,
            "huevos":0
        }


    # LÓGICA PROPIA
    def hacer_pan(self, cantidad: int) -> dict:

        #PRIMERO comprobar huevos
        if self.inventario.get("huevos", 0) < 1:
            print("Panadería: faltan huevos, pidiendo...")
            respuesta = self.pedir_producto("127.0.0.1", "huevos", 5)
            if self.inventario.get("huevos", 0) < 1:
                return {"error": "No se pudieron conseguir huevos"}

        #luego ya haces pan
        if self.inventario["harina"] >= cantidad:
            
            self.inventario["harina"] -= cantidad
            self.inventario["huevos"] -= 1
            self.inventario["pan"] += cantidad

            print(f"Panadería: {cantidad} panes hechos")

            if self.inventario["harina"] < 3:
                print("Panadería: poca harina, pidiendo más...")
                self.pedir_harina("127.0.0.1", 5)

            return {"ok": f"{cantidad} panes hechos"}

        return {"error": "No hay harina"}

    def vender_pan(self, cantidad: int) -> dict[str, str]:
        if self.inventario["pan"] >= cantidad:
            self.inventario["pan"] -= cantidad
            return {"ok": f"{cantidad} panes vendidos"}
        return {"error": "No hay pan"}


    # POLIMORFISMO
    def procesar_mensaje(self, mensaje: str) -> dict:
        tipo = mensaje.get("tipo")

        if tipo == "comprar_pan":
            return self.vender_pan(mensaje.get("cantidad", 1))

        elif tipo == "estado":
            return self.inventario

        return {"error": "Mensaje no válido"}


    # INTERACCIÓN CON OTROS
    def pedir_harina(self, ip_supermercado: str, cantidad: int = 5) -> dict:
        
        print("Panadería: pidiendo harina al supermercado...")

        mensaje = {
            "tipo": "pedido",
            "producto": "harina",
            "cantidad": cantidad
        }

        respuesta = self.enviar_mensaje(ip_supermercado, 5002, mensaje)
        print(respuesta)

        if respuesta.get("estado") == "ok":
            print("Panadería: harina recibida correctamente")
            self.inventario["harina"] += cantidad

            print("Panadería: usando harina para hacer pan...")
            self.hacer_pan(3)

        return respuesta  
    
    def pedir_producto(self, ip_supermercado: str, producto: str, cantidad: int = 5) -> dict:
    
        print(f"Panadería: pidiendo {producto} al supermercado...")

        mensaje = {
            "tipo": "pedido",
            "producto": producto,
            "cantidad": cantidad
        }

        respuesta = self.enviar_mensaje(ip_supermercado, 5002, mensaje)
        print(respuesta)

        if respuesta.get("estado") == "ok":
            print(f"Panadería: {producto} recibido correctamente")
            self.inventario[producto] = self.inventario.get(producto, 0) + cantidad

        return respuesta