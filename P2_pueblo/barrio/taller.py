from panaderia import Negocio
import time
import threading

class Taller(Negocio):

    def __init__(self, puerto: int = 5003) -> None:
        super().__init__("Taller", puerto)

        self.inventario = {
            "aceite_motor": 5,
            "tornillos": 20,
            "ruedas": 2,
            "coches_en_reparacion": 0,
            "coches_reparados": 0
        }

        self.lock = threading.Lock()

    # -------------------------
    # LÓGICA PROPIA
    # -------------------------
    def reparar_coche(self, tipo: str = "basica") -> dict:
        """
        Tipos de reparación:
          - basica:   necesita aceite_motor x1 + tornillos x4  (5s)
          - ruedas:   necesita ruedas x2 + tornillos x8        (8s)
        """
        requisitos = {
            "basica": {"aceite_motor": 1, "tornillos": 4},
            "ruedas": {"ruedas": 2, "tornillos": 8}
        }

        if tipo not in requisitos:
            return {"error": f"Tipo de reparación '{tipo}' desconocido"}

        materiales = requisitos[tipo]

        # Comprobar stock
        for material, necesario in materiales.items():
            if self.inventario.get(material, 0) < necesario:
                print(f"Taller: falta {material}, pidiendo al supermercado...")
                self.pedir_material("127.0.0.1", material, necesario + 5)
                return {"error": f"Esperando {material} del supermercado"}

        # Consumir materiales e iniciar reparación
        for material, necesario in materiales.items():
            self.inventario[material] -= necesario

        self.inventario["coches_en_reparacion"] += 1
        duracion = 5 if tipo == "basica" else 8
        print(f"Taller: reparación '{tipo}' iniciada ({duracion}s)...")
        time.sleep(duracion)
        self.inventario["coches_en_reparacion"] -= 1
        self.inventario["coches_reparados"] += 1
        print(f"Taller: reparación '{tipo}' completada.")
        return {"ok": f"Reparación '{tipo}' completada"}

    # -------------------------
    # POLIMORFISMO
    # -------------------------
    def procesar_mensaje(self, mensaje: dict) -> dict:
        tipo = mensaje.get("tipo")

        if tipo == "reparar":
            tipo_rep = mensaje.get("reparacion", "basica")
            hilo = threading.Thread(target=self.reparar_coche, args=(tipo_rep,))
            hilo.start()
            return {"ok": f"Reparación '{tipo_rep}' en curso..."}

        elif tipo == "estado":
            return self.inventario

        elif tipo == "servicios":
            return {
                "servicios": ["basica", "ruedas"],
                "precios": {"basica": 50, "ruedas": 120},
                "materiales_necesarios": {
                    "basica": {"aceite_motor": 1, "tornillos": 4},
                    "ruedas": {"ruedas": 2, "tornillos": 8}
                }
            }

        return {"error": "Mensaje no válido"}

    # -------------------------
    # INTERACCIÓN CON OTROS NEGOCIOS
    # -------------------------
    def pedir_material(self, ip_supermercado: str, producto: str, cantidad: int = 10) -> dict:
        """Compra materiales al supermercado (puerto 5002)."""
        print(f"Taller: pidiendo {cantidad} {producto} al supermercado...")
        mensaje = {
            "tipo": "pedido",
            "producto": producto,
            "cantidad": cantidad
        }
        respuesta = self.enviar_mensaje(ip_supermercado, 5002, mensaje)
        print(respuesta)

        if respuesta.get("estado") == "ok":
            self.inventario[producto] = self.inventario.get(producto, 0) + cantidad
            print(f"Taller: {producto} recibido. Stock -> {self.inventario[producto]}")

        return respuesta


    def pedir_menu(self, ip_restaurante: str, cantidad: int = 2) -> dict:
        """Pide menús al restaurante para los trabajadores del taller (puerto 5001)."""
        print(f"Taller: pidiendo {cantidad} menú(s) al restaurante para los trabajadores...")
        mensaje = {
            "tipo": "menu_trabajadores",
            "cantidad": cantidad
        }
        respuesta = self.enviar_mensaje(ip_restaurante, 5001, mensaje)
        print(respuesta)

        if respuesta.get("ok"):
            print(f"Taller: trabajadores alimentados. Precio: {respuesta.get('precio', '?')}€")

        return respuesta


if __name__ == "__main__":
    # Añadir materiales de taller al inventario del supermercado
    # (el supermercado tiene que tener estos productos)
    taller = Taller()
    taller.iniciar_servidor()
