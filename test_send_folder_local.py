import os
import time
import threading
from app_logic import PacketHandler
from network_core import NetworkAdapter, start_listener_thread
from utils import get_mac_address

if __name__ == "__main__":
    interface = "wlo1"
    folder = "CV"  # Cambia por la carpeta que quieras probar (debe existir)
    
    # Verificar que la carpeta existe
    if not os.path.exists(folder):
        print(f"❌ Error: La carpeta '{folder}' no existe")
        exit(1)
    
    # Obtén tu propia MAC
    my_mac = get_mac_address(interface)
    print(f"Enviando carpeta '{folder}' a mi propia MAC: {my_mac} usando interfaz {interface}")
    
    # Inicializa adaptador y handler
    adapter = NetworkAdapter(interface)
    handler = PacketHandler()
    handler.set_adapter(adapter)
    
    # CRÍTICO: Iniciar listener ANTES de enviar
    print("Iniciando listener...")
    listener_thread = start_listener_thread(adapter, handler.handle_packet)
    time.sleep(1)  # Dar tiempo al listener para arrancar
    
    # Lanza el envío
    print(f"\nIniciando envío de carpeta '{folder}'...\n")
    handler.send_folder(adapter, my_mac, folder)
    
    # CRÍTICO: Mantener el script vivo para que los hilos trabajen
    print("\nEsperando a que termine la transferencia...")
    print("(Presiona Ctrl+C para cancelar)\n")
    
    try:
        # Esperar indefinidamente (o hasta Ctrl+C)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nTransferencia cancelada por el usuario.")