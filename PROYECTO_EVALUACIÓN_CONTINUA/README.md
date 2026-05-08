# Simulador de ataque Sybil en una red P2P

**Autores:** Pedro Barros Bobadilla, Marc Martínez Arias, Jorgue Rodríguez Salgado, Juan Fernández Condormango

## Visión general

Este repositorio contiene una simulación de red P2P pensada para estudiar cómo funciona un ataque Sybil y qué efecto tienen varias defensas sencillas cuando el atacante intenta introducir muchas identidades falsas en poco tiempo.

La estructura del proyecto está orientada a que cada parte tenga una responsabilidad clara. Hay un nodo bootstrap para el arranque de la red, nodos legítimos que mantienen sus vecinos, un atacante que genera identidades falsas y un simulador que coordina la ejecución completa y deja trazas del experimento.

## Qué hace cada módulo

### `config.py`

Define los parámetros globales de la simulación: número de nodos legítimos, número de identidades Sybil, tamaño máximo de la tabla de vecinos, activación o no de defensas y directorio de logs.

### `main.py`

Es el punto de entrada. Lee los argumentos de línea de comandos, ajusta la configuración según el modo seleccionado y lanza el simulador principal.

### `core/node.py`

Contiene la implementación de `P2PNode`. Cada nodo abre un servidor TCP, atiende conexiones entrantes, intercambia mensajes con otros nodos y mantiene su tabla de vecinos. Aquí también se aplican las defensas contra el ataque.

### `attack/sybil_attacker.py`

Modela al atacante. Su trabajo consiste en generar múltiples identidades y lanzar intentos de entrada en paralelo para tratar de ocupar espacio en la red.

### `simulation/simulator.py`

Orquesta todo el ciclo del experimento. Arranca el bootstrap, crea nodos legítimos, espera a que la red se estabilice, lanza el ataque, recoge métricas y deja un resumen final en consola y en un fichero JSON.

### `utils/helpers.py`

Agrupa funciones auxiliares: logging, serialización de mensajes y utilidades relacionadas con la prueba de trabajo y otros detalles de soporte.

## Funcionamiento general

El flujo normal de ejecución se puede resumir así:

1. Se inicia el nodo bootstrap.
2. Se levantan los nodos legítimos.
3. Esos nodos se conectan al bootstrap y empiezan a descubrir vecinos.
4. La red espera unos segundos para estabilizarse.
5. El atacante Sybil genera identidades falsas y lanza conexiones en paralelo.
6. El simulador recoge métricas y genera un informe final.

## Defensas incluidas

### Limitación por IP

Cada nodo puede restringir cuántas conexiones acepta desde una misma dirección IP. En un entorno local esta defensa resulta especialmente visible porque todas las identidades del atacante salen desde la misma máquina.

### Reputación

Los nodos mantienen un historial básico de confianza. Si una identidad no alcanza un umbral mínimo, puede ser rechazada. Esto permite que la red no trate todas las incorporaciones nuevas como si fueran automáticamente fiables.

### Proof of Work opcional

Antes de aceptar una conexión, el nodo puede exigir la resolución de un pequeño problema criptográfico. Su objetivo no es impedir el ataque de forma absoluta, sino elevar el coste de generar muchas identidades seguidas.

## Requisitos

- Python 3.8 o superior.
- No hacen falta dependencias externas si se conserva el enfoque actual basado en la librería estándar.

## Cómo ejecutarlo

### Modo normal

```bash
python main.py --mode normal
```

Ejecuta la simulación con las defensas principales activadas.

### Modo sin defensas

```bash
python main.py --mode no-defense
```

Sirve para comparar el impacto del ataque cuando la red acepta conexiones sin apenas filtros.

### Modo sigiloso

```bash
python main.py --mode stealth
```

Introduce un patrón de ataque menos agresivo para observar si ciertas defensas simples pierden efectividad.

### Configuración personalizada

```bash
python main.py --nodes 20 --sybil 100 --max-neighbors 10
```

Permite cambiar el tamaño de la red y la intensidad del ataque.

### Activar Proof of Work

```bash
python main.py --enable-pow
```

Esta opción hace la ejecución más lenta, sobre todo cuando el número de identidades falsas es alto.

## Salida del programa

La ejecución genera varios tipos de salida:

- Mensajes en consola con las fases del experimento.
- Logs separados para bootstrap, nodos legítimos, atacante y simulador.
- Un fichero JSON con métricas agregadas al final de la ejecución.

## Lectura rápida de los logs

- `BOOTSTRAP-5000.log`: actividad del nodo bootstrap.
- `Node-5001.log` y equivalentes: comportamiento de cada nodo legítimo.
- `attacker.log`: intentos y resultados del atacante.
- `simulation.log`: visión global del experimento.
- `metrics_*.json`: resumen estructurado de configuración y resultados.
