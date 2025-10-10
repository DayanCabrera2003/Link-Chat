"""
Link-Chat - Aplicación de chat y transferencia de archivos en Capa 2
Programa principal con configuración automática de red
"""

import config
import utils
import network_core
import protocol
from app_logic import PacketHandler
import subprocess
import sys
import os
import socket
import time
import threading


def run_command(cmd, check=False):
    """Ejecuta un comando del sistema y retorna el output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, stderr=subprocess.DEVNULL)
        if check and result.returncode != 0:
            return None
        return result.stdout
    except:
        return None


def find_and_setup_ethernet():
    """
    Encuentra y configura automáticamente una interfaz Ethernet.
    Si no hay Ethernet, usa WiFi como fallback.
    
    Returns:
        tuple: (interface_name, is_ethernet, warnings)
    """
    warnings = []
    
    print("🔍 Buscando interfaces de red...")
    
    # Obtener todas las interfaces
    interfaces = socket.if_nameindex()
    ethernet_interfaces = []
    wifi_interfaces = []
    
    for idx, name in interfaces:
        # Ignorar loopback, docker, proton, vpn
        if any(x in name.lower() for x in ['lo', 'docker', 'proton', 'ipv6', 'tun', 'tap']):
            continue
        
        # Clasificar por tipo
        if any(x in name.lower() for x in ['wl', 'wifi', 'wlan']):
            wifi_interfaces.append(name)
        else:
            ethernet_interfaces.append(name)
    
    # Prioridad: Ethernet > WiFi
    target_interface = None
    is_ethernet = False
    
    if ethernet_interfaces:
        print(f"✓ Interfaces Ethernet encontradas: {', '.join(ethernet_interfaces)}")
        target_interface = ethernet_interfaces[0]
        is_ethernet = True
    elif wifi_interfaces:
        print(f"⚠ No se encontró Ethernet, usando WiFi: {wifi_interfaces[0]}")
        warnings.append("⚠ ADVERTENCIA: Usando WiFi en lugar de Ethernet")
        warnings.append("  El broadcast de capa 2 puede no funcionar correctamente")
        warnings.append("  RECOMENDACIÓN: Conecta un cable Ethernet para mejor rendimiento")
        target_interface = wifi_interfaces[0]
        is_ethernet = False
    else:
        raise IOError("No se encontraron interfaces de red válidas")
    
    # Verificar y activar la interfaz si está DOWN
    print(f"\n🔧 Configurando interfaz: {target_interface}")
    
    status_output = run_command(f"ip link show {target_interface}")
    
    if status_output and 'state DOWN' in status_output:
        print(f"  └─ Interfaz está DOWN, activando...")
        run_command(f"ip link set {target_interface} up")
        
        time.sleep(2)
        
        # Verificar nuevamente
        status_output = run_command(f"ip link show {target_interface}")
        if status_output and 'state UP' in status_output:
            print(f"  └─ ✓ Interfaz activada correctamente")
        else:
            warnings.append(f"⚠ No se pudo activar la interfaz {target_interface}")
    elif status_output and 'state UP' in status_output:
        print(f"  └─ ✓ Interfaz ya está activa")
    
    # Si es Ethernet, verificar link físico
    if is_ethernet:
        link_output = run_command(f"ethtool {target_interface}")
        if link_output:
            if 'Link detected: yes' in link_output:
                print(f"  └─ ✓ Cable Ethernet conectado")
                
                # Mostrar velocidad si está disponible
                for line in link_output.split('\n'):
                    if 'Speed:' in line:
                        speed = line.split(':')[1].strip()
                        print(f"      └─ Velocidad: {speed}")
                        break
            elif 'Link detected: no' in link_output:
                warnings.append("⚠ ADVERTENCIA: Cable Ethernet desconectado")
                warnings.append("  Verifica que el cable esté bien conectado")
    
    # Verificar si tiene IP configurada (solo informativo, NO es necesario para Capa 2)
    addr_output = run_command(f"ip addr show {target_interface}")
    has_ip = addr_output and 'inet ' in addr_output
    
    if has_ip:
        print(f"  └─ ℹ️  Interfaz tiene IP configurada (no necesario para Link-Chat)")
    else:
        print(f"  └─ ℹ️  Interfaz sin IP (normal para comunicación pura de Capa 2)")
    
    return target_interface, is_ethernet, warnings


def check_firewall():
    """Verifica y advierte sobre firewall activo"""
    result = run_command("ufw status")
    
    if result and 'Status: active' in result:
        return [
            "⚠ ADVERTENCIA: Firewall UFW está activo",
            "  Esto puede bloquear paquetes de Link-Chat",
            "  Si tienes problemas de conexión, desactívalo con: sudo ufw disable"
        ]
    
    return []


def main():
    """
    Función principal de Link-Chat con configuración automática.
    """
    print("=" * 70)
    print("         💬 Link-Chat - Chat en Capa 2")
    print("=" * 70)
    print()
    
    # Verificar permisos de root
    if os.geteuid() != 0:
        print("❌ ERROR: Este programa requiere privilegios de root para usar sockets crudos.")
        print("   Por favor, ejecútalo con 'sudo python3 main.py'")
        return
    
    all_warnings = []
    
    try:
        # 1. Configuración de red
        # ========================
        target_interface, is_ethernet, net_warnings = find_and_setup_ethernet()
        all_warnings.extend(net_warnings)
        
        # 2. Verificación de Firewall
        # ===========================
        fw_warnings = check_firewall()
        all_warnings.extend(fw_warnings)
        
        # 3. Inicialización del Adaptador de Red
        # ======================================
        print(f"\n🚀 Inicializando en interfaz: {target_interface}")
        adapter = network_core.NetworkAdapter(target_interface)
        print(f"  └─ MAC de origen: {adapter.src_mac}")
        
        # 4. Configuración del Manejador de Paquetes
        # ==========================================
        packet_handler = PacketHandler()
        packet_handler.set_adapter(adapter)
        
        # 5. Inicio del Hilo Listener
        # ===========================
        network_core.start_listener_thread(adapter, packet_handler.handle_packet)
        print("  └─ Escuchando en segundo plano...")
        
        # 6. Configuración del nombre de usuario
        # ======================================
        username = input("\n👤 Ingresa tu nombre de usuario: ").strip()
        while not username:
            username = input("👤 El nombre no puede estar vacío. Ingresa tu nombre: ").strip()
        packet_handler.set_username(username)
        print(f"¡Hola, {username}!")
        
        # Mostrar advertencias si las hay
        if all_warnings:
            print("\n" + "="*30 + " AVISOS " + "="*30)
            for warning in all_warnings:
                print(warning)
            print("=" * 70)
        
        # 7. Bucle Principal de Comandos
        # ==============================
        print("\n✅ Sistema listo. Escribe 'help' para ver los comandos.")
        
        while True:
            try:
                # Leer comando del usuario
                user_input = input(f"[{username}]> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split()
                command = parts[0].lower()
                
                # Procesar comandos
                if command == "exit":
                    break
                
                elif command == "help":
                    print("\nComandos disponibles:")
                    print("  send <MAC_destino> <mensaje>   - Envía un mensaje a una MAC específica")
                    print("  broadcast <mensaje>            - Envía un mensaje a todos en la red")
                    print("  file <MAC_destino> <ruta_archivo> - Envía un archivo a una MAC")
                    print("  discover                       - Busca otros usuarios en la red")
                    print("  exit                           - Cierra la aplicación")
                
                elif command == "send":
                    if len(parts) < 3:
                        print("❌ Uso: send <MAC_destino> <mensaje>")
                        continue
                    
                    dest_mac = parts[1]
                    message = ' '.join(parts[2:])
                    
                    # Crear cabecera y payload
                    payload = message.encode('utf-8')
                    header = protocol.LinkChatHeader.pack(protocol.PacketType.TEXT, len(payload))
                    
                    # Enviar trama
                    print(f"-> Enviando a {dest_mac}...")
                    adapter.send_frame(dest_mac, header + payload)
                
                elif command == "broadcast":
                    if len(parts) < 2:
                        print("❌ Uso: broadcast <mensaje>")
                        continue
                    
                    message = ' '.join(parts[1:])
                    
                    # Crear cabecera y payload
                    payload = message.encode('utf-8')
                    header = protocol.LinkChatHeader.pack(protocol.PacketType.TEXT, len(payload))
                    
                    # Enviar trama a la dirección de broadcast
                    print("-> Enviando a todos (broadcast)...")
                    adapter.send_frame(config.BROADCAST_MAC, header + payload)
                
                elif command == "file":
                    if len(parts) != 3:
                        print("❌ Uso: file <MAC_destino> <ruta_archivo>")
                        continue
                    
                    dest_mac = parts[1]
                    filepath = parts[2]
                    
                    if not os.path.exists(filepath):
                        print(f"❌ Error: El archivo '{filepath}' no existe.")
                        continue
                    
                    # Iniciar transferencia de archivo (se ejecuta en segundo plano)
                    # La lógica está en app_logic.py
                    thread = threading.Thread(target=packet_handler.send_file, args=(adapter, dest_mac, filepath))
                    thread.start()
                
                elif command == "discover":
                    # Crear cabecera (sin payload)
                    header = protocol.LinkChatHeader.pack(protocol.PacketType.DISCOVERY_REQUEST, 0)
                    
                    # Enviar trama de descubrimiento a broadcast
                    print("-> Buscando otros usuarios en la red...")
                    adapter.send_frame(config.BROADCAST_MAC, header)
                
                else:
                    print(f"❌ Comando '{command}' no reconocido. Escribe 'help' para ayuda.")
            
            except KeyboardInterrupt:
                # Capturar Ctrl+C en el bucle de comandos para salir limpiamente
                print("\nDetectado Ctrl+C. Saliendo...")
                break
            
            except Exception as e:
                # Capturar otros errores inesperados en el bucle
                print(f"🔥 Error inesperado en el bucle de comandos: {e}")
                print("   Continuando ejecución...")
    
    except IOError as e:
        print(f"\n❌ ERROR DE RED: {e}")
        print("   Asegúrate de que la interfaz de red está conectada y activa.")
    except PermissionError as e:
        print(f"\n❌ ERROR DE PERMISOS: {e}")
        print("   Este programa debe ejecutarse con privilegios de root (sudo).")
    except Exception as e:
        print(f"\n🔥 ERROR INESPERADO: {e}")
        print("   Ocurrió un error fatal. Revisa la traza para más detalles.")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Link-Chat finalizado.")


if __name__ == "__main__":
    main()
