#!/usr/bin/env python3
"""
SIMULACIÓN DE ATAQUE SYBIL EN RED P2P
Script principal de ejecución

Uso:
    python main.py [--mode MODE] [--nodes N] [--sybil S]
    
Modos:
    normal:     Simulación completa con defensa
    no-defense: Simulación SIN defensas (máximo impacto)
    stealth:    Ataque sigiloso con rate limiting
"""

import sys
import argparse
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

import config
from simulation.simulator import NetworkSimulator


def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Simulación de Ataque Sybil en Red P2P',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--mode',
        choices=['normal', 'no-defense', 'stealth'],
        default='normal',
        help='Modo de simulación (default: normal)'
    )
    
    parser.add_argument(
        '--nodes',
        type=int,
        default=config.NUM_LEGITIMATE_NODES,
        help=f'Número de nodos legítimos (default: {config.NUM_LEGITIMATE_NODES})'
    )
    
    parser.add_argument(
        '--sybil',
        type=int,
        default=config.SYBIL_IDENTITIES,
        help=f'Número de identidades Sybil (default: {config.SYBIL_IDENTITIES})'
    )
    
    parser.add_argument(
        '--max-neighbors',
        type=int,
        default=config.MAX_NEIGHBORS,
        help=f'Máximo de vecinos por nodo (default: {config.MAX_NEIGHBORS})'
    )
    
    parser.add_argument(
        '--enable-pow',
        action='store_true',
        help='Activar Proof of Work (ADVERTENCIA: muy lento)'
    )
    
    return parser.parse_args()


def configure_simulation(args):
    """Configura parámetros según modo de simulación"""
    
    # Aplicar argumentos
    config.NUM_LEGITIMATE_NODES = args.nodes
    config.SYBIL_IDENTITIES = args.sybil
    config.MAX_NEIGHBORS = args.max_neighbors
    
    if args.mode == 'no-defense':
        print("\n  MODO SIN DEFENSA - Demostrando máximo impacto del ataque\n")
        config.ENABLE_IP_LIMITING = False
        config.ENABLE_REPUTATION = False
        config.ENABLE_POW = False
    
    elif args.mode == 'stealth':
        print("\n  MODO SIGILOSO - Ataque con rate limiting\n")
        config.ATTACK_DELAY = 5
    
    elif args.mode == 'normal':
        print("\n MODO NORMAL - Defensas activadas\n")
        config.ENABLE_IP_LIMITING = True
        config.ENABLE_REPUTATION = True
    
    if args.enable_pow:
        print("Proof of Work ACTIVADO (esto será LENTO)\n")
        config.ENABLE_POW = True


def print_banner():
    """Imprime banner de bienvenida"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                                                                                                                                              ║
║     SIMULADOR DE ATAQUE SYBIL EN SISTEMAS P2P                                                                                                         ║
║                                                                                                                                                                                              ║
║     Proyecto: Sistemas Distribuidos                                                                                                                          ║
║     Temática: Paso de Mensajes y Seguridad en Redes P2P                                                                                       ║
║                                                                                                                                                                                              ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Función principal"""
    print_banner()
    
    args = parse_arguments()
    configure_simulation(args)
    
    # Crear directorio de logs
    Path(config.LOG_DIR).mkdir(exist_ok=True)
    
    # Ejecutar simulación
    simulator = NetworkSimulator()
    simulator.run_full_simulation()


if __name__ == "__main__":
    main()
