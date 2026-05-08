#!/usr/bin/env python3
"""
Analizador de Métricas de Simulación
Genera gráficos comparativos y estadísticas detalladas
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_metrics(filepath: str) -> dict:
    """Carga archivo de métricas JSON"""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_simulations(metrics_with_defense: dict, metrics_without_defense: dict):
    """Compara dos simulaciones y genera reporte"""
    
    print("\n" + "="*70)
    print(" ANÁLISIS COMPARATIVO: CON vs SIN DEFENSA ".center(70))
    print("="*70 + "\n")
    
    # Extraer datos
    with_def = metrics_with_defense['attack_stats']
    without_def = metrics_without_defense['attack_stats']
    
    agg_with = metrics_with_defense['aggregated']
    agg_without = metrics_without_defense['aggregated']
    
    # Tabla comparativa
    print(f"{'MÉTRICA':<40} {'SIN DEFENSA':>12} {'CON DEFENSA':>12} {'MEJORA':>10}")
    print("-" * 70)
    
    # Tasa de éxito del ataque
    success_without = without_def['success_rate']
    success_with = with_def['success_rate']
    improvement = success_without - success_with
    
    print(f"{'Tasa de éxito Sybil (%)':<40} {success_without:>11.1f}% {success_with:>11.1f}% {improvement:>9.1f}%")
    
    # Conexiones aceptadas
    accepted_without = without_def['successful_connections']
    accepted_with = with_def['successful_connections']
    
    print(f"{'Conexiones Sybil aceptadas':<40} {accepted_without:>12d} {accepted_with:>12d} {accepted_without-accepted_with:>10d}")
    
    # Saturación de red
    sat_without = agg_without['network_saturation']
    sat_with = agg_with['network_saturation']
    
    print(f"{'Saturación de red (%)':<40} {sat_without:>11.1f}% {sat_with:>11.1f}% {sat_without-sat_with:>9.1f}%")
    
    # Sybil detectados
    detected_without = agg_without['total_sybil_detected']
    detected_with = agg_with['total_sybil_detected']
    
    print(f"{'Identidades Sybil detectadas':<40} {detected_without:>12d} {detected_with:>12d} {detected_with-detected_without:>10d}")
    
    print("\n" + "="*70)
    
    # Veredicto
    if improvement > 50:
        verdict = " DEFENSA MUY EFECTIVA - Reducción >50%"
    elif improvement > 30:
        verdict = "  DEFENSA MODERADA - Reducción 30-50%"
    else:
        verdict = " DEFENSA INSUFICIENTE - Reducción <30%"
    
    print(f"\nVEREDICTO: {verdict}\n")
    
    # Análisis detallado
    print("ANÁLISIS:")
    print(f"  • El ataque pasó de {success_without:.1f}% a {success_with:.1f}% de éxito")
    print(f"  • Se bloquearon {improvement:.1f} puntos porcentuales de conexiones maliciosas")
    print(f"  • La saturación de red se redujo en {sat_without - sat_with:.1f}%")
    print(f"  • Se detectaron {detected_with} identidades Sybil adicionales\n")


def analyze_single_simulation(metrics: dict):
    """Analiza una simulación individual"""
    
    print("\n" + "="*70)
    print(" ANÁLISIS DE SIMULACIÓN ".center(70))
    print("="*70 + "\n")
    
    config = metrics['config']
    attack = metrics['attack_stats']
    agg = metrics['aggregated']
    
    print("CONFIGURACIÓN:")
    print(f"  • Nodos legítimos: {config['num_legitimate_nodes']}")
    print(f"  • Identidades Sybil: {config['sybil_identities']}")
    print(f"  • Max vecinos/nodo: {config['max_neighbors']}")
    print(f"  • Defensas activas:")
    print(f"    - IP Limiting: {'✓' if config['ip_limiting'] else '✗'}")
    print(f"    - Reputación: {'✓' if config['reputation'] else '✗'}")
    print(f"    - Proof of Work: {'✓' if config['pow'] else '✗'}")
    
    print(f"\nRESULTADOS DEL ATAQUE:")
    print(f"  • Intentos totales: {attack['total_identities']}")
    print(f"  • Conexiones exitosas: {attack['successful_connections']} ({attack['success_rate']:.1f}%)")
    print(f"  • Conexiones rechazadas: {attack['rejected_connections']} ({100 - attack['success_rate']:.1f}%)")
    
    print(f"\nIMPACTO EN LA RED:")
    print(f"  • Saturación: {agg['network_saturation']:.1f}%")
    print(f"  • Vecinos promedio: {agg['avg_neighbors_per_node']:.2f}")
    print(f"  • Sybil detectados: {agg['total_sybil_detected']}")
    print(f"  • Total rechazado: {agg['total_connections_rejected']}")
    
    print("\n" + "="*70 + "\n")


def main():
    """Función principal"""
    
    # Buscar archivos de métricas
    log_dir = Path('logs')
    
    if not log_dir.exists():
        print(" No se encontró directorio 'logs/'")
        print("   Ejecuta primero: python main.py")
        return
    
    metric_files = sorted(log_dir.glob('metrics_*.json'))
    
    if not metric_files:
        print(" No se encontraron archivos de métricas")
        print("   Ejecuta primero: python main.py")
        return
    
    print(f"\nEncontrados {len(metric_files)} archivos de métricas:\n")
    for i, f in enumerate(metric_files, 1):
        print(f"  {i}. {f.name}")
    
    # Analizar último archivo
    latest = metric_files[-1]
    print(f"\n Analizando: {latest.name}\n")
    
    metrics = load_metrics(latest)
    analyze_single_simulation(metrics)
    
    # Si hay múltiples archivos, ofrecer comparación
    if len(metric_files) >= 2:
        print("\n Tienes múltiples simulaciones. Para comparar:")
        print(f"   python {sys.argv[0]} compare <archivo1> <archivo2>")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == 'compare':
        # Modo comparación
        m1 = load_metrics(sys.argv[2])
        m2 = load_metrics(sys.argv[3])
        compare_simulations(m1, m2)
    else:
        main()
