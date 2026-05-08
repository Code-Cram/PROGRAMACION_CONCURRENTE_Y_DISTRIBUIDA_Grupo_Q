"""
Módulo de Utilidades
Logger, serialización de mensajes, helpers criptográficos
"""

import json
import hashlib
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import config


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Configura logger con formato profesional"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler
    if config.LOG_TO_FILE and log_file:
        Path(config.LOG_DIR).mkdir(exist_ok=True)
        file_handler = logging.FileHandler(f"{config.LOG_DIR}/{log_file}")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def serialize_message(msg_type: str, sender_id: str, payload: Any) -> bytes:
    """
    Serializa mensaje P2P a JSON bytes
    Incluye timestamp y checksum para integridad
    """
    message = {
        'type': msg_type,
        'sender': sender_id,
        'payload': payload,
        'timestamp': time.time()
    }
    
    json_msg = json.dumps(message)
    message['checksum'] = hashlib.sha256(json_msg.encode()).hexdigest()[:8]
    
    return json.dumps(message).encode('utf-8')


def deserialize_message(data: bytes) -> Dict:
    """Deserializa mensaje JSON con validación básica"""
    try:
        message = json.loads(data.decode('utf-8'))
        required_fields = ['type', 'sender', 'payload', 'timestamp']
        
        if not all(field in message for field in required_fields):
            raise ValueError("Mensaje incompleto")
        
        return message
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Error al deserializar mensaje: {e}")


def generate_node_id() -> str:
    """Genera UUID único para identificación de nodo"""
    return str(uuid.uuid4())


def calculate_pow(data: str, difficulty: int) -> tuple:
    """
    Proof of Work: encuentra nonce que genere hash con N ceros iniciales
    Retorna (nonce, hash, tiempo_computación)
    """
    start = time.time()
    nonce = 0
    target = '0' * difficulty
    
    while True:
        hash_input = f"{data}{nonce}"
        hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
        
        if hash_result.startswith(target):
            elapsed = time.time() - start
            return nonce, hash_result, elapsed
        
        nonce += 1


def verify_pow(data: str, nonce: int, difficulty: int) -> bool:
    """Verifica validez de Proof of Work"""
    target = '0' * difficulty
    hash_input = f"{data}{nonce}"
    hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
    return hash_result.startswith(target)


class NetworkStats:
    """Recopilador de métricas de red para análisis"""
    def __init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.connections_established = 0
        self.connections_rejected = 0
        self.sybil_nodes_detected = 0
        self.start_time = time.time()
    
    def get_stats(self) -> Dict:
        elapsed = time.time() - self.start_time
        return {
            'uptime_seconds': round(elapsed, 2),
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'connections_established': self.connections_established,
            'connections_rejected': self.connections_rejected,
            'sybil_detected': self.sybil_nodes_detected,
            'msg_rate': round(self.messages_sent / elapsed, 2) if elapsed > 0 else 0
        }
    
    def reset(self):
        self.__init__()
