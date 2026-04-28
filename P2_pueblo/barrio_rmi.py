"""
Barrio RMI — Adaptador Pyro5 + Clase base Tienda
=================================================
Define:
  - Tienda: clase base para todos los comercios del pueblo
  - BarrioRMI: adaptador Pyro5 que agrupa tiendas y las expone vía RMI
"""

import threading
import time
import random
import Pyro5.api


# ─────────────────────────────────────────────────────────────────────────────
# CLASE BASE: TIENDA
# ─────────────────────────────────────────────────────────────────────────────

class Tienda:
    """
    Clase base para todos los comercios del pueblo.
    Cada tienda tiene inventario, precios, caja registradora y
    capacidad de producción automática en segundo plano.
    """

    def __init__(self, nombre, descripcion, inventario_inicial,
                 precios_venta, caja_inicial=100.0):
        self.nombre = nombre
        self.descripcion = descripcion
        self.inventario = dict(inventario_inicial)
        self.precios_venta = dict(precios_venta)
        self.caja = caja_inicial
        self.lock = threading.Lock()
        self._barrio_tiendas = {}
        self._barrio_nombre = ""

    def configurar_barrio(self, nombre_barrio, tiendas_dict):
        """Conecta la tienda con las demás tiendas de su barrio."""
        self._barrio_nombre = nombre_barrio
        self._barrio_tiendas = tiendas_dict

    # ── Interfaz pública ─────────────────────────────────────────────

    def catalogo(self):
        """Devuelve catálogo con precios y stock."""
        with self.lock:
            resultado = {}
            for prod, precio in self.precios_venta.items():
                stock = self.inventario.get(prod, 0)
                resultado[prod] = {"precio": precio, "stock": stock}
            return resultado

    def vender(self, producto, cantidad):
        """Vende un producto al jugador o a otra tienda."""
        with self.lock:
            if producto not in self.precios_venta:
                return {"error": f"'{producto}' no está en nuestro catálogo"}
            stock = self.inventario.get(producto, 0)
            if stock < cantidad:
                return {"error": f"Solo hay {stock} unidades de {producto}"}
            precio_unit = self.precios_venta[producto]
            total = round(precio_unit * cantidad, 2)
            self.inventario[producto] -= cantidad
            self.caja += total
            return {"ok": f"{cantidad}x {producto} vendidos",
                    "total": total, "precio_unit": precio_unit}

    def estado(self):
        """Devuelve resumen financiero de la tienda."""
        with self.lock:
            return {
                "nombre": self.nombre,
                "caja": round(self.caja, 2),
                "inventario": {k: v for k, v in self.inventario.items() if v > 0},
            }

    # ── Comercio intra-barrio ────────────────────────────────────────

    def comprar_a_vecino(self, nombre_tienda, producto, cantidad):
        """Compra un producto a otra tienda del mismo barrio."""
        vecino = self._barrio_tiendas.get(nombre_tienda)
        if not vecino:
            return {"error": f"Tienda '{nombre_tienda}' no encontrada"}
        resultado = vecino.vender(producto, cantidad)
        if "ok" in resultado:
            with self.lock:
                self.inventario[producto] = self.inventario.get(producto, 0) + cantidad
                self.caja -= resultado["total"]
        return resultado

    # ── Producción automática (override en subclases) ────────────────

    def iniciar_produccion(self):
        """Lanza hilos de producción. Override en subclases."""
        pass

    def _hilo_produccion(self, funcion, intervalo_min, intervalo_max):
        """Helper para crear un hilo de producción periódica."""
        def bucle():
            while True:
                time.sleep(random.uniform(intervalo_min, intervalo_max))
                try:
                    funcion()
                except Exception as e:
                    print(f"[{self.nombre}] Error producción: {e}")
        t = threading.Thread(target=bucle, daemon=True)
        t.start()
        return t


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTADOR PYRO5: BARRIO RMI
# ─────────────────────────────────────────────────────────────────────────────

@Pyro5.api.expose
class BarrioRMI:
    """
    Envuelve un conjunto de tiendas y las expone vía Pyro5 RMI.
    Permite a otros barrios consultar catálogos y comprar productos.
    """

    def __init__(self, nombre, tiendas_dict):
        """
        nombre: nombre del barrio
        tiendas_dict: {nombre_tienda: instancia_Tienda}
        """
        self.nombre = nombre
        self.tiendas = tiendas_dict

    def catalogo(self):
        """Catálogo completo de todas las tiendas del barrio."""
        resultado = {}
        for nombre_t, tienda in self.tiendas.items():
            cat = tienda.catalogo()
            for prod, info in cat.items():
                if info["stock"] > 0:
                    resultado[prod] = {
                        "tienda": nombre_t,
                        "precio": info["precio"],
                        "stock": info["stock"],
                        "barrio": self.nombre,
                    }
        return resultado

    def vender(self, producto, cantidad):
        """Busca la tienda que vende el producto y realiza la venta."""
        for nombre_t, tienda in self.tiendas.items():
            cat = tienda.catalogo()
            if producto in cat and cat[producto]["stock"] >= cantidad:
                resultado = tienda.vender(producto, cantidad)
                if "ok" in resultado:
                    resultado["tienda_vendedora"] = nombre_t
                    resultado["barrio"] = self.nombre
                return resultado
        return {"error": f"'{producto}' no disponible en {self.nombre}"}

    def estado(self):
        """Resumen financiero del barrio."""
        resumen = {"nombre": self.nombre, "tiendas": {}}
        for nombre_t, tienda in self.tiendas.items():
            resumen["tiendas"][nombre_t] = tienda.estado()
        return resumen
