# Guía breve de ejecución

**Autores:** Pedro Barros Bobadilla, Marc Martínez Arias, Jorgue Rodríguez Salgado, Juan Fernández Condormango

## Arranque básico

### Ejecutar con defensas

```bash
python main.py --mode normal
```

Es la forma recomendada de empezar porque permite comprobar el comportamiento de la red con las defensas activadas.

### Ejecutar sin defensas

```bash
python main.py --mode no-defense
```

Esta ejecución sirve como referencia para medir el impacto máximo del ataque.

### Analizar resultados

```bash
python analyze_results.py
```

Con este comando se revisan las métricas generadas por la simulación.

## Comparar dos ejecuciones

Una secuencia razonable para comparar escenarios es esta:

```bash
python main.py --mode no-defense
python main.py --mode normal
python analyze_results.py compare logs/metrics_1.json logs/metrics_2.json
```

Si los nombres exactos de los JSON cambian, basta con sustituirlos por los que se hayan generado en la carpeta `logs/`.

## Configuraciones útiles

### Red más grande

```bash
python main.py --nodes 20 --sybil 100 --max-neighbors 10
```

### Demostración pequeña y clara

```bash
python main.py --nodes 5 --sybil 10 --max-neighbors 3
```

### Activar prueba de trabajo

```bash
python main.py --enable-pow
```

Conviene usar esta opción con cuidado porque puede alargar bastante el tiempo de ejecución.

## Revisar logs durante la ejecución

### Bootstrap

```bash
tail -f logs/BOOTSTRAP-5000.log
```

### Nodo concreto

```bash
tail -f logs/Node-5001.log
```

### Atacante

```bash
tail -f logs/attacker.log
```

### Resumen general

```bash
tail -f logs/simulation.log
```

### Filtrar eventos importantes

```bash
tail -f logs/simulation.log | grep "ATAQUE\|RECHAZADO\|VEREDICTO"
```

## Problemas habituales

### Error: `Address already in use`

Suele ocurrir cuando una ejecución anterior no ha cerrado bien los sockets.

```bash
# Linux o macOS
killall python

# Windows
taskkill /F /IM python.exe
```

Si no quieres matar procesos a mano, otra opción es esperar unos segundos a que el sistema libere los puertos.

### No se crean los logs

Comprueba que exista la carpeta `logs/`.

```bash
mkdir -p logs
python main.py
```

### La simulación va demasiado lenta

Lo más habitual es que la prueba de trabajo esté activada o que el número de identidades Sybil sea demasiado alto para la configuración elegida.
