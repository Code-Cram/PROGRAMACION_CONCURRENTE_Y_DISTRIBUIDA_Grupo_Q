from panaderia import Negocio
import time
import threading

class Restaurante(Negocio):

    def __init__(self, puerto: int = 5001) -> None:
        super().__init__("Restaurante", puerto)

        self.inventario = {
            "pan": 0,
            "huevos": 5,
            "leche": 3,
            "bocadillo": 0,
            "tortilla": 0
        }

        self.lock = threading.Lock()

    # -------------------------
    # LÓGICA PROPIA
    # -------------------------
    def hacer_bocadillo(self, cantidad: int = 1) -> dict:
        if self.inventario.get("pan", 0) < cantidad:
            print("Restaurante: falta pan, pidiendo a la panadería...")
            self.pedir_pan("127.0.0.1", cantidad + 2)
            return {"error": "Esperando pan de la panadería"}

        self.inventario["pan"] -= cantidad
        print(f"Restaurante: preparando {cantidad} bocadillo(s)...")
        time.sleep(2)
        self.inventario["bocadillo"] += cantidad
        print(f"Restaurante: {cantidad} bocadillo(s) listos")
        return {"ok": f"{cantidad} bocadillo(s) hechos"}

    def hacer_tortilla(self, cantidad: int = 1) -> dict:
        if self.inventario.get("huevos", 0) < cantidad * 2:
            print("Restaurante: faltan huevos, pidiendo al supermercado...")
            self.pedir_ingrediente("127.0.0.1", "huevos", 6)
            return {"error": "Esperando huevos del supermercado"}

        self.inventario["huevos"] -= cantidad * 2
        print(f"Restaurante: preparando {cantidad} tortilla(s)...")
        time.sleep(3)
        self.inventario["tortilla"] += cantidad
        print(f"Restaurante: {cantidad} tortilla(s) lista(s)")
        return {"ok": f"{cantidad} tortilla(s) hechas"}

    def vender_plato(self, plato: str, cantidad: int = 1) -> dict:
        if self.inventario.get(plato, 0) >= cantidad:
            self.inventario[plato] -= cantidad
            return {"ok": f"{cantidad} {plato}(s) vendido(s)"}
        return {"error": f"No hay {plato} disponible"}

    # -------------------------
    # POLIMORFISMO
    # -------------------------
    def procesar_mensaje(self, mensaje: dict) -> dict:
        tipo = mensaje.get("tipo")

        if tipo == "pedir_plato":
            plato = mensaje.get("plato", "")
            cantidad = mensaje.get("cantidad", 1)
            return self.vender_plato(plato, cantidad)

        elif tipo == "hacer_bocadillo":
            cantidad = mensaje.get("cantidad", 1)
            hilo = threading.Thread(target=self.hacer_bocadillo, args=(cantidad,))
            hilo.start()
            return {"ok": f"Preparando {cantidad} bocadillo(s)..."}

        elif tipo == "hacer_tortilla":
            cantidad = mensaje.get("cantidad", 1)
            hilo = threading.Thread(target=self.hacer_tortilla, args=(cantidad,))
            hilo.start()
            return {"ok": f"Preparando {cantidad} tortilla(s)..."}

        elif tipo == "estado":
            return self.inventario

        elif tipo == "carta":
            return {"platos": ["bocadillo", "tortilla"], "precios": {"bocadillo": 4, "tortilla": 6}}

        elif tipo == "menu_trabajadores":
            # El taller pide menús para sus trabajadores
            cantidad = mensaje.get("cantidad", 1)
            print(f"Restaurante: pedido de {cantidad} menú(s) del taller")
            # Intentamos preparar bocadillos (plato rápido para trabajadores)
            resultado = self.hacer_bocadillo(cantidad)
            if "ok" in resultado:
                return {"ok": f"{cantidad} menú(s) preparados para el taller", "precio": cantidad * 4}
            return resultado

        return {"error": "Mensaje no válido"}

    # -------------------------
    # INTERACCIÓN CON OTROS NEGOCIOS
    # -------------------------
    def pedir_pan(self, ip_panaderia: str, cantidad: int = 3) -> dict:
        """Compra pan a la panadería (puerto 5000)."""
        print(f"Restaurante: pidiendo {cantidad} pan(es) a la panadería...")
        mensaje = {
            "tipo": "comprar_pan",
            "cantidad": cantidad
        }
        respuesta = self.enviar_mensaje(ip_panaderia, 5000, mensaje)
        print(respuesta)

        if respuesta.get("ok"):
            self.inventario["pan"] = self.inventario.get("pan", 0) + cantidad
            print(f"Restaurante: pan recibido. Stock pan -> {self.inventario['pan']}")

        return respuesta

    def pedir_ingrediente(self, ip_supermercado: str, producto: str, cantidad: int = 5) -> dict:
        """Compra ingredientes al supermercado (puerto 5002)."""
        print(f"Restaurante: pidiendo {cantidad} {producto} al supermercado...")
        mensaje = {
            "tipo": "pedido",
            "producto": producto,
            "cantidad": cantidad
        }
        respuesta = self.enviar_mensaje(ip_supermercado, 5002, mensaje)
        print(respuesta)

        if respuesta.get("estado") == "ok":
            self.inventario[producto] = self.inventario.get(producto, 0) + cantidad
            print(f"Restaurante: {producto} recibido. Stock -> {self.inventario[producto]}")

        return respuesta


if __name__ == "__main__":
    restaurante = Restaurante()
    restaurante.iniciar_servidor()
