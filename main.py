"""
Link-Chat - Aplicación de chat y transferencia de archivos en Capa 2
Programa principal
"""

import utils
import network_core
from app_logic import PacketHandler


def main():
    """
    Función principal de Link-Chat.
    
    Inicializa el adaptador de red, el manejador de paquetes y el listener,
    luego proporciona una interfaz de consola para interactuar con la aplicación.
    """
    print("=== Link-Chat - Chat en Capa 2 ===")
    print("Inicializando...\n")
    
    try:
        # Buscar una interfaz de red adecuada (excluyendo loopback)
        interface = utils.find_network_interface()
        print(f"✓ Interfaz de red encontrada: {interface}")
        
        # Crear el adaptador de red con la interfaz encontrada
        # NOTA: Requiere privilegios de root/sudo para crear raw sockets
        adapter = network_core.NetworkAdapter(interface)
        print(f"✓ Adaptador de red inicializado")
        print(f"  Dirección MAC local: {adapter.src_mac}")
        
        # Crear el manejador de paquetes
        handler = PacketHandler()
        print(f"✓ Manejador de paquetes creado")
        
        # Iniciar el hilo listener que escuchará tramas entrantes
        # El listener ejecutará handler.handle_packet() para cada paquete recibido
        listener_thread = network_core.start_listener_thread(adapter, handler.handle_packet)
        print(f"✓ Listener iniciado en segundo plano\n")
        
        print("Link-Chat está listo para usar.")
        print("Comandos disponibles:")
        print("  - exit: Salir de la aplicación")
        print("  (Más comandos se añadirán próximamente)\n")
        
        # Bucle principal de la interfaz de consola
        while True:
            try:
                # Leer comando del usuario
                command = input("> ").strip()
                
                # Procesar comandos
                if command == 'exit':
                    print("\nCerrando Link-Chat...")
                    break
                elif command == '':
                    # Ignorar líneas vacías
                    continue
                else:
                    print(f"Comando no reconocido: '{command}'")
                    print("Usa 'exit' para salir.")
            
            except KeyboardInterrupt:
                # Manejar Ctrl+C
                print("\n\nInterrumpido por el usuario.")
                print("Cerrando Link-Chat...")
                break
    
    except IOError as e:
        print(f"✗ Error de red: {e}")
        print("Asegúrate de que hay interfaces de red disponibles.")
    except PermissionError as e:
        print(f"✗ Error de permisos: {e}")
        print("Este programa requiere privilegios de superusuario (root).")
        print("Ejecuta con: sudo python3 main.py")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    print("Link-Chat finalizado.")


if __name__ == "__main__":
    main()
