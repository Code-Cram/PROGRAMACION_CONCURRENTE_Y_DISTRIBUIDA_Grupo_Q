# Tutorial — P2 Grupo Q: MUD Concurrente

## Instalación

```bash
pip install Pyro4 serpent
```

> Si usas un entorno conda concreto, actívalo primero:
> ```bash
> conda activate <nombre_entorno>
> pip install Pyro4 serpent
> ```

---

## Scripts y qué incluye cada uno

| Script | Qué incluye |
|--------|-------------|
| `P2_Grupo_Q_semana1.py` | Una **Calle** con 2 jugadores. Producción concurrente básica, compraventa y gestión de inventario. |
| `P2_Grupo_Q_semana2.py` | Todo lo anterior + un **Barrio** con 2 calles. Redistribución automática de recursos (BarrioComercial) o ajuste dinámico de precios (BarrioEconomico). |
| `P2_Grupo_Q_semana3.py` | Todo lo anterior + un **Pueblo** con 2 barrios. Equilibrio global de recursos entre barrios y modo distribuido con PyRO4. |

---

## Cómo ejecutarlo

```bash
python P2_Grupo_Q_semana1.py
python P2_Grupo_Q_semana2.py
python P2_Grupo_Q_semana3.py   # requiere Pyro4
```

---

## Ejemplo rápido

El juego arranca en una terminal de texto. Tienes un artesano que produce ítems en segundo plano mientras tú escribes comandos.

```
Bienvenido a Calle del Ébano, Marc.

[Marc] > producir madera        # el trabajador empieza a producir en 2º plano
[Marc] > inventario             # ves lo que hay en el taller
  madera: 3

[Marc] > cambiar pedro          # cambias al otro jugador de la calle
[Pedro] > producir tablas       # Pedro consume madera y fabrica tablas
[Pedro] > precio tablas 6       # fija el precio de venta

[Pedro] > cambiar marc
[Marc] > comprar tablas 1       # Marc compra una tabla por 6 monedas
[Marc] > bolsa                  # ves tu inventario personal y monedas

[Marc] > salir                  # cierra el juego limpiamente
```

### Comandos principales

| Comando | Acción |
|---------|--------|
| `producir [item]` | Empieza a producir ese ítem |
| `parar` | Para la producción |
| `inventario` | Stock del taller compartido |
| `bolsa` | Tu inventario personal y monedas |
| `comprar [item] [n]` | Compra del taller al precio fijado |
| `vender [item] [n] [jugador]` | Venta directa a otro jugador |
| `depositar` / `retirar` | Mueve ítems entre bolsa y taller |
| `cambiar [jugador]` | Cambia el jugador activo |
| `ayuda` | Muestra todos los comandos |
| `salir` | Cierra el juego |
