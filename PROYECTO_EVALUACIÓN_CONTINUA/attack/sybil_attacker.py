"""
Atacante Sybil
Genera múltiples identidades falsas para saturar tablas de vecinos
"""

import socket
import threading
import time
from typing import List
import random

import config
from utils.helpers import (
    setup_logger, serialize_message, deserialize_message, 
    generate_node_id, NetworkStats
)


class SybilNode:
    """
    Nodo malicioso que ejecuta ataque Sybil mediante:
    - Generación masiva de identidades únicas
    - Conexión paralela a nodos objetivo
    - Saturación de tablas de vecinos
    """
    
    def __init__(self, num_identities: int = config.SYBIL_IDENTITIES):
        self.num_identities = num_identities
        self.sybil_identities: List[str] = []
        self.successful_connections = 0
        self.rejected_connections = 0
        
        self.logger = setup_logger("ATTACKER", "attacker.log")
        self.stats = NetworkStats()
        
        self.logger.warning(
            f"\n╔═══════════════════════════════════════════════════╗\n"
            f"║  ATACANTE SYBIL INICIALIZADO                                                                                        ║\n"
            f"║  Identidades a generar: {num_identities:4d}                                                         ║\n"
            f"╚═══════════════════════════════════════════════════╝"
        )
    
    def generate_identities(self):
        """Genera pool de identidades falsas"""
        self.logger.info(f"Generando {self.num_identities} identidades Sybil...")
        
        for i in range(self.num_identities):
            fake_id = generate_node_id()
            self.sybil_identities.append(fake_id)
        
        self.logger.info(
            f"✓ {len(self.sybil_identities)} identidades creadas | "
            f"Primeras 3: {[sid[:8] for sid in self.sybil_identities[:3]]}"
        )
    
    def launch_attack(self, target_host: str, target_port: int, 
                     attack_all_nodes: bool = True):
        """
        Ejecuta ataque Sybil contra nodo(s) objetivo
        
        Args:
            target_host: IP del primer objetivo
            target_port: Puerto del primer objetivo
            attack_all_nodes: Si True, ataca rango de puertos
        """
        self.logger.warning(" INICIANDO ATAQUE SYBIL ")
        
        if attack_all_nodes:
            # Atacar todos los nodos en rango de puertos
            target_ports = range(
                config.NODE_BASE_PORT, 
                config.NODE_BASE_PORT + config.NUM_LEGITIMATE_NODES
            )
        else:
            target_ports = [target_port]
        
        # Lanzar conexiones en paralelo para cada identidad
        threads = []
        
        for identity in self.sybil_identities:
            # Cada identidad ataca un nodo aleatorio (o todos)
            target = random.choice(list(target_ports))
            
            thread = threading.Thread(
                target=self._attack_single_target,
                args=(identity, target_host, target),
                daemon=True
            )
            threads.append(thread)
            thread.start()
            
            # Pequeño delay para evitar saturar SO
            time.sleep(0.01)
        
        # Esperar a que terminen los intentos de conexión
        self.logger.info(f"Esperando finalización de {len(threads)} hilos de ataque...")
        for thread in threads:
            thread.join(timeout=10)
        
        self._report_attack_results()
    
    def _attack_single_target(self, fake_id: str, host: str, port: int):
        """Intenta conectar una identidad Sybil a un nodo"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            
            # Usar puerto falso alto para simular nodo diferente
            fake_port = config.ATTACKER_BASE_PORT + random.randint(1, 9999)
            
            payload = {'port': fake_port}
            
            # Nota: Sin PoW, el ataque es trivial
            # Con PoW habilitado, cada identidad debe computar hash
            if config.ENABLE_POW:
                # En ataque real, atacante podría precalcular o usar hardware especializado
                # Aquí simplemente no enviamos PoW, esperando rechazo
                pass
            
            message = serialize_message('JOIN', fake_id, payload)
            sock.send(message)
            
            response = deserialize_message(sock.recv(config.MESSAGE_BUFFER_SIZE))
            sock.close()
            
            if response['type'] == 'JOIN_ACCEPTED':
                self.successful_connections += 1
                self.logger.debug(
                    f"✓ Sybil {fake_id[:8]} ACEPTADO en {host}:{port}"
                )
            
            elif response['type'] == 'JOIN_REJECTED':
                self.rejected_connections += 1
                reason = response['payload'].get('reason', 'UNKNOWN')
                self.logger.debug(
                    f"✗ Sybil {fake_id[:8]} RECHAZADO en {host}:{port} | "
                    f"Razón: {reason}"
                )
        
        except Exception as e:
            self.rejected_connections += 1
            self.logger.debug(
                f"✗ Sybil {fake_id[:8]} ERROR conectando a {host}:{port}: {e}"
            )
    
    def _report_attack_results(self):
        """Genera reporte del resultado del ataque"""
        total_attempts = len(self.sybil_identities)
        success_rate = (self.successful_connections / total_attempts * 100) if total_attempts > 0 else 0
        
        report = f"""
╔═══════════════════════════════════════════════════════════╗
║               REPORTE DE ATAQUE SYBIL                                                                                                            ║
╠═══════════════════════════════════════════════════════════╣
║  Identidades generadas:    {total_attempts:5d}                                                                            ║
║  Conexiones exitosas:      {self.successful_connections:5d}  ({success_rate:5.1f}%)   ║
║  Conexiones rechazadas:    {self.rejected_connections:5d}  ({100-success_rate:5.1f}%)║
╠═══════════════════════════════════════════════════════════╣
║  EVALUACIÓN DEL ATAQUE:                                                                                                                         ║
"""
        
        if success_rate > 50:
            report += "║   ATAQUE EXITOSO - Red comprometida               ║\n"
        elif success_rate > 20:
            report += "║    ATAQUE PARCIAL - Defensas débiles              ║\n"
        else:
            report += "║   ATAQUE MITIGADO - Defensas efectivas            ║\n"
        
        report += "╚═══════════════════════════════════════════════════════════╝"
        
        self.logger.warning(report)
    
    def get_attack_stats(self):
        """Retorna estadísticas del ataque"""
        return {
            'total_identities': len(self.sybil_identities),
            'successful_connections': self.successful_connections,
            'rejected_connections': self.rejected_connections,
            'success_rate': (self.successful_connections / len(self.sybil_identities) * 100) 
                           if self.sybil_identities else 0
        }


class AdvancedSybilAttacker(SybilNode):
    """
    Atacante Sybil avanzado con técnicas evasivas:
    - Rotación de IPs (simulada via proxies)
    - Rate limiting evasivo
    - Comportamiento adaptativo
    """
    
    def __init__(self, num_identities: int = config.SYBIL_IDENTITIES):
        super().__init__(num_identities)
        self.logger.info("Modo AVANZADO: Evasión de defensas activada")
    
    def launch_stealthy_attack(self, target_host: str, target_port: int):
        """
        Ataque sigiloso con rate limiting
        Envía conexiones espaciadas para evitar detección
        """
        self.logger.warning(" Iniciando ataque SIGILOSO con rate limiting")
        
        for i, identity in enumerate(self.sybil_identities):
            self._attack_single_target(identity, target_host, target_port)
            
            # Delay entre conexiones para evadir rate limiting
            time.sleep(0.5)
            
            if (i + 1) % 10 == 0:
                self.logger.info(f"Progreso: {i+1}/{len(self.sybil_identities)} identidades procesadas")
        
        self._report_attack_results()
