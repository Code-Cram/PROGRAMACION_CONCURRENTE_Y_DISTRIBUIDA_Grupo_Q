"""
Tiendas del Barrio LavaBocas
=============================
5 comercios:
  1. Frutería Joaquin       — frutas frescas, cócteles
  2. Heladería Biboli        — helados artesanales
  3. Supermercado Ahorramenos    — snacks, bebidas, conservas
  4. Herrería Forjado a Fuego         — clavos, bisagras, espadas (inter-barrio: vende a Carpintería)
  5. Panadería Alemanya        — pan con manzana, empanadas
"""

from barrio_rmi import Tienda
import random


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRUTERÍA Joaquin 
# ─────────────────────────────────────────────────────────────────────────────

class FruteriaAvenida(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Frutería Joaquin",
            descripcion=(
                "Fruta fresca de temporada expuesta en cajones de madera.\n"
                "Manzanas, naranjas, uvas y cacao recién llegados del campo.\n"
                "También preparan cócteles de frutas."
            ),
            inventario_inicial={
                "apple": 30, "orange": 30, "grape": 20,
                "cacao": 15, "coctel": 0,
            },
            precios_venta={
                "apple": 1, "orange": 1.25, "grape": 1.50,
                "cacao": 1.25, "coctel": 2.50,
            },
            caja_inicial=100.0,
        )

    def _cosechar_frutas(self):
        with self.lock:
            fruta = random.choice(["apple", "orange", "grape", "cacao"])
            cantidad = random.randint(3, 8)
            self.inventario[fruta] += cantidad

    def _producir_cocteles(self):
        with self.lock:
            if (self.inventario.get("orange", 0) >= 2 and
                    self.inventario.get("grape", 0) >= 1):
                self.inventario["orange"] -= 2
                self.inventario["grape"] -= 1
                self.inventario["coctel"] += 2

    def iniciar_produccion(self):
        self._hilo_produccion(self._cosechar_frutas, 5, 10)
        self._hilo_produccion(self._producir_cocteles, 8, 15)


# ─────────────────────────────────────────────────────────────────────────────
# 2. HELADERÍA Biboli
# ─────────────────────────────────────────────────────────────────────────────

class HeladeriaAvenida(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Heladería Biboli",
            descripcion=(
                "Helados artesanales de mil sabores. La leche la producen\n"
                "ellos mismos y el cacao viene de la Frutería.\n"
                "El pan para los conos viene de La Calle LavaCejas."
            ),
            inventario_inicial={
                "leche": 20, "cacao": 5,
                "helado": 5, "helado_cacao": 3,
            },
            precios_venta={"helado": 4.50, "helado_cacao": 6.50},
            caja_inicial=80.0,
        )

    def _producir_leche(self):
        with self.lock:
            if self.inventario.get("leche", 0) < 20:
                self.inventario["leche"] += 8

    def _producir_helados(self):
        with self.lock:
            # Helado normal: 2 leche
            if self.inventario.get("leche", 0) >= 2:
                self.inventario["leche"] -= 2
                self.inventario["helado"] += 1
            # Helado cacao: 2 leche + 1 cacao
            if (self.inventario.get("leche", 0) >= 2 and
                    self.inventario.get("cacao", 0) >= 1):
                self.inventario["leche"] -= 2
                self.inventario["cacao"] -= 1
                self.inventario["helado_cacao"] += 1
        # Pedir cacao a frutería si falta
        with self.lock:
            poco_cacao = self.inventario.get("cacao", 0) < 3
        if poco_cacao:
            self.comprar_a_vecino("fruteria", "cacao", 5)

    def iniciar_produccion(self):
        self._hilo_produccion(self._producir_leche, 6, 12)
        self._hilo_produccion(self._producir_helados, 5, 10)


# ─────────────────────────────────────────────────────────────────────────────
# 3. SUPERMERCADO Ahorramenos
# ─────────────────────────────────────────────────────────────────────────────

class SupermercadoAvenida(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Supermercado Ahorramenos",
            descripcion=(
                "De todo un poco: snacks, bebidas, conservas y helados\n"
                "de reventa. Abastece a los vecinos de La Calle LavaBocas."
            ),
            inventario_inicial={
                "snacks": 20, "bebidas": 20,
                "conservas": 5, "helado": 3,
            },
            precios_venta={
                "snacks": 3.50, "bebidas": 2.50,
                "conservas": 4.50, "helado": 5.20,
            },
            caja_inicial=150.0,
        )

    def _reponer_stock(self):
        with self.lock:
            if self.inventario.get("snacks", 0) < 10:
                self.inventario["snacks"] += random.randint(5, 10)
            if self.inventario.get("bebidas", 0) < 10:
                self.inventario["bebidas"] += random.randint(5, 10)
        # Comprar helado a heladería para reventa
        with self.lock:
            poco_helado = self.inventario.get("helado", 0) < 3
        if poco_helado:
            self.comprar_a_vecino("heladeria", "helado", 3)

    def iniciar_produccion(self):
        self._hilo_produccion(self._reponer_stock, 10, 18)


# ─────────────────────────────────────────────────────────────────────────────
# 4. HERRERÍA Forjado a Fuego
# ─────────────────────────────────────────────────────────────────────────────

class HerreriaAvenida(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Herrería Forjado a Fuego",
            descripcion=(
                "El golpeteo del martillo sobre el yunque resuena sin parar.\n"
                "Aquí se forjan clavos, bisagras y espadas con lingotes de\n"
                "hierro. Los mangos de madera vienen de La Calle LavaCejas."
            ),
            inventario_inicial={
                "lingote_hierro": 20, "mango_madera": 3,
                "clavos": 8, "bisagras": 4,
                "espada": 0, "herradura": 2,
            },
            precios_venta={
                "clavos": 8, "bisagras": 12,
                "espada": 50, "herradura": 10,
            },
            caja_inicial=100.0,
        )

    def _forjar_productos(self):
        with self.lock:
            # Clavos: 1 lingote
            if self.inventario.get("lingote_hierro", 0) >= 1:
                self.inventario["lingote_hierro"] -= 1
                self.inventario["clavos"] += 5
            # Bisagras: 1 lingote
            if self.inventario.get("lingote_hierro", 0) >= 1:
                self.inventario["lingote_hierro"] -= 1
                self.inventario["bisagras"] += 2
            # Herraduras: 1 lingote
            if self.inventario.get("lingote_hierro", 0) >= 1:
                self.inventario["lingote_hierro"] -= 1
                self.inventario["herradura"] += 2
            # Espada: 3 lingotes + 1 mango_madera
            if (self.inventario.get("lingote_hierro", 0) >= 3 and
                    self.inventario.get("mango_madera", 0) >= 1):
                self.inventario["lingote_hierro"] -= 3
                self.inventario["mango_madera"] -= 1
                self.inventario["espada"] += 1

    def _extraer_mineral(self):
        """Simula la extracción de mineral y fundición en lingotes."""
        with self.lock:
            if self.inventario.get("lingote_hierro", 0) < 10:
                self.inventario["lingote_hierro"] += 5

    def iniciar_produccion(self):
        self._hilo_produccion(self._forjar_productos, 8, 15)
        self._hilo_produccion(self._extraer_mineral, 10, 18)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PANADERÍA Alemanya
# ─────────────────────────────────────────────────────────────────────────────

class PanaderiaAvenida(Tienda):
    def __init__(self):
        super().__init__(
            nombre="Panadería Alemanya",
            descripcion=(
                "Pan caliente y bollos recién hechos. Usan manzanas de la\n"
                "Frutería para su famoso pan con manzana. La harina la\n"
                "muelen ellos mismos."
            ),
            inventario_inicial={
                "harina": 20, "apple": 7,
                "pan": 4, "pan_manzana": 2, "empanada": 0,
            },
            precios_venta={
                "pan": 3.50, "pan_manzana": 4.50, "empanada": 5,
            },
            caja_inicial=50.0,
        )

    def _hornear_pan(self):
        with self.lock:
            if self.inventario.get("harina", 0) >= 2:
                self.inventario["harina"] -= 2
                self.inventario["pan"] += 2
            # Pan con manzana: harina + apple
            if (self.inventario.get("harina", 0) >= 2 and
                    self.inventario.get("apple", 0) >= 1):
                self.inventario["harina"] -= 2
                self.inventario["apple"] -= 1
                self.inventario["pan_manzana"] += 2
        # Auto-reponer harina (molino propio)
        with self.lock:
            if self.inventario.get("harina", 0) < 8:
                self.inventario["harina"] += 10
        # Pedir manzanas a frutería
        with self.lock:
            pocas_manzanas = self.inventario.get("apple", 0) < 3
        if pocas_manzanas:
            self.comprar_a_vecino("fruteria", "apple", 10)

    def _producir_empanadas(self):
        with self.lock:
            if (self.inventario.get("harina", 0) >= 3 and
                    self.inventario.get("apple", 0) >= 2):
                self.inventario["harina"] -= 3
                self.inventario["apple"] -= 2
                self.inventario["empanada"] += 1

    def iniciar_produccion(self):
        self._hilo_produccion(self._hornear_pan, 4, 8)
        self._hilo_produccion(self._producir_empanadas, 10, 20)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE CONSTRUCCIÓN DEL BARRIO
# ─────────────────────────────────────────────────────────────────────────────

def crear_avenida():
    """
    Crea e interconecta las 5 tiendas del Barrio LavaBocas.
    Devuelve dict {nombre_clave: instancia_Tienda}.
    """
    tiendas = {
        "fruteria":     FruteriaAvenida(),
        "heladeria":    HeladeriaAvenida(),
        "supermercado":  SupermercadoAvenida(),
        "herreria":     HerreriaAvenida(),
        "panaderia":    PanaderiaAvenida(),
    }
    for t in tiendas.values():
        t.configurar_barrio("Barrio LavaBocas", tiendas)
    return tiendas
