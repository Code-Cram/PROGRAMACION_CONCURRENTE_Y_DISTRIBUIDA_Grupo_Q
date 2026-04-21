"""
Logica generica de un comercio del MUD.

Un comercio se configura con sus catalogos e inventario inicial y se ejecuta
como proceso independiente. La produccion de cada pedido corre en un hilo
separado para no bloquear el bucle principal.

Bugs corregidos respecto a la version original:
  - Race condition: verificar_recursos y consumir_recursos ahora ocurren
    dentro del mismo lock, evitando que dos pedidos simultaneos consuman
    el mismo stock.
  - El comercio ahora cobra las monedas tambien en el flujo de produccion
    bajo demanda (no solo en compra_exitosa).
  - atender_pedido_inter lanza un hilo para producir en lugar de bloquear
    el hilo inter con time.sleep.
"""

import threading
import queue
import time


def iniciar_comercio(
    nombre,
    catalogo,
    catalogo_inter,
    inventario_inicial,
    monedas_iniciales,
    cola_pedidos,
    cola_respuestas,
    cola_pedidos_inter,
    cola_resp_inter,
    cola_pedir_a_vecino,
    cola_resp_vecino,
    recursos_del_vecino,      # set: recursos que este comercio pide al vecino
):
    """
    Proceso generico de comercio. Parametrizado con catalogos e inventario
    para que herreria y carpinteria compartan exactamente la misma logica.
    """
    inventario = dict(inventario_inicial)
    productos_terminados = {}
    monedas = monedas_iniciales
    lock = threading.Lock()

    def log(msg):
        print(f"  [{nombre}] {msg}")

    # --- helpers de inventario (siempre llamar con lock adquirido) ---

    def _verificar(receta):
        for recurso, cantidad in receta["recursos"].items():
            if inventario.get(recurso, 0) < cantidad:
                return False, recurso
        return True, None

    def _consumir(receta):
        for recurso, cantidad in receta["recursos"].items():
            inventario[recurso] -= cantidad

    # --- produccion en hilo ---

    def producir(producto_id, receta, destino_cola, pedido_id):
        log(f"Fabricando {receta['nombre']}... ({receta['tiempo']}s)")
        time.sleep(receta["tiempo"])
        with lock:
            productos_terminados[producto_id] = productos_terminados.get(producto_id, 0) + 1
            # BUG CORREGIDO: cobrar monedas aqui, no solo en compra_exitosa
            monedas_ref[0] += receta["precio"]
        log(f"{receta['nombre']} terminado.")
        destino_cola.put({
            "tipo": "produccion_completa",
            "pedido_id": pedido_id,
            "producto": producto_id,
            "nombre": receta["nombre"],
            "precio": receta["precio"],
        })

    # Usamos una lista de un elemento para poder mutar 'monedas' desde los hilos
    # (las funciones anidadas no pueden hacer 'nonlocal' sobre variables de un
    # proceso externo; este patron evita usar global)
    monedas_ref = [monedas]

    # --- comunicacion inter-comercio ---

    def pedir_al_vecino(recurso, cantidad):
        log(f"Pidiendo {cantidad}x {recurso} al vecino...")
        cola_pedir_a_vecino.put({"tipo": "pedido_inter", "recurso": recurso, "cantidad": cantidad})
        try:
            resp = cola_resp_vecino.get(timeout=60)
            if resp.get("exito"):
                with lock:
                    inventario[recurso] = inventario.get(recurso, 0) + cantidad
                log(f"Recibido {cantidad}x {recurso} del vecino.")
                return True
            log(f"El vecino no tiene {recurso}.")
            return False
        except queue.Empty:
            log("Sin respuesta del vecino (timeout).")
            return False

    def atender_pedido_inter(pedido):
        recurso = pedido.get("recurso")
        cantidad = pedido.get("cantidad", 1)

        # Caso 1: hay que fabricarlo segun catalogo inter
        if recurso in catalogo_inter:
            receta = catalogo_inter[recurso]
            with lock:
                ok, _ = _verificar(receta)
                if ok:
                    _consumir(receta)
            if ok:
                # BUG CORREGIDO: lanzar hilo en lugar de time.sleep aqui
                def fabricar_y_responder():
                    log(f"Produciendo {receta['nombre']} para el vecino...")
                    time.sleep(receta["tiempo"])
                    log(f"{receta['nombre']} entregado al vecino.")
                    cola_resp_inter.put({"exito": True, "recurso": recurso, "cantidad": cantidad})
                threading.Thread(target=fabricar_y_responder, daemon=True).start()
            else:
                cola_resp_inter.put({"exito": False, "recurso": recurso})

        # Caso 2: ya esta en el inventario
        elif inventario.get(recurso, 0) >= cantidad:
            with lock:
                inventario[recurso] -= cantidad
            cola_resp_inter.put({"exito": True, "recurso": recurso, "cantidad": cantidad})

        else:
            cola_resp_inter.put({"exito": False, "recurso": recurso})

    def hilo_inter():
        while True:
            try:
                p = cola_pedidos_inter.get(timeout=1)
                if p.get("tipo") == "cerrar":
                    break
                atender_pedido_inter(p)
            except queue.Empty:
                continue

    threading.Thread(target=hilo_inter, daemon=True).start()
    log(f"Abierto. Inventario inicial: {inventario}")

    # --- bucle principal del proceso ---

    while True:
        try:
            pedido = cola_pedidos.get(timeout=1)
        except queue.Empty:
            continue

        tipo = pedido.get("tipo")

        if tipo == "cerrar":
            log("Cerrando...")
            break

        elif tipo == "ver_catalogo":
            info = {
                pid: {
                    "nombre": r["nombre"],
                    "precio": r["precio"],
                    "tiempo": r["tiempo"],
                    "disponible": productos_terminados.get(pid, 0),
                }
                for pid, r in catalogo.items()
            }
            cola_respuestas.put({
                "tipo": "catalogo",
                "comercio": nombre,
                "productos": info,
                "inventario_materias": dict(inventario),
                "monedas": monedas_ref[0],
            })

        elif tipo == "ver_inventario":
            cola_respuestas.put({
                "tipo": "inventario",
                "materias": dict(inventario),
                "productos": dict(productos_terminados),
                "monedas": monedas_ref[0],
            })

        elif tipo == "comprar":
            producto_id = pedido.get("producto")
            pedido_id   = pedido.get("pedido_id", "?")

            if producto_id not in catalogo:
                cola_respuestas.put({"tipo": "error", "mensaje": f"Producto '{producto_id}' no existe."})
                continue

            receta = catalogo[producto_id]

            # Vender stock ya fabricado si hay
            with lock:
                if productos_terminados.get(producto_id, 0) > 0:
                    productos_terminados[producto_id] -= 1
                    monedas_ref[0] += receta["precio"]
                    cola_respuestas.put({
                        "tipo": "compra_exitosa",
                        "producto": producto_id,
                        "nombre": receta["nombre"],
                        "precio": receta["precio"],
                        "mensaje": f"{receta['nombre']} listo (ya estaba disponible).",
                    })
                    continue

            # Pedir al vecino si falta algun recurso que el provee
            with lock:
                ok, falta = _verificar(receta)

            if not ok and falta in recursos_del_vecino:
                if pedir_al_vecino(falta, receta["recursos"][falta]):
                    with lock:
                        ok, falta = _verificar(receta)

            if not ok:
                cola_respuestas.put({"tipo": "error", "mensaje": f"Sin recursos para '{receta['nombre']}'. Falta: {falta}."})
                continue

            # BUG CORREGIDO: verificar y consumir dentro del mismo lock
            with lock:
                ok, falta = _verificar(receta)
                if ok:
                    _consumir(receta)

            if not ok:
                # Otro hilo consumio el recurso justo antes — poco probable pero posible
                cola_respuestas.put({"tipo": "error", "mensaje": f"Sin recursos para '{receta['nombre']}' (race condition). Intenta de nuevo."})
                continue

            threading.Thread(
                target=producir,
                args=(producto_id, receta, cola_respuestas, pedido_id),
                daemon=True,
            ).start()

            cola_respuestas.put({
                "tipo": "pedido_aceptado",
                "producto": producto_id,
                "nombre": receta["nombre"],
                "tiempo": receta["tiempo"],
                "mensaje": f"Pedido aceptado. {receta['nombre']} estara listo en {receta['tiempo']}s.",
            })
