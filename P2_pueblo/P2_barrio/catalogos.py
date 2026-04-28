"""
Catalogos de productos de la Calle de los Artesanos.
Cada producto define: nombre, recursos necesarios, tiempo (s) y precio (monedas).
"""

CATALOGO_HERRERIA = {
    "clavos":     {"nombre": "Clavos (5 uds)",      "recursos": {"lingote_hierro": 1},                    "tiempo": 10, "precio":  8},
    "bisagras":   {"nombre": "Bisagras (2 uds)",     "recursos": {"lingote_hierro": 1},                    "tiempo": 15, "precio": 12},
    "espada":     {"nombre": "Espada de hierro",     "recursos": {"lingote_hierro": 3, "mango_madera": 1}, "tiempo": 30, "precio": 50},
    "herradura":  {"nombre": "Herradura",             "recursos": {"lingote_hierro": 1},                    "tiempo": 10, "precio": 10},
    "reja_arado": {"nombre": "Reja de arado",        "recursos": {"lingote_hierro": 2, "tablon": 1},       "tiempo": 25, "precio": 35},
}

# Precios y tiempos reducidos para pedidos entre comercios
CATALOGO_HERRERIA_INTER = {
    "clavos":   {"nombre": "Clavos (5 uds)",  "recursos": {"lingote_hierro": 1}, "tiempo":  8, "precio": 6},
    "bisagras": {"nombre": "Bisagras (2 uds)", "recursos": {"lingote_hierro": 1}, "tiempo": 10, "precio": 9},
}

CATALOGO_CARPINTERIA = {
    "tablon":      {"nombre": "Tablon de madera",          "recursos": {"tronco": 1},                     "tiempo":  5, "precio":  3},
    "mango_madera":{"nombre": "Mango de madera",           "recursos": {"tablon": 1},                     "tiempo":  8, "precio":  5},
    "silla":       {"nombre": "Silla de madera",           "recursos": {"tablon": 2, "clavos": 1},        "tiempo": 20, "precio": 25},
    "mesa":        {"nombre": "Mesa de madera",            "recursos": {"tablon": 4, "clavos": 1},        "tiempo": 30, "precio": 40},
    "puerta":      {"nombre": "Puerta de madera",          "recursos": {"tablon": 3, "bisagras": 1},      "tiempo": 25, "precio": 35},
    "escudo":      {"nombre": "Escudo de madera reforzado","recursos": {"tablon": 2, "lingote_hierro": 1},"tiempo": 20, "precio": 30},
}

CATALOGO_CARPINTERIA_INTER = {
    "mango_madera": {"nombre": "Mango de madera",  "recursos": {"tablon": 1},  "tiempo": 6, "precio": 3},
    "tablon":       {"nombre": "Tablon de madera", "recursos": {"tronco": 1},  "tiempo": 4, "precio": 2},
}
