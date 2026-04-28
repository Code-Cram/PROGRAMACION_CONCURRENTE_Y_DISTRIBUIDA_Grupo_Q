# Barrio: La Comarca

## Descripción

El barrio **La Comarca** está formado por **dos calles** con 4 negocios distribuidos que se comunican entre sí mediante **sockets TCP**.

### Negocios y puertos

| Negocio | Puerto | Calle |
|---------|--------|-------|
| Panadería El Horno | `5000` | Calle 1 |
| Restaurante El Rincón | `5001` | Calle 2 |
| Supermercado La Despensa | `5002` | Calle 1 |
| Taller Mecánico El Piston | `5003` | Calle 2 |

### Red de interacciones distribuidas

```
  [Panadería :5000] ←── harina/huevos ──→ [Supermercado :5002]
         │                                         ↑
         │ pan                              aceite/tornillos
         ↓                                         │
  [Restaurante :5001] ←── menús ─────── [Taller :5003]
         │
         └── huevos/leche ──→ [Supermercado :5002]
```

### Interacciones económicas

| Comprador | Proveedor | Producto | Precio |
|-----------|-----------|----------|--------|
| Restaurante | Panadería | pan | automático |
| Restaurante | Supermercado | huevos, leche | automático |
| Taller | Restaurante | menú trabajadores | 4€/menú |
| Taller | Supermercado | aceite, tornillos, ruedas | automático |
| Panadería | Supermercado | harina, huevos | automático |

### Característica única del barrio

**Economía circular**: Cuando un negocio se queda sin stock, lo pide automáticamente al proveedor correspondiente sin intervención del usuario. Todo el barrio funciona de forma autónoma y distribuida.

## Requisitos

Python 3.6+ — sin dependencias externas.

## Cómo ejecutar el barrio completo

### Opción A: MUD interactivo (recomendado)

```bash
cd barrio/
python mud_barrio.py
```

En otra terminal, conéctate como jugador:

```bash
telnet localhost 1234
```

Puedes abrir **varias terminales** con `telnet` para tener múltiples jugadores simultáneos.

### Opción B: Terminal clásica

```bash
cd barrio/
python negocios.py
```

## Comandos del MUD

Una vez conectado por telnet, introduce tu nombre y explora:

| Comando | Descripción |
|---------|-------------|
| `mirar` | Ver descripción del lugar actual |
| `ir <lugar>` | Moverse: `plaza`, `restaurante`, `taller`, `supermercado`, `panaderia` |
| `estado` | Inventario del negocio actual |
| `carta` | Carta del restaurante (en restaurante) |
| `bocadillo` | Hacer un bocadillo — pide pan a Panadería si falta |
| `tortilla` | Hacer una tortilla — pide huevos a Supermercado si falta |
| `reparar basica` | Reparación básica: 50€, 5s |
| `reparar ruedas` | Cambio de ruedas: 120€, 8s |
| `menu <n>` | Taller pide n menús al Restaurante (interacción distribuida) |
| `comprar <producto> <n>` | Comprar en el Supermercado |
| `pan <n>` | Hornear pan en la Panadería |
| `ayuda` | Ver todos los comandos |
| `salir` | Desconectarse |

### Ejemplo de sesión

```
telnet localhost 1234

¡Bienvenido al MUD: El Barrio - La Comarca!
¿Cómo te llamas, viajero?
> Ana

¡Bienvenida, Ana! Disfruta del barrio.

[Plaza del Barrio - La Comarca]
Estás en la Plaza Central...
Salidas: restaurante, taller, supermercado, panaderia

> ir restaurante
[Restaurante El Rincón]
...

> bocadillo
El cocinero se pone manos a la obra...
✓ 1 bocadillo(s) hechos — ¡Buen provecho!

> ir taller
> menu 3
El taller pide 3 menú(s) al Restaurante El Rincón...
✓ 3 menú(s) preparados para el taller — Total: 12€
```

## Estructura de ficheros

```
barrio/
├── mudserver.py      # Motor mud-pi (no modificar)
├── mud_barrio.py     # MUD del barrio (entrada principal MUD)
├── negocios.py       # Modo terminal clásico (todos los negocios)
├── calle.py          # Modo terminal solo calle 2
├── panaderia.py      # Clase base Negocio + Panadería
├── restaurante.py    # Lógica del restaurante
├── super.py          # Lógica del supermercado
├── taller.py         # Lógica del taller
└── README.md
```

## Puertos utilizados

| Servicio | Puerto |
|----------|--------|
| Panadería (socket) | 5000 |
| Restaurante (socket) | 5001 |
| Supermercado (socket) | 5002 |
| Taller (socket) | 5003 |
| MUD Telnet | 1234 |

## Checklist de requisitos entregados

- ✅ Interacción entre profesiones de la misma calle (Taller → Restaurante: menús)
- ✅ Interacción distribuida entre calles (Restaurante → Panadería, Taller → Supermercado)
- ✅ Interacción comercial/económica (precios en €, stock, reposición automática)
- ✅ MUD con motor mud-pi (telnet localhost 1234)
- ✅ 1 repositorio por calle + 1 repositorio de barrio
