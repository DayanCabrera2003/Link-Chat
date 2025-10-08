"""
Link-Chat - Aplicación de chat y transferencia de archivos en Capa 2
Programa principal
"""

import config
import utils
import network_core
import protocol
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
        print("  - discover: Descubrir dispositivos en la red local")
        print("  - send <dest_mac> <mensaje>: Enviar mensaje a una MAC específica")
        print("  - sendfile <dest_mac> <filepath>: Enviar archivo a una MAC específica")
        print("  - exit: Salir de la aplicación")
        print("\nEjemplos:")
        print("  discover")
        print("  send ff:ff:ff:ff:ff:ff Hola a todos!")
        print("  send 08:00:27:7d:2b:8c Hola específico")
        print("  sendfile ff:ff:ff:ff:ff:ff /path/to/file.txt\n")
        
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
                elif command == 'discover':
                    # Comando de descubrimiento de dispositivos en la red
                    try:
                        # Pedir al usuario su nombre de usuario
                        username = input("Ingresa tu nombre de usuario: ").strip()
                        
                        if not username:
                            print("Error: El nombre de usuario no puede estar vacío.")
                            continue
                        
                        # Codificar el nombre de usuario a bytes
                        username_bytes = username.encode('utf-8')
                        
                        # Crear la cabecera Link-Chat para DISCOVERY_REQUEST
                        discovery_header = protocol.LinkChatHeader.pack(
                            protocol.PacketType.DISCOVERY_REQUEST,
                            len(username_bytes)
                        )
                        
                        # Construir el payload completo: cabecera + nombre de usuario
                        discovery_payload = discovery_header + username_bytes
                        
                        # Enviar broadcast a todas las máquinas en la red local
                        adapter.send_frame(config.BROADCAST_MAC, discovery_payload)
                        
                        print(f"✓ Solicitud de descubrimiento enviada como '{username}' a la red")
                        print("  Esperando respuestas...\n")
                    
                    except Exception as e:
                        print(f"✗ Error al enviar solicitud de descubrimiento: {e}")
                
                elif command.startswith('send '):
                    # Parsear el comando 'send <dest_mac> <mensaje>'
                    # Formato: send ff:ff:ff:ff:ff:ff Mensaje de prueba
                    parts = command.split(None, 2)  # Dividir en máximo 3 partes
                    
                    if len(parts) < 3:
                        print("Error: Formato incorrecto.")
                        print("Uso: send <dest_mac> <mensaje>")
                        print("Ejemplo: send ff:ff:ff:ff:ff:ff Hola!")
                        continue
                    
                    # Extraer MAC de destino y mensaje
                    dest_mac = parts[1]
                    message = parts[2]
                    
                    # Validar formato básico de MAC (xx:xx:xx:xx:xx:xx)
                    if len(dest_mac) != 17 or dest_mac.count(':') != 5:
                        print(f"Error: MAC inválida '{dest_mac}'")
                        print("Formato esperado: xx:xx:xx:xx:xx:xx")
                        continue
                    
                    try:
                        # Codificar el mensaje a bytes UTF-8
                        message_bytes = message.encode('utf-8')
                        
                        # Crear la cabecera Link-Chat
                        # PacketType.TEXT indica que es un mensaje de texto
                        # len(message_bytes) especifica la longitud del payload
                        header = protocol.LinkChatHeader.pack(
                            protocol.PacketType.TEXT,
                            len(message_bytes)
                        )
                        
                        # Construir el payload completo: cabecera + mensaje
                        full_payload = header + message_bytes
                        
                        # Enviar la trama Ethernet con el payload
                        adapter.send_frame(dest_mac, full_payload)
                        
                        print(f"✓ Mensaje enviado a [{dest_mac}]")
                    
                    except Exception as e:
                        print(f"✗ Error al enviar mensaje: {e}")
                
                elif command.startswith('sendfile '):
                    # Parsear el comando 'sendfile <dest_mac> <filepath>'
                    # Formato: sendfile ff:ff:ff:ff:ff:ff /path/to/file.txt
                    parts = command.split(None, 2)  # Dividir en máximo 3 partes
                    
                    if len(parts) < 3:
                        print("Error: Formato incorrecto.")
                        print("Uso: sendfile <dest_mac> <filepath>")
                        print("Ejemplo: sendfile ff:ff:ff:ff:ff:ff /home/user/documento.pdf")
                        continue
                    
                    # Extraer MAC de destino y ruta del archivo
                    dest_mac = parts[1]
                    filepath = parts[2]
                    
                    # Validar formato básico de MAC (xx:xx:xx:xx:xx:xx)
                    if len(dest_mac) != 17 or dest_mac.count(':') != 5:
                        print(f"Error: MAC inválida '{dest_mac}'")
                        print("Formato esperado: xx:xx:xx:xx:xx:xx")
                        continue
                    
                    try:
                        # Llamar al método send_file del handler
                        print(f"\nIniciando transferencia de archivo...")
                        handler.send_file(adapter, dest_mac, filepath)
                        print(f"✓ Transferencia completada exitosamente.\n")
                    
                    except FileNotFoundError as e:
                        print(f"✗ Error: {e}")
                    except Exception as e:
                        print(f"✗ Error al enviar archivo: {e}")
                        import traceback
                        traceback.print_exc()
                
                else:
                    print(f"Comando no reconocido: '{command}'")
                    print("Comandos disponibles: discover, send, sendfile, exit")
            
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
