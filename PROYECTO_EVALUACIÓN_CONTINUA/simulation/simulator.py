"""
Simulador de Red P2P con Ataque Sybil
Orquesta nodos legítimos, bootstrap, atacante y recolección de métricas
"""

import time
import threading
from typing import List
import json
from datetime import datetime

import config
from core.node import P2PNode
from attack.sybil_attacker import SybilNode
from utils.helpers import setup_logger


class NetworkSimulator:
    """
    Simulador completo de red P2P para análisis de ataque Sybil
    
    Flujo de simulación:
    1. Iniciar nodo bootstrap
    2. Iniciar nodos legítimos
    3. Esperar estabilización de red
    4. Lanzar ataque Sybil
    5. Recolectar métricas
    6. Generar reporte
    """
    
    def __init__(self):
        self.bootstrap_node: P2PNode = None
        self.legitimate_nodes: List[P2PNode] = []
        self.attacker: SybilNode = None
        
        self.logger = setup_logger("SIMULATOR", "simulation.log")
        
        self.logger.info(
            f"\n{'='*60}\n"
            f"SIMULACIÓN DE ATAQUE SYBIL EN RED P2P\n"
            f"{'='*60}\n"
            f"Configuración:\n"
            f"  - Nodos legítimos: {config.NUM_LEGITIMATE_NODES}\n"
            f"  - Identidades Sybil: {config.SYBIL_IDENTITIES}\n"
            f"  - Max vecinos/nodo: {config.MAX_NEIGHBORS}\n"
            f"  - Defensa IP limiting: {config.ENABLE_IP_LIMITING}\n"
            f"  - Defensa Reputación: {config.ENABLE_REPUTATION}\n"
            f"  - Defensa PoW: {config.ENABLE_POW}\n"
            f"{'='*60}"
        )
    
    def setup_network(self):
        """Fase 1: Configurar infraestructura de red"""
        self.logger.info("\n[FASE 1] Configurando red P2P...")
        
        # 1.1 Iniciar Bootstrap Node
        self.logger.info("Iniciando Bootstrap Node...")
        self.bootstrap_node = P2PNode(
            config.BOOTSTRAP_HOST,
            config.BOOTSTRAP_PORT,
            is_bootstrap=True
        )
        self.bootstrap_node.start()
        time.sleep(1)  # Esperar que socket esté listo
        
        # 1.2 Iniciar Nodos Legítimos
        self.logger.info(f"Iniciando {config.NUM_LEGITIMATE_NODES} nodos legítimos...")
        
        for i in range(config.NUM_LEGITIMATE_NODES):
            port = config.NODE_BASE_PORT + i
            node = P2PNode(config.BOOTSTRAP_HOST, port)
            node.start()
            self.legitimate_nodes.append(node)
            time.sleep(0.2)  # Evitar race conditions
        
        self.logger.info(f"✓ {len(self.legitimate_nodes)} nodos iniciados")
    
    def bootstrap_network(self):
        """Fase 2: Conectar nodos a la red"""
        self.logger.info("\n[FASE 2] Conectando nodos a la red...")
        
        for i, node in enumerate(self.legitimate_nodes):
            self.logger.info(f"Conectando nodo {i+1}/{len(self.legitimate_nodes)}...")
            node.join_network(config.BOOTSTRAP_HOST, config.BOOTSTRAP_PORT)
            time.sleep(0.5)  # Delay entre joins
        
        self.logger.info(" Todos los nodos conectados al bootstrap")
        
        # Esperar estabilización
        self.logger.info("Esperando estabilización de red (10s)...")
        time.sleep(10)
        
        self._print_network_status("RED ANTES DEL ATAQUE")
    
    def launch_attack(self):
        """Fase 3: Ejecutar ataque Sybil"""
        self.logger.warning("\n[FASE 3] LANZANDO ATAQUE SYBIL...")
        
        self.attacker = SybilNode(num_identities=config.SYBIL_IDENTITIES)
        self.attacker.generate_identities()
        
        time.sleep(config.ATTACK_DELAY)
        
        self.attacker.launch_attack(
            config.BOOTSTRAP_HOST,
            config.NODE_BASE_PORT,
            attack_all_nodes=True
        )
        
        # Esperar que conexiones se procesen
        time.sleep(5)
    
    def analyze_results(self):
        """Fase 4: Análisis post-ataque"""
        self.logger.info("\n[FASE 4] Analizando impacto del ataque...")
        
        self._print_network_status("RED DESPUÉS DEL ATAQUE")
        
        # Recolectar métricas
        metrics = self._collect_metrics()
        
        # Generar reporte
        self._generate_report(metrics)
    
    def _print_network_status(self, title: str):
        """Imprime estado actual de la red"""
        print(f"\n{'='*60}")
        print(f"{title:^60}")
        print(f"{'='*60}")
        
        # Bootstrap
        bootstrap_status = self.bootstrap_node.get_network_status()
        print(f"\n[BOOTSTRAP - Puerto {config.BOOTSTRAP_PORT}]")
        print(f"  Vecinos registrados: {bootstrap_status['neighbors']}/{bootstrap_status['max_neighbors']}")
        print(f"  Conexiones por IP: {bootstrap_status['connections_by_ip']}")
        print(f"  Msgs enviados: {bootstrap_status['stats']['messages_sent']}")
        print(f"  Msgs recibidos: {bootstrap_status['stats']['messages_received']}")
        print(f"  Conexiones rechazadas: {bootstrap_status['stats']['connections_rejected']}")
        print(f"  Sybil detectados: {bootstrap_status['stats']['sybil_detected']}")
        
        # Nodos legítimos
        print(f"\n[NODOS LEGÍTIMOS]")
        for i, node in enumerate(self.legitimate_nodes[:5]):  # Mostrar primeros 5
            status = node.get_network_status()
            print(f"  Nodo {i+1} (Puerto {status['port']}): "
                  f"{status['neighbors']}/{status['max_neighbors']} vecinos | "
                  f"Rechazados: {status['stats']['connections_rejected']}")
        
        if len(self.legitimate_nodes) > 5:
            print(f"  ... y {len(self.legitimate_nodes) - 5} nodos más")
        
        print(f"{'='*60}\n")
    
    def _collect_metrics(self) -> dict:
        """Recolecta métricas de toda la red"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'num_legitimate_nodes': config.NUM_LEGITIMATE_NODES,
                'sybil_identities': config.SYBIL_IDENTITIES,
                'max_neighbors': config.MAX_NEIGHBORS,
                'ip_limiting': config.ENABLE_IP_LIMITING,
                'reputation': config.ENABLE_REPUTATION,
                'pow': config.ENABLE_POW
            },
            'bootstrap': self.bootstrap_node.get_network_status(),
            'legitimate_nodes': [],
            'attack_stats': self.attacker.get_attack_stats() if self.attacker else {}
        }
        
        # Métricas agregadas de nodos legítimos
        total_neighbors = 0
        total_rejected = 0
        total_sybil_detected = 0
        
        for node in self.legitimate_nodes:
            status = node.get_network_status()
            metrics['legitimate_nodes'].append(status)
            total_neighbors += status['neighbors']
            total_rejected += status['stats']['connections_rejected']
            total_sybil_detected += status['stats']['sybil_detected']
        
        metrics['aggregated'] = {
            'avg_neighbors_per_node': total_neighbors / len(self.legitimate_nodes),
            'total_connections_rejected': total_rejected,
            'total_sybil_detected': total_sybil_detected,
            'network_saturation': (total_neighbors / (len(self.legitimate_nodes) * config.MAX_NEIGHBORS)) * 100
        }
        
        return metrics
    
    def _generate_report(self, metrics: dict):
        """Genera reporte técnico del experimento"""
        report = f"""
╔═══════════════════════════════════════════════════════════════════╗
║              REPORTE DE SIMULACIÓN - ATAQUE SYBIL                                                                                                          ║
╠═══════════════════════════════════════════════════════════════════╣
║  CONFIGURACIÓN                                                    ║
║    Nodos legítimos:           {metrics['config']['num_legitimate_nodes']:4d}                            ║
║    Identidades Sybil:         {metrics['config']['sybil_identities']:4d}                            ║
║    Max vecinos/nodo:          {metrics['config']['max_neighbors']:4d}                            ║
║    IP Limiting:               {'ACTIVO' if metrics['config']['ip_limiting'] else 'INACTIVO':6s}                        ║
║    Sistema Reputación:        {'ACTIVO' if metrics['config']['reputation'] else 'INACTIVO':6s}                        ║
║    Proof of Work:             {'ACTIVO' if metrics['config']['pow'] else 'INACTIVO':6s}                        ║
╠═══════════════════════════════════════════════════════════════════╣
║  RESULTADOS DEL ATAQUE                                            ║
║    Intentos de conexión:      {metrics['attack_stats']['total_identities']:4d}                            ║
║    Conexiones exitosas:       {metrics['attack_stats']['successful_connections']:4d} ({metrics['attack_stats']['success_rate']:5.1f}%)                   ║
║    Conexiones rechazadas:     {metrics['attack_stats']['rejected_connections']:4d} ({100 - metrics['attack_stats']['success_rate']:5.1f}%)                   ║
╠═══════════════════════════════════════════════════════════════════╣
║  IMPACTO EN LA RED                                                ║
║    Vecinos promedio/nodo:     {metrics['aggregated']['avg_neighbors_per_node']:5.2f}                           ║
║    Saturación de red:         {metrics['aggregated']['network_saturation']:5.1f}%                          ║
║    Sybil detectados:          {metrics['aggregated']['total_sybil_detected']:4d}                            ║
║    Conexiones rechazadas:     {metrics['aggregated']['total_connections_rejected']:4d}                            ║
╠═══════════════════════════════════════════════════════════════════╣
"""
        
        # Evaluación de efectividad de defensa
        if metrics['attack_stats']['success_rate'] < 10:
            verdict = "DEFENSA EFECTIVA - Ataque neutralizado"
        elif metrics['attack_stats']['success_rate'] < 30:
            verdict =   "DEFENSA PARCIAL - Mitigación moderada"
        else:
            verdict = " DEFENSA INSUFICIENTE - Red comprometida"
        
        report += f"║  VEREDICTO: {verdict:50s} ║\n"
        report += "╚═══════════════════════════════════════════════════════════════════╝"
        
        print(report)
        self.logger.info(report)
        
        # Guardar métricas a archivo JSON
        with open(f"{config.LOG_DIR}/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.logger.info("✓ Métricas guardadas en logs/metrics_*.json")
    
    def run_full_simulation(self):
        """Ejecuta simulación completa end-to-end"""
        try:
            self.setup_network()
            time.sleep(2)
            
            self.bootstrap_network()
            time.sleep(2)
            
            self.launch_attack()
            time.sleep(2)
            
            self.analyze_results()
            
            self.logger.info("\n SIMULACIÓN COMPLETADA")
        
        except KeyboardInterrupt:
            self.logger.warning("\n Simulación interrumpida por usuario")
        
        except Exception as e:
            self.logger.error(f"\n Error en simulación: {e}", exc_info=True)
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Limpia recursos y detiene todos los nodos"""
        self.logger.info("\nLimpiando recursos...")
        
        if self.bootstrap_node:
            self.bootstrap_node.stop()
        
        for node in self.legitimate_nodes:
            node.stop()
        
        self.logger.info("✓ Simulación finalizada correctamente")


def run_simulation():
    """Punto de entrada principal"""
    simulator = NetworkSimulator()
    simulator.run_full_simulation()


if __name__ == "__main__":
    run_simulation()
