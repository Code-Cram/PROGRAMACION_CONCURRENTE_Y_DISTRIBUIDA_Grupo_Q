from panaderia import Negocio   
import time

class Supermercado(Negocio):

    def __init__(self, puerto: int = 5002) -> None:
        super().__init__("Supermercado", puerto)

        self.inventario = {
            "harina": 50,
            "manzanas": 30,
            "leche": 20,
            "huevos": 40,
            "azucar": 25
        }


    # VENDER PRODUCTOS
    def vender_producto(self, producto: str, cantidad: int) -> dict:
        if producto not in self.inventario:
            print(f"Supermercado: producto {producto} no existe")
            return {"estado": "error", "mensaje": "Producto no existe"}

        if self.inventario[producto] < cantidad:
            print(f"Supermercado: no hay suficiente {producto}")
            return {"estado": "error", "mensaje": "No hay suficiente stock"}

        print(f"Supermercado: preparando pedido de {producto}...")
        time.sleep(2)

        print(f"Supermercado: vendiendo {cantidad} de {producto}")

        self.inventario[producto] -= cantidad
        print(f"Supermercado: stock restante de {producto} -> {self.inventario[producto]}")
        if self.inventario[producto] < 10:
            print(f"Supermercado: poco stock de {producto}")
            self.reponer_stock(producto)

        return {
            "estado": "ok",
            "mensaje": f"{cantidad} {producto} vendidos"
        }

    def reponer_stock(self, producto: str):
        print(f"Supermercado: reponiendo {producto}...")
        
        time.sleep(2)

        self.inventario[producto] += 20

        print(f"Supermercado: nuevo stock de {producto} -> {self.inventario[producto]}")

    # POLIMORFISMO
    def procesar_mensaje(self, mensaje: dict) -> dict:
        tipo = mensaje.get("tipo")

        if tipo == "pedido":
            producto = mensaje.get("producto")
            cantidad = mensaje.get("cantidad", 1)

            print(f"Supermercado: pedido recibido -> {producto} x{cantidad}")

            return self.vender_producto(producto, cantidad)

        elif tipo == "estado":
            print("Supermercado: enviando estado del inventario")
            return self.inventario

        return {"estado": "error", "mensaje": "Mensaje no válido"}

if __name__ == "__main__":
    supermercado = Supermercado()
    supermercado.iniciar_servidor()