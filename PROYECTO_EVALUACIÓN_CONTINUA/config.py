"""
Configuración del Sistema P2P
Parámetros ajustables para simulación y experimentación
"""

# === CONFIGURACIÓN DE RED ===
BOOTSTRAP_HOST = 'localhost'
BOOTSTRAP_PORT = 5000
NODE_BASE_PORT = 5001
ATTACKER_BASE_PORT = 6000

# === PARÁMETROS P2P ===
MAX_NEIGHBORS = 5  # Máximo de vecinos por nodo (Dunbar's number adaptado)
HEARTBEAT_INTERVAL = 5  # Segundos entre heartbeats
CONNECTION_TIMEOUT = 15  # Segundos antes de considerar nodo muerto
MESSAGE_BUFFER_SIZE = 4096

# === PARÁMETROS DE ATAQUE ===
SYBIL_IDENTITIES = 50  # Número de identidades falsas a crear
ATTACK_DELAY = 2  # Segundos antes de iniciar ataque tras bootstrap

# === DEFENSA: LIMITACIÓN POR IP ===
MAX_CONNECTIONS_PER_IP = 2  # Máximo de nodos desde misma IP
ENABLE_IP_LIMITING = True

# === DEFENSA: SISTEMA DE REPUTACIÓN ===
INITIAL_REPUTATION = 0.5  # Reputación inicial [0.0-1.0]
MIN_REPUTATION_THRESHOLD = 0.3  # Bajo este valor, nodo es rechazado
REPUTATION_DECAY = 0.01  # Pérdida por heartbeat perdido
REPUTATION_GAIN = 0.02  # Ganancia por interacción exitosa
ENABLE_REPUTATION = True

# === DEFENSA: PROOF OF WORK ===
POW_DIFFICULTY = 4  # Número de ceros iniciales en hash
ENABLE_POW = False  # Activar PoW (muy costoso, solo demo)

# === SIMULACIÓN ===
NUM_LEGITIMATE_NODES = 10  # Nodos honestos en la red
SIMULATION_DURATION = 60  # Segundos de simulación total

# === LOGGING ===
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_DIR = 'logs'
