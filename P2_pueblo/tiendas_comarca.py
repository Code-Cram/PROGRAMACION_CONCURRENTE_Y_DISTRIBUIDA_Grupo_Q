"""
Tiendas del Barrio LavaCejas
=============================
5 comercios:
  1. Panadería Cod Ere      — pan, bollería
  2. Restaurante Asquas   — bocadillos, tortillas, menús
  3. Supermercado Batman — productos varios, auto-reposición
  4. Taller Mecánico Fire Mega — reparaciones de coches
  5. Carpintería Pajaro Loco   — muebles, tablas (inter-barrio: necesita clavos de Herrería)
"""

from barrio_rmi import Tienda
import random


# ─────────────────────────────────────────────────────────────────────────────
# 1. PANADERÍA COD ERE
# ─────────────────────────────────────────────────────────────────────────────

class PanaderiaComarca(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Panadería Cod Ere",
            descripcion=(
                "El calor del horno llega desde la trastienda y el olor a pan\n"
                "recién hecho impregna el ambiente. Aquí se hacen los mejores\n"
                "panes del pueblo con harina del Supermercado."
            ),
            inventario_inicial={"harina": 15, "huevos": 10, "pan": 5,
                                "pan_integral": 2, "bolleria": 0},
            precios_venta={"pan": 3, "pan_integral": 4, "bolleria": 5},
            caja_inicial=80.0,
        )

    def _producir_pan(self):
        with self.lock:
            if self.inventario["harina"] >= 2 and self.inventario["huevos"] >= 1:
                self.inventario["harina"] -= 2
                self.inventario["huevos"] -= 1
                self.inventario["pan"] += 3
                # print(f"[{self.nombre}] Horneados 3 panes")
        # Pedir al supermercado si falta harina
        with self.lock:
            poca_harina = self.inventario["harina"] < 5
            pocos_huevos = self.inventario["huevos"] < 3
        if poca_harina:
            self.comprar_a_vecino("supermercado", "harina", 10)
        if pocos_huevos:
            self.comprar_a_vecino("supermercado", "huevos", 6)

    def _producir_bolleria(self):
        with self.lock:
            if self.inventario["harina"] >= 3 and self.inventario["huevos"] >= 2:
                self.inventario["harina"] -= 3
                self.inventario["huevos"] -= 2
                self.inventario["bolleria"] += 2

    def iniciar_produccion(self):
        self._hilo_produccion(self._producir_pan, 4, 8)
        self._hilo_produccion(self._producir_bolleria, 8, 15)


# ─────────────────────────────────────────────────────────────────────────────
# 2. RESTAURANTE ASQUAS
# ─────────────────────────────────────────────────────────────────────────────

class RestauranteComarca(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Restaurante Asquas",
            descripcion=(
                "Mesas con manteles de cuadros, olor a cocina casera y\n"
                "el murmullo de la radio de fondo. El pan viene fresco\n"
                "de la Panadería cada mañana."
            ),
            inventario_inicial={"pan": 5, "huevos": 8, "bocadillo": 3,
                                "tortilla": 2, "menu": 1},
            precios_venta={"bocadillo": 4, "tortilla": 6, "menu": 8},
            caja_inicial=100.0,
        )

    def _producir_bocadillos(self):
        with self.lock:
            if self.inventario["pan"] >= 1:
                self.inventario["pan"] -= 1
                self.inventario["bocadillo"] += 1
        with self.lock:
            poco_pan = self.inventario["pan"] < 3
        if poco_pan:
            self.comprar_a_vecino("panaderia", "pan", 5)

    def _producir_tortillas(self):
        with self.lock:
            if self.inventario["huevos"] >= 2:
                self.inventario["huevos"] -= 2
                self.inventario["tortilla"] += 1
        with self.lock:
            pocos_huevos = self.inventario["huevos"] < 4
        if pocos_huevos:
            self.comprar_a_vecino("supermercado", "huevos", 6)

    def _producir_menus(self):
        with self.lock:
            if self.inventario["bocadillo"] >= 1 and self.inventario["tortilla"] >= 1:
                self.inventario["bocadillo"] -= 1
                self.inventario["tortilla"] -= 1
                self.inventario["menu"] += 1

    def iniciar_produccion(self):
        self._hilo_produccion(self._producir_bocadillos, 5, 10)
        self._hilo_produccion(self._producir_tortillas, 8, 14)
        self._hilo_produccion(self._producir_menus, 10, 18)


# ─────────────────────────────────────────────────────────────────────────────
# 3. SUPERMERCADO BATMAN
# ─────────────────────────────────────────────────────────────────────────────

class SupermercadoComarca(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Supermercado Batman",
            descripcion=(
                "Estanterías repletas de productos que abastecen a todos\n"
                "los negocios del barrio. Harina, huevos, aceite, tornillos…\n"
                "aquí encuentras de todo."
            ),
            inventario_inicial={
                "harina": 50, "huevos": 40, "leche": 20,
                "manzanas": 30, "azucar": 25,
                "aceite_motor": 20, "tornillos": 100, "ruedas": 8,
            },
            precios_venta={
                "harina": 2, "huevos": 1.5, "leche": 2,
                "manzanas": 1, "azucar": 1.5,
                "aceite_motor": 5, "tornillos": 3, "ruedas": 15,
            },
            caja_inicial=200.0,
        )

    def _reponer_stock(self):
        with self.lock:
            for producto in ["harina", "huevos", "leche", "manzanas", "azucar"]:
                if self.inventario.get(producto, 0) < 10:
                    self.inventario[producto] += 15
            for producto in ["aceite_motor", "tornillos", "ruedas"]:
                if self.inventario.get(producto, 0) < 5:
                    self.inventario[producto] += 10

    def iniciar_produccion(self):
        self._hilo_produccion(self._reponer_stock, 12, 20)


# ─────────────────────────────────────────────────────────────────────────────
# 4. TALLER MECÁNICO FIRE MEGA
# ─────────────────────────────────────────────────────────────────────────────

class TallerComarca(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Taller Mecánico Fire Mega",
            descripcion=(
                "Olor a aceite, coches en los elevadores y cajas de\n"
                "herramientas por doquier. Los materiales llegan del\n"
                "Supermercado y los trabajadores comen en el Restaurante."
            ),
            inventario_inicial={
                "aceite_motor": 5, "tornillos": 20, "ruedas": 2,
                "reparacion_basica": 0, "cambio_ruedas": 0,
            },
            precios_venta={"reparacion_basica": 50, "cambio_ruedas": 120},
            caja_inicial=100.0,
        )

    def _producir_servicios(self):
        with self.lock:
            # Reparación básica: 1 aceite + 4 tornillos
            if (self.inventario.get("aceite_motor", 0) >= 1 and
                    self.inventario.get("tornillos", 0) >= 4):
                self.inventario["aceite_motor"] -= 1
                self.inventario["tornillos"] -= 4
                self.inventario["reparacion_basica"] += 1
            # Cambio de ruedas: 2 ruedas + 8 tornillos
            if (self.inventario.get("ruedas", 0) >= 2 and
                    self.inventario.get("tornillos", 0) >= 8):
                self.inventario["ruedas"] -= 2
                self.inventario["tornillos"] -= 8
                self.inventario["cambio_ruedas"] += 1
        # Pedir materiales si faltan
        with self.lock:
            poco_aceite = self.inventario.get("aceite_motor", 0) < 3
            pocos_torn = self.inventario.get("tornillos", 0) < 10
        if poco_aceite:
            self.comprar_a_vecino("supermercado", "aceite_motor", 5)
        if pocos_torn:
            self.comprar_a_vecino("supermercado", "tornillos", 20)

    def iniciar_produccion(self):
        self._hilo_produccion(self._producir_servicios, 8, 15)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CARPINTERÍA PÁJARO LOCO
# ─────────────────────────────────────────────────────────────────────────────

class CarpinteriaComarca(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Carpintería Pájaro Loco",
            descripcion=(
                "Virutas de madera cubren el suelo. El carpintero trabaja\n"
                "con troncos para hacer tablas y muebles de calidad.\n"
                "Los clavos y bisagras vienen de la Herrería del otro barrio."
            ),
            inventario_inicial={
                "tronco": 15, "tablon": 10, "clavos": 5,
                "bisagras": 2, "mango_madera": 3,
                "silla": 0, "mesa": 0, "puerta": 0,
            },
            precios_venta={
                "tablon": 3, "mango_madera": 5,
                "silla": 25, "mesa": 40, "puerta": 35,
            },
            caja_inicial=80.0,
        )

    def _producir_tablones(self):
        with self.lock:
            if self.inventario.get("tronco", 0) >= 1:
                self.inventario["tronco"] -= 1
                self.inventario["tablon"] += 2
        # Auto-reponer troncos (bosque cercano)
        with self.lock:
            if self.inventario.get("tronco", 0) < 5:
                self.inventario["tronco"] += 5

    def _producir_muebles(self):
        with self.lock:
            # Silla: 2 tablones + 1 clavos
            if (self.inventario.get("tablon", 0) >= 2 and
                    self.inventario.get("clavos", 0) >= 1):
                self.inventario["tablon"] -= 2
                self.inventario["clavos"] -= 1
                self.inventario["silla"] += 1
            # Mesa: 4 tablones + 1 clavos
            if (self.inventario.get("tablon", 0) >= 4 and
                    self.inventario.get("clavos", 0) >= 1):
                self.inventario["tablon"] -= 4
                self.inventario["clavos"] -= 1
                self.inventario["mesa"] += 1
            # Puerta: 3 tablones + 1 bisagras
            if (self.inventario.get("tablon", 0) >= 3 and
                    self.inventario.get("bisagras", 0) >= 1):
                self.inventario["tablon"] -= 3
                self.inventario["bisagras"] -= 1
                self.inventario["puerta"] += 1

    def _producir_mangos(self):
        with self.lock:
            if self.inventario.get("tablon", 0) >= 1:
                self.inventario["tablon"] -= 1
                self.inventario["mango_madera"] += 1

    def iniciar_produccion(self):
        self._hilo_produccion(self._producir_tablones, 5, 10)
        self._hilo_produccion(self._producir_muebles, 10, 20)
        self._hilo_produccion(self._producir_mangos, 8, 15)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE CONSTRUCCIÓN DEL BARRIO
# ─────────────────────────────────────────────────────────────────────────────

def crear_comarca():
    """
    Crea e interconecta las 5 tiendas del Barrio LavaCejas.
    Devuelve dict {nombre_clave: instancia_Tienda}.
    """
    tiendas = {
        "panaderia":    PanaderiaComarca(),
        "restaurante":  RestauranteComarca(),
        "supermercado":  SupermercadoComarca(),
        "taller":       TallerComarca(),
        "carpinteria":  CarpinteriaComarca(),
    }
    for t in tiendas.values():
        t.configurar_barrio("Barrio LavaCejas", tiendas)
    return tiendas
