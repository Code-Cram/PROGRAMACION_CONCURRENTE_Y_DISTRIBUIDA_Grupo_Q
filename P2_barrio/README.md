# Tutorial de ejecución del Barrio MUD-Pi

Este documento explica cómo ejecutar el servidor del videojuego integrado y cómo conectarse a él desde terminal usando telnet.

## Archivos necesarios

Todos los archivos deben estar en la misma carpeta del proyecto:

- `P2_Grupo_Q_semana2.py` — lógica principal del barrio, calles, jugadores y trabajadores.
- `mudserver.py` — servidor telnet basado en mud-pi.
- `P2_Grupo_Q_barrio_mudpi.py` — script integrador del videojuego.

## 1. Comprobar que los archivos están en la misma carpeta

Desde una terminal, entra en la carpeta del proyecto y ejecuta:

```bash
ls
```

Deberían aparecer, al menos, estos archivos:

```bash
P2_Grupo_Q_semana2.py
mudserver.py
P2_Grupo_Q_barrio_mudpi.py
```

## 2. Ejecutar el servidor

Desde esa misma carpeta, lanza el script principal:

```bash
python P2_Grupo_Q_barrio_mudpi.py
```

Si el arranque ha ido bien, aparecerá un mensaje parecido a este:

```text
Servidor Barrio MUD-Pi escuchando en puerto 1234 (telnet)...
```

Esa terminal debe quedarse abierta, porque ahí se ejecuta el servidor.

## 3. Abrir un cliente telnet

Abre una nueva terminal y ejecuta:

```bash
telnet localhost 1234
```

Si quieres simular varios jugadores a la vez, abre varias terminales y repite ese mismo comando en cada una.

## 4. Elegir personaje

Cuando te conectes, verás un mensaje de bienvenida parecido a este:

```text
Bienvenido al Barrio del Mercado.
Elige personaje escribiendo su nombre:
  marc, pedro, jorge, juan
```

Escribe uno de esos nombres y pulsa Enter. Por ejemplo:

```text
marc
```

Entonces entrarás al juego con ese personaje.

## 5. Comandos básicos dentro del juego

Una vez dentro, puedes usar estos comandos:

- `ayuda` — muestra la lista de comandos.
- `recetas` — muestra las recetas del trabajador activo.
- `producir <item>` — inicia la producción de un objeto.
- `parar` — detiene la producción.
- `inventario` — muestra el inventario de la calle.
- `bolsa` — muestra la bolsa personal y las monedas del jugador.
- `precios` — muestra los precios de producción del jugador.
- `precio <item> <num>` — cambia el precio de producción de un producto.
- `precio_bolsa <item> <num>` — fija el precio de reventa personal.
- `comprar <item> <cantidad>` — compra ítems disponibles en el taller.
- `almacen` — muestra el almacén total del barrio.
- `ranking` — muestra el ranking de calles por riqueza.
- `riqueza` — muestra la riqueza total del barrio.
- `salir` — cierra la sesión del jugador.

## 6. Ejemplo de sesión

Ejemplo de comandos con Marc:

```text
marc
ayuda
recetas
producir madera
inventario
precio madera 4
bolsa
almacen
ranking
riqueza
salir
```

## 7. Cerrar el servidor

Cuando quieras parar completamente el videojuego, vuelve a la terminal donde lanzaste el servidor y pulsa:

```text
Ctrl + C
```

El script cerrará el servidor y detendrá los hilos del barrio.

## 8. Errores habituales

### Error: `No module named ...`

Asegúrate de que todos los archivos están en la misma carpeta y de ejecutar el script desde esa ubicación.

### Error: `telnet: command not found`

Instala telnet en tu sistema. En Ubuntu o Debian:

```bash
sudo apt-get install telnet
```

### El cliente entra pero no responde bien

Comprueba que el servidor sigue ejecutándose en la otra terminal y que no se ha cerrado por error.

## 9. Resumen rápido

1. Coloca `P2_Grupo_Q_semana2.py`, `mudserver.py` y `P2_Grupo_Q_barrio_mudpi.py` en la misma carpeta.
2. Ejecuta `python P2_Grupo_Q_barrio_mudpi.py`.
3. Abre otra terminal y lanza `telnet localhost 1234`.
4. Elige personaje: `marc`, `pedro`, `jorge` o `juan`.
5. Usa `ayuda` para empezar a jugar.
