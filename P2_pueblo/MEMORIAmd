# Memoria Explicativa — Pueblo Villaviciosa del Ron

## 1. Descripción del Juego

**Pueblo Villaviciosa del Ron** 
Es un juego de texto (MUD) jugable desde la terminal en el que el jugador puede navegar entre dos barrios con 5 comercios cada uno, comprar productos, y observar cómo los negocios comercian entre sí de forma autónoma.

El pueblo está compuesto por:

**Barrio La Comarca**
- Panadería Cod Ere
- Restaurante Asquas
- Supermercado Batman
- Taller Mecánico Fire Mega
- Carpintería Pájaro Loco

**Barrio La Avenida**
- Frutería Joaquin
- Heladería Biboli
- Supermercado Ahorramenos
- Herrería Forjado a Fuego
- Panadería Alemanya

---

## 2. Arquitectura del Sistema


* ECONOMATO CENTRAL (comunicación mediante Pyro5 RMI)
    - Registro de usuarios
    - Catálogo
    - Transacciones

* BARRIOS
    - Barrio 1 - La Comarca (5 comercios)
    - Barrio 2 - La Avenida (5 comercios)
Cada barrio funciona de forma independinte, pero conectado al sistema central
La comunicación entre barrios se realiza mediante Pyro5


### Componentes principales:

1. **pueblo.py**: Script principal que orquesta todo y presenta el juego terminal
2. **economato.py**: Servicio Pyro5 RMI centralizado
3. **barrio_rmi.py**: Clase base `Tienda` + adaptador `BarrioRMI` para Pyro5
4. **tiendas_comarca.py**: 5 clases de tiendas del Barrio La Comarca
5. **tiendas_avenida.py**: 5 clases de tiendas del Barrio La Avenida

---

## 3. Economato Central

El **Economato** es un servicio Pyro5 que centraliza las funciones económicas del pueblo:

- **Registro de barrios**: Cada barrio se registra con su URI Pyro5 al arrancar
- **Catálogo global**: Consulta unificada de todos los productos de todos los barrios
- **Cuentas corrientes**: Saldo de cada tienda gestionado centralmente
- **Compras inter-barrio**: Media las compras entre tiendas de distintos barrios, cobrando una **comisión del 5%**
- **Historial**: Log de todas las transacciones inter-barrio con timestamps

### API del Economato (Pyro5 RMI):

```python
@Pyro5.api.expose
class Economato:
    def registrar_barrio(nombre, uri)          # Registrar barrio
    def catalogo_global()                       # Catálogo de todo el pueblo
    def comprar_inter_barrio(comprador, barrio_vendedor, producto, cantidad)
    def consultar_saldo(tienda_id)
    def depositar(tienda_id, cantidad)
    def historial()                             # Log de transacciones
    def resumen()                               # Estado del economato
```

---

## 4. Uso de Pyro5 (Remote Method Invocation)

La librería **Pyro5** se utiliza para la invocación remota de métodos entre barrios:

### ¿Qué es Pyro5?
Pyro5 (Python Remote Objects) permite llamar a métodos de objetos Python que están en otros procesos o máquinas como si fueran locales. Usa un **Name Server** para el descubrimiento de servicios.

### Cómo se usa en el proyecto:

1. **Name Server**: Se arranca un Pyro5 Name Server en `localhost:9090`
2. **Registro**: Cada barrio se registra como un `BarrioRMI` en el Name Server
3. **Descubrimiento**: El Economato localiza los barrios por nombre vía el Name Server
4. **Invocación**: Cuando un barrio quiere comprar a otro, el Economato obtiene un `Proxy` del barrio vendedor y llama a su método `vender()` vía RMI

### Ejemplo de flujo:

```
Jugador en Carpintería (Comarca) ejecuta: importar clavos 5

1. pueblo.py → economato.comprar_inter_barrio("La Comarca.carpinteria", "La Avenida", "clavos", 5)
2. Economato obtiene URI de "La Avenida" del Name Server
3. Economato crea Proxy Pyro5 → barrio_avenida_rmi.vender("clavos", 5)
4. BarrioRMI busca la tienda que tiene clavos (Herrería)
5. Herrería.vender("clavos", 5) → {"ok": "5x clavos vendidos", "total": 40}
6. Economato añade comisión 5%: 40 + 2 = 42€
7. Resultado vuelve al jugador
```

### Clases Pyro5 expuestas:

- `Economato` — registrado como `pueblo.economato`
- `BarrioRMI("La Comarca")` — registrado como `pueblo.barrio.comarca`
- `BarrioRMI("La Avenida")` — registrado como `pueblo.barrio.avenida`

---

## 5. Transacciones entre Calles de Distintos Barrios

Las transacciones inter-barrio son el corazón del sistema distribuido. Se producen de dos formas:

### A) Automáticas (hilo de fondo)

Un hilo daemon revisa periódicamente (cada 15s) si las tiendas necesitan productos del otro barrio:

| Comprador (Barrio) | Vendedor (Barrio) | Producto | Motivo |
|---|---|---|---|
| Carpintería (Comarca) | Herrería (Avenida) | clavos, bisagras | Para fabricar muebles |
| Herrería (Avenida) | Carpintería (Comarca) | mango_madera | Para forjar espadas |
| Restaurante (Comarca) | Frutería (Avenida) | frutas | Ingredientes para platos |

### B) Manuales (jugador)

El jugador puede ejecutar `importar <producto> <cantidad>` estando en cualquier barrio para comprar productos del barrio contrario.

Todas las transacciones inter-barrio pasan por el **Economato** y quedan registradas en el **historial**.

---

## 6. Concurrencia y Sincronización

El sistema es altamente concurrente:

- **Hilos de producción**: Cada tienda tiene 1-3 hilos daemon que producen bienes periódicamente
- **Hilo de comercio inter-barrio**: Un hilo daemon gestiona las compras automáticas entre barrios
- **Hilo Pyro5 daemon**: Atiende las llamadas RMI entrantes
- **Thread-safety**: Todos los accesos al inventario y caja están protegidos con `threading.Lock()`

### Patrón de sincronización:

```python
# Lectura protegida
with tienda.lock:
    stock = tienda.inventario.get("producto", 0)

# Modificación protegida
with tienda.lock:
    tienda.inventario["producto"] -= cantidad
    tienda.caja += precio
```

---

## 7. Instrucciones de Ejecución

### Requisitos
- Python 3.8+
- Pyro5: `pip install Pyro5`

### Ejecución
```bash
cd Pueblo/
python pueblo.py
```

### Comandos del juego

| Comando | Descripción |
|---------|-------------|
| `mirar` | Ver ubicación actual |
| `ir <lugar>` | Moverse entre localizaciones |
| `catalogo` | Ver productos de la tienda actual |
| `catalogo pueblo` | Ver catálogo global (todos los barrios) |
| `comprar <prod> <n>` | Comprar producto local |
| `importar <prod> <n>` | Comprar de otro barrio (Pyro5 RMI) |
| `estado` | Ver inventario y dinero del jugador |
| `economato` | Ver estado del Economato Central |
| `historial` | Ver transacciones inter-barrio |
| `ayuda` | Lista de comandos |
| `salir` | Salir del juego |

---

## 8. Decisiones de Diseño

### ¿Por qué Pyro5 y no sockets TCP?
- **Abstracción**: Pyro5 permite llamar a métodos remotos como si fueran locales
- **Name Server**: Facilita el descubrimiento de servicios sin hardcodear puertos
- **Serialización**: Pyro5 gestiona automáticamente la serialización/deserialización
- **Requisito de la práctica**: Se pide explícitamente usar RMI con Pyro

### ¿Por qué 2 barrios con 5 tiendas?
- Equilibra la complejidad con la jugabilidad
- Cada barrio tiene variedad (alimentación, manufactura, servicios)
- Las dependencias cruzadas (Carpintería↔Herrería) crean una economía circular natural

### ¿Por qué un Economato centralizado?
- Requisito de la práctica (funciones económicas del pueblo)
- Permite controlar y auditar las transacciones inter-barrio
- La comisión del 5% incentiva el comercio local

### ¿Por qué hilos y no procesos?
- Simplifica la compartición de estado (inventarios, caja)
- Evita la complejidad de IPC para la comunicación intra-barrio
- Los `Lock` de threading son suficientes para evitar race conditions

---

## 9. Estructura de Ficheros

```
Pueblo/
├── pueblo.py            # Script principal (orquestador + juego terminal)
├── economato.py         # Economato Central (Pyro5 RMI)
├── barrio_rmi.py        # Clase base Tienda + Adaptador BarrioRMI (Pyro5)
├── tiendas_comarca.py   # 5 tiendas del Barrio La Comarca
├── tiendas_avenida.py   # 5 tiendas del Barrio La Avenida
├── MEMORIA.md           # Este documento
├── barrio/              # Código original del barrio La Comarca
├── P2_barrio/           # Código original del barrio Los Artesanos
└── P2_2final_2/         # Código original del barrio La Avenida
```
