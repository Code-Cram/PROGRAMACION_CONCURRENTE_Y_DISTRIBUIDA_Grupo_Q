"""
Nodo P2P Base
Implementación de nodo legítimo con gestión de vecinos, heartbeat y mensajería
"""

import socket
import threading
import time
from typing import Dict, List, Optional
import json

import config
from utils.helpers import (
    setup_logger, serialize_message, deserialize_message, 
    generate_node_id, NetworkStats, calculate_pow, verify_pow
)


class P2PNode:
    """
    Nodo P2P con capacidades de:
    - Descubrimiento de peers via bootstrap
    - Mantenimiento de tabla de vecinos
    - Heartbeat automático
    - Defensa anti-Sybil integrada
    """
    
    def __init__(self, host: str, port: int, is_bootstrap: bool = False):
        self.host = host
        self.port = port
        self.node_id = generate_node_id()
        self.is_bootstrap = is_bootstrap
        
        # Gestión de vecinos
        self.neighbors: Dict[str, Dict] = {}  # node_id -> info
        self.max_neighbors = config.MAX_NEIGHBORS
        
        # Defensa: conteo de conexiones por IP
        self.connections_by_ip: Dict[str, int] = {}
        
        # Reputación de nodos
        self.reputation: Dict[str, float] = {}  # node_id -> score
        
        # Servidor TCP
        self.server_socket = None
        self.running = False
        
        # Estadísticas
        self.stats = NetworkStats()
        
        # Logger
        log_name = f"BOOTSTRAP-{port}" if is_bootstrap else f"Node-{port}"
        self.logger = setup_logger(log_name, f"{log_name}.log")
        
        self.logger.info(f"Nodo inicializado | ID: {self.node_id[:8]} | {host}:{port}")
    
    def start(self):
        """Inicia servidor TCP y threads de gestión"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        self.running = True
        
        self.logger.info(f"Servidor TCP escuchando en {self.host}:{self.port}")
        
        # Thread para aceptar conexiones
        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        accept_thread.start()
        
        # Thread para heartbeat
        if not self.is_bootstrap:
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
        
        # Thread para limpieza de vecinos muertos
        cleanup_thread = threading.Thread(target=self._cleanup_dead_neighbors, daemon=True)
        cleanup_thread.start()
    
    def _accept_connections(self):
        """Acepta conexiones entrantes y delega manejo a threads"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error aceptando conexión: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Maneja mensajes de un cliente conectado"""
        try:
            data = client_socket.recv(config.MESSAGE_BUFFER_SIZE)
            if not data:
                return
            
            message = deserialize_message(data)
            self.stats.messages_received += 1
            
            msg_type = message['type']
            sender_id = message['sender']
            payload = message['payload']
            
            # Procesar según tipo de mensaje
            if msg_type == 'JOIN':
                self._handle_join(client_socket, sender_id, payload, address)
            
            elif msg_type == 'PING':
                self._handle_ping(client_socket, sender_id)
            
            elif msg_type == 'GET_PEERS':
                self._handle_get_peers(client_socket)
            
            elif msg_type == 'DATA':
                self._handle_data(sender_id, payload)
            
            else:
                self.logger.warning(f"Tipo de mensaje desconocido: {msg_type}")
        
        except Exception as e:
            self.logger.error(f"Error manejando cliente {address}: {e}")
        
        finally:
            client_socket.close()
    
    def _handle_join(self, client_socket: socket.socket, sender_id: str, 
                     payload: Dict, address: tuple):
        """
        Procesa solicitud JOIN con defensas anti-Sybil:
        1. Limitación por IP
        2. Verificación de reputación
        3. Prueba de trabajo (opcional)
        """
        sender_ip = address[0]
        sender_port = payload.get('port')
        
        # DEFENSA 1: Limitación de conexiones por IP
        if config.ENABLE_IP_LIMITING:
            current_connections = self.connections_by_ip.get(sender_ip, 0)
            if current_connections >= config.MAX_CONNECTIONS_PER_IP:
                self.logger.warning(
                    f"RECHAZADO: {sender_id[:8]} | IP {sender_ip} excede límite "
                    f"({current_connections}/{config.MAX_CONNECTIONS_PER_IP})"
                )
                response = serialize_message('JOIN_REJECTED', self.node_id, 
                                            {'reason': 'IP_LIMIT_EXCEEDED'})
                client_socket.send(response)
                self.stats.connections_rejected += 1
                self.stats.sybil_nodes_detected += 1
                return
        
        # DEFENSA 2: Verificación de reputación
        if config.ENABLE_REPUTATION:
            reputation = self.reputation.get(sender_id, config.INITIAL_REPUTATION)
            if reputation < config.MIN_REPUTATION_THRESHOLD:
                self.logger.warning(
                    f"RECHAZADO: {sender_id[:8]} | Reputación baja ({reputation:.2f})"
                )
                response = serialize_message('JOIN_REJECTED', self.node_id,
                                            {'reason': 'LOW_REPUTATION'})
                client_socket.send(response)
                self.stats.connections_rejected += 1
                return
        
        # DEFENSA 3: Proof of Work (opcional, muy costoso)
        if config.ENABLE_POW:
            pow_data = payload.get('pow', {})
            nonce = pow_data.get('nonce')
            if not verify_pow(sender_id, nonce, config.POW_DIFFICULTY):
                self.logger.warning(f"RECHAZADO: {sender_id[:8]} | PoW inválido")
                response = serialize_message('JOIN_REJECTED', self.node_id,
                                            {'reason': 'INVALID_POW'})
                client_socket.send(response)
                self.stats.connections_rejected += 1
                return
        
        # Verificar si hay espacio en tabla de vecinos
        if len(self.neighbors) >= self.max_neighbors:
            self.logger.warning(
                f"RECHAZADO: {sender_id[:8]} | Tabla llena "
                f"({len(self.neighbors)}/{self.max_neighbors})"
            )
            response = serialize_message('JOIN_REJECTED', self.node_id,
                                        {'reason': 'TABLE_FULL'})
            client_socket.send(response)
            self.stats.connections_rejected += 1
            return
        
        # ACEPTAR CONEXIÓN
        self.neighbors[sender_id] = {
            'ip': sender_ip,
            'port': sender_port,
            'last_seen': time.time(),
            'reputation': self.reputation.get(sender_id, config.INITIAL_REPUTATION)
        }
        
        # Actualizar contador de IP
        self.connections_by_ip[sender_ip] = self.connections_by_ip.get(sender_ip, 0) + 1
        
        self.logger.info(
            f"ACEPTADO: {sender_id[:8]} | {sender_ip}:{sender_port} | "
            f"Vecinos: {len(self.neighbors)}/{self.max_neighbors}"
        )
        
        response = serialize_message('JOIN_ACCEPTED', self.node_id, {
            'your_reputation': self.reputation.get(sender_id, config.INITIAL_REPUTATION)
        })
        client_socket.send(response)
        self.stats.connections_established += 1
    
    def _handle_ping(self, client_socket: socket.socket, sender_id: str):
        """Responde a heartbeat y actualiza reputación"""
        if sender_id in self.neighbors:
            self.neighbors[sender_id]['last_seen'] = time.time()
            
            # Incrementar reputación por ping exitoso
            if config.ENABLE_REPUTATION:
                current_rep = self.reputation.get(sender_id, config.INITIAL_REPUTATION)
                self.reputation[sender_id] = min(1.0, current_rep + config.REPUTATION_GAIN)
        
        response = serialize_message('PONG', self.node_id, {'timestamp': time.time()})
        client_socket.send(response)
    
    def _handle_get_peers(self, client_socket: socket.socket):
        """Retorna lista de vecinos conocidos (para bootstrap)"""
        peer_list = [
            {'id': nid, 'ip': info['ip'], 'port': info['port']}
            for nid, info in self.neighbors.items()
        ]
        response = serialize_message('PEER_LIST', self.node_id, {'peers': peer_list})
        client_socket.send(response)
    
    def _handle_data(self, sender_id: str, payload: Dict):
        """Procesa mensaje de datos (placeholder para aplicación)"""
        self.logger.debug(f"DATA recibido de {sender_id[:8]}: {payload}")
    
    def join_network(self, bootstrap_host: str, bootstrap_port: int):
        """Conecta a la red via nodo bootstrap"""
        try:
            # Preparar payload con PoW si está habilitado
            payload = {'port': self.port}
            
            if config.ENABLE_POW:
                self.logger.info("Calculando Proof of Work...")
                nonce, pow_hash, elapsed = calculate_pow(self.node_id, config.POW_DIFFICULTY)
                payload['pow'] = {'nonce': nonce, 'hash': pow_hash}
                self.logger.info(f"PoW completado en {elapsed:.2f}s | Hash: {pow_hash[:16]}...")
            
            # Conectar a bootstrap
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((bootstrap_host, bootstrap_port))
            
            message = serialize_message('JOIN', self.node_id, payload)
            sock.send(message)
            
            response = deserialize_message(sock.recv(config.MESSAGE_BUFFER_SIZE))
            sock.close()
            
            if response['type'] == 'JOIN_ACCEPTED':
                self.logger.info(f"✓ Unido a red via {bootstrap_host}:{bootstrap_port}")
                
                # Obtener lista de peers
                self._request_peers(bootstrap_host, bootstrap_port)
            
            elif response['type'] == 'JOIN_REJECTED':
                reason = response['payload'].get('reason', 'UNKNOWN')
                self.logger.error(f"✗ JOIN rechazado: {reason}")
        
        except Exception as e:
            self.logger.error(f"Error uniéndose a red: {e}")
    
    def _request_peers(self, host: str, port: int):
        """Solicita lista de peers al bootstrap"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            
            message = serialize_message('GET_PEERS', self.node_id, {})
            sock.send(message)
            
            response = deserialize_message(sock.recv(config.MESSAGE_BUFFER_SIZE))
            sock.close()
            
            if response['type'] == 'PEER_LIST':
                peers = response['payload']['peers']
                self.logger.info(f"Recibidos {len(peers)} peers del bootstrap")
                
                # Conectar a algunos peers
                for peer in peers[:3]:  # Conectar máximo 3
                    if peer['id'] != self.node_id:
                        self._connect_to_peer(peer['ip'], peer['port'])
        
        except Exception as e:
            self.logger.error(f"Error solicitando peers: {e}")
    
    def _connect_to_peer(self, peer_ip: str, peer_port: int):
        """Establece conexión con un peer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_ip, peer_port))
            
            payload = {'port': self.port}
            if config.ENABLE_POW:
                nonce, pow_hash, _ = calculate_pow(self.node_id, config.POW_DIFFICULTY)
                payload['pow'] = {'nonce': nonce, 'hash': pow_hash}
            
            message = serialize_message('JOIN', self.node_id, payload)
            sock.send(message)
            
            response = deserialize_message(sock.recv(config.MESSAGE_BUFFER_SIZE))
            sock.close()
            
            if response['type'] == 'JOIN_ACCEPTED':
                self.logger.info(f"✓ Conectado a peer {peer_ip}:{peer_port}")
        
        except Exception as e:
            self.logger.debug(f"No se pudo conectar a {peer_ip}:{peer_port}: {e}")
    
    def _heartbeat_loop(self):
        """Envía pings periódicos a vecinos"""
        while self.running:
            time.sleep(config.HEARTBEAT_INTERVAL)
            
            for neighbor_id, info in list(self.neighbors.items()):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((info['ip'], info['port']))
                    
                    message = serialize_message('PING', self.node_id, {})
                    sock.send(message)
                    
                    response = deserialize_message(sock.recv(config.MESSAGE_BUFFER_SIZE))
                    sock.close()
                    
                    if response['type'] == 'PONG':
                        self.stats.messages_sent += 1
                
                except Exception as e:
                    self.logger.debug(f"Heartbeat falló con {neighbor_id[:8]}: {e}")
    
    def _cleanup_dead_neighbors(self):
        """Elimina vecinos que no responden hace tiempo"""
        while self.running:
            time.sleep(config.CONNECTION_TIMEOUT)
            
            current_time = time.time()
            dead_neighbors = []
            
            for neighbor_id, info in self.neighbors.items():
                if current_time - info['last_seen'] > config.CONNECTION_TIMEOUT:
                    dead_neighbors.append(neighbor_id)
                    
                    # Penalizar reputación
                    if config.ENABLE_REPUTATION:
                        current_rep = self.reputation.get(neighbor_id, config.INITIAL_REPUTATION)
                        self.reputation[neighbor_id] = max(0.0, current_rep - config.REPUTATION_DECAY)
            
            for neighbor_id in dead_neighbors:
                neighbor_info = self.neighbors.pop(neighbor_id)
                
                # Actualizar contador de IP
                ip = neighbor_info['ip']
                if ip in self.connections_by_ip:
                    self.connections_by_ip[ip] = max(0, self.connections_by_ip[ip] - 1)
                
                self.logger.warning(f"Vecino muerto eliminado: {neighbor_id[:8]}")
    
    def get_network_status(self) -> Dict:
        """Retorna estado actual del nodo"""
        return {
            'node_id': self.node_id[:8],
            'port': self.port,
            'neighbors': len(self.neighbors),
            'max_neighbors': self.max_neighbors,
            'neighbor_list': [n[:8] for n in self.neighbors.keys()],
            'connections_by_ip': dict(self.connections_by_ip),
            'stats': self.stats.get_stats()
        }
    
    def stop(self):
        """Detiene el nodo gracefully"""
        self.logger.info("Deteniendo nodo...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
