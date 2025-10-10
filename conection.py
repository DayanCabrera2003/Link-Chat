#!/usr/bin/env python3
"""Script de prueba para Link-Chat"""

import subprocess
import sys
import time

def test_interface(interface):
    """Verifica que la interfaz esté configurada correctamente"""
    print(f"🔍 Verificando interfaz {interface}...")
    
    # Verificar que existe
    result = subprocess.run(
        f"ip link show {interface}",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Interfaz {interface} no encontrada")
        return False
    
    # Verificar que está UP
    if 'state UP' in result.stdout:
        print(f"✓ Interfaz {interface} está UP")
    else:
        print(f"⚠ Interfaz {interface} está DOWN, intentando activar...")
        subprocess.run(f"sudo ip link set {interface} up", shell=True)
        time.sleep(2)
    
    # Mostrar MAC
    with open(f'/sys/class/net/{interface}/address') as f:
        mac = f.read().strip()
    print(f"✓ MAC address: {mac}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: sudo python3 test_connection.py <interfaz>")
        print("Ejemplo: sudo python3 test_connection.py eth0")
        sys.exit(1)
    
    interface = sys.argv[1]
    
    if test_interface(interface):
        print("\n✅ Interfaz lista para usar con Link-Chat")
        print(f"Ejecuta: sudo python3 main.py")
    else:
        print("\n❌ La interfaz no está lista")
        sys.exit(1)