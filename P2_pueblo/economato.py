"""
Economato Central del Pueblo — Servicio Pyro5 RMI
==================================================
Gestiona las funciones económicas y comerciales centrales:
  - Registro de barrios y sus catálogos
  - Catálogo global del pueblo
  - Cuentas corrientes de cada tienda
  - Compras inter-barrio mediadas por RMI
  - Historial de transacciones
"""

import Pyro5.api
import threading
from datetime import datetime


@Pyro5.api.expose
class Economato:
    """Servicio central del pueblo, accesible vía Pyro5 RMI."""

    COMISION = 0.05  # 5 % de comisión por transacción inter-barrio

    def __init__(self):
        self._barrios = {}       # nombre_barrio -> Pyro5 URI (str)
        self._cuentas = {}       # "barrio.tienda" -> saldo (float)
        self._historial = []     # lista de dicts con cada transacción
        self._lock = threading.Lock()

    # ── Registro ─────────────────────────────────────────────────────

    def registrar_barrio(self, nombre, uri):
        """Registra un barrio con su URI Pyro5."""
        with self._lock:
            self._barrios[nombre] = uri
        print(f"[ECONOMATO] Barrio '{nombre}' registrado (URI: {uri})")
        return True

    def registrar_cuenta(self, tienda_id, saldo_inicial=0.0):
        """Crea una cuenta corriente para una tienda."""
        with self._lock:
            if tienda_id not in self._cuentas:
                self._cuentas[tienda_id] = saldo_inicial
        return True

    # ── Cuentas ──────────────────────────────────────────────────────

    def depositar(self, tienda_id, cantidad):
        with self._lock:
            self._cuentas.setdefault(tienda_id, 0.0)
            self._cuentas[tienda_id] += cantidad
        return self._cuentas[tienda_id]

    def retirar(self, tienda_id, cantidad):
        with self._lock:
            saldo = self._cuentas.get(tienda_id, 0.0)
            if saldo >= cantidad:
                self._cuentas[tienda_id] -= cantidad
                return {"ok": True, "saldo": self._cuentas[tienda_id]}
            return {"ok": False, "error": "Saldo insuficiente", "saldo": saldo}

    def consultar_saldo(self, tienda_id):
        with self._lock:
            return self._cuentas.get(tienda_id, 0.0)

    # ── Catálogo global ──────────────────────────────────────────────

    def catalogo_global(self):
        """Consulta el catálogo de TODOS los barrios vía Pyro5."""
        catalogo = {}
        for nombre, uri in list(self._barrios.items()):
            try:
                proxy = Pyro5.api.Proxy(uri)
                cat = proxy.catalogo()
                catalogo[nombre] = cat
            except Exception as e:
                catalogo[nombre] = {"error": str(e)}
        return catalogo

    # ── Compras inter-barrio ─────────────────────────────────────────

    def comprar_inter_barrio(self, comprador_id, barrio_vendedor, producto, cantidad):
        """
        Media una compra entre tiendas de distintos barrios.
        Cobra una comisión del 5 %.
        """
        uri = self._barrios.get(barrio_vendedor)
        if not uri:
            return {"error": f"Barrio '{barrio_vendedor}' no registrado"}

        try:
            proxy = Pyro5.api.Proxy(uri)
            resultado = proxy.vender(producto, cantidad)
        except Exception as e:
            return {"error": f"Error de comunicación RMI: {e}"}

        if "error" in resultado:
            return resultado

        precio_base = resultado["total"]
        comision = round(precio_base * self.COMISION, 2)
        precio_final = round(precio_base + comision, 2)

        # Registrar la transacción
        with self._lock:
            self._historial.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "comprador": comprador_id,
                "barrio_vendedor": barrio_vendedor,
                "producto": producto,
                "cantidad": cantidad,
                "precio_base": precio_base,
                "comision": comision,
                "precio_final": precio_final,
            })

        resultado["comision"] = comision
        resultado["precio_final"] = precio_final
        return resultado

    # ── Historial ────────────────────────────────────────────────────

    def historial(self):
        with self._lock:
            return list(self._historial)

    def resumen(self):
        """Resumen del estado del economato."""
        with self._lock:
            return {
                "barrios_registrados": list(self._barrios.keys()),
                "num_cuentas": len(self._cuentas),
                "num_transacciones": len(self._historial),
                "cuentas": dict(self._cuentas),
                "comision_total": round(
                    sum(t.get("comision", 0) for t in self._historial), 2
                ),
            }
