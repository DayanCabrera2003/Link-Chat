"""
Diagnóstico especializado para Link-Chat con cable Ethernet
Detecta problemas específicos de comunicación entre dos laptops
"""

import socket
import struct
import time
import sys

# Importar módulos de Link-Chat
import config
import utils
import protocol


class Colors:
    """Códigos de color ANSI para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.RESET}")
    print("=" * 70 + "\n")


def print_test(text):
    """Imprime el nombre de una prueba"""
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {text}")


def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    """Imprime mensaje de error"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    """Imprime mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text):
    """Imprime mensaje informativo"""
    print(f"{Colors.WHITE}ℹ {text}{Colors.RESET}")


def test_interface_cable_ethernet():
    """Verifica que la interfaz sea Ethernet (no WiFi)"""
    print_header("1. VERIFICACIÓN DE INTERFAZ ETHERNET")
    
    try:
        interface = utils.find_network_interface()
        print_info(f"Interfaz detectada: {interface}")
        
        # Verificar si es WiFi
        is_wifi = any(x in interface.lower() for x in ['wl', 'wifi', 'wlan'])
        
        if is_wifi:
            print_warning(f"La interfaz '{interface}' parece ser WiFi")
            print_warning("WiFi puede tener problemas con broadcast de capa 2")
            print_info("Recomendación: Usa cable Ethernet (eth0, enp3s0, etc.)")
            return False
        else:
            print_success(f"Interfaz Ethernet detectada: {interface}")
            
            # Verificar que esté UP
            import subprocess
            result = subprocess.run(['ip', 'link', 'show', interface], 
                                  capture_output=True, text=True)
            
            if 'state UP' in result.stdout:
                print_success("Interfaz está UP (activa)")
                return True
            else:
                print_error("Interfaz está DOWN (inactiva)")
                print_info("Ejecuta: sudo ip link set <interfaz> up")
                return False
    
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_ethernet_link():
    """Verifica que el cable ethernet tenga link"""
    print_header("2. VERIFICACIÓN DE ENLACE FÍSICO")
    
    try:
        interface = utils.find_network_interface()
        
        import subprocess
        result = subprocess.run(['ethtool', interface], 
                              capture_output=True, text=True, 
                              stderr=subprocess.DEVNULL)
        
        if result.returncode == 0:
            if 'Link detected: yes' in result.stdout:
                print_success("Cable ethernet conectado (link detectado)")
                
                # Obtener velocidad
                for line in result.stdout.split('\n'):
                    if 'Speed:' in line:
                        print_info(f"  {line.strip()}")
                    if 'Duplex:' in line:
                        print_info(f"  {line.strip()}")
                
                return True
            else:
                print_error("Cable ethernet NO conectado")
                print_info("Verifica:")
                print_info("  1. El cable está bien conectado en ambas laptops")
                print_info("  2. El cable no está dañado")
                print_info("  3. Los puertos ethernet funcionan")
                return False
        else:
            print_warning("ethtool no disponible, saltando verificación de link")
            print_info("Instala ethtool: sudo apt install ethtool")
            return True  # Asumimos que está bien
    
    except Exception as e:
        print_warning(f"No se pudo verificar link físico: {e}")
        print_info("Continuando sin esta verificación...")
        return True


def test_send_receive_pattern():
    """Prueba envío/recepción con patrón específico"""
    print_header("3. PRUEBA DE ENVÍO/RECEPCIÓN")
    
    print_info("Esta prueba requiere coordinación entre las dos laptops")
    print_info("Sigue las instrucciones cuidadosamente\n")
    
    try:
        interface = utils.find_network_interface()
        src_mac = utils.get_mac_address()
        
        print_info(f"Tu MAC: {src_mac}")
        print_info(f"Tu interfaz: {interface}\n")
        
        # Preguntar modo
        print("¿Qué rol tendrá esta laptop?")
        print("  [1] EMISOR - Enviará un mensaje de prueba")
        print("  [2] RECEPTOR - Esperará recibir un mensaje")
        
        choice = input("\nElige (1 o 2): ").strip()
        
        if choice == '1':
            # MODO EMISOR
            print("\n" + Colors.CYAN + "=== MODO EMISOR ===" + Colors.RESET)
            
            dest_mac = input("\nIngresa la MAC de la otra laptop: ").strip()
            
            if len(dest_mac) != 17 or dest_mac.count(':') != 5:
                print_error("MAC inválida")
                return False
            
            # Crear socket
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, 
                               socket.htons(config.ETHTYPE_CUSTOM))
            sock.bind((interface, 0))
            
            # Preparar mensaje
            test_message = f"ETHERNET_TEST_FROM_{src_mac}"
            message_bytes = test_message.encode('utf-8')
            
            # Crear cabecera Link-Chat
            header = protocol.LinkChatHeader.pack(protocol.PacketType.TEXT, 
                                                 len(message_bytes))
            payload = header + message_bytes
            
            # Construir trama Ethernet
            dest_mac_bytes = bytes.fromhex(dest_mac.replace(':', ''))
            src_mac_bytes = bytes.fromhex(src_mac.replace(':', ''))
            eth_header = struct.pack('!6s6sH', dest_mac_bytes, src_mac_bytes, 
                                    config.ETHTYPE_CUSTOM)
            frame = eth_header + payload
            
            print_info(f"\nEnviando mensaje de prueba...")
            print_info(f"  De: {src_mac}")
            print_info(f"  A: {dest_mac}")
            print_info(f"  Tamaño: {len(frame)} bytes")
            
            # Enviar 3 veces para asegurar
            for i in range(3):
                sock.send(frame)
                print_success(f"Paquete #{i+1} enviado")
                time.sleep(0.5)
            
            sock.close()
            
            print_success("\n✓ Envío completado")
            print_info("Verifica en la otra laptop si recibió el mensaje")
            return True
        
        elif choice == '2':
            # MODO RECEPTOR
            print("\n" + Colors.CYAN + "=== MODO RECEPTOR ===" + Colors.RESET)
            
            # Crear socket
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, 
                               socket.htons(config.ETHTYPE_CUSTOM))
            sock.bind((interface, 0))
            sock.settimeout(30.0)
            
            print_info("\nEsperando mensajes por 30 segundos...")
            print_info("(En la otra laptop, ejecuta el modo EMISOR ahora)")
            print()
            
            received_count = 0
            start_time = time.time()
            
            while time.time() - start_time < 30.0:
                try:
                    packet, addr = sock.recvfrom(65535)
                    
                    # Desempaquetar Ethernet
                    eth_header_size = 14
                    eth_header = packet[:eth_header_size]
                    dest_mac_bytes, src_mac_bytes, ethertype = struct.unpack(
                        '!6s6sH', eth_header)
                    
                    src_mac_recv = ':'.join(f'{b:02x}' for b in src_mac_bytes)
                    
                    # Verificar EtherType
                    if ethertype == config.ETHTYPE_CUSTOM:
                        received_count += 1
                        
                        # Extraer payload
                        payload = packet[eth_header_size:]
                        
                        if len(payload) >= protocol.LinkChatHeader.HEADER_SIZE:
                            header_bytes = payload[:protocol.LinkChatHeader.HEADER_SIZE]
                            pkt_type, payload_len = protocol.LinkChatHeader.unpack(header_bytes)
                            content = payload[protocol.LinkChatHeader.HEADER_SIZE:]
                            
                            try:
                                message = content.decode('utf-8')
                                print_success(f"✓ Mensaje recibido de [{src_mac_recv}]:")
                                print_info(f"  Contenido: {message}")
                            except:
                                print_success(f"✓ Paquete recibido de [{src_mac_recv}] ({len(payload)} bytes)")
                
                except socket.timeout:
                    break
            
            sock.close()
            
            if received_count > 0:
                print_success(f"\n✓✓✓ ÉXITO: Recibidos {received_count} paquetes")
                print_success("La comunicación por cable ethernet FUNCIONA correctamente")
                return True
            else:
                print_error("\n✗ No se recibió ningún paquete en 30 segundos")
                print_warning("\nPosibles causas:")
                print_info("  1. La otra laptop no envió correctamente")
                print_info("  2. Cable ethernet desconectado o dañado")
                print_info("  3. Firewall bloqueando paquetes (desactiva temporalmente)")
                print_info("  4. Las laptops no están en el mismo segmento de red")
                return False
        
        else:
            print_error("Opción inválida")
            return False
    
    except PermissionError:
        print_error("Permisos insuficientes")
        print_info("Ejecuta con: sudo python3 ethernet_diagnostic.py")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_firewall():
    """Verifica estado del firewall"""
    print_header("4. VERIFICACIÓN DE FIREWALL")
    
    try:
        import subprocess
        
        # Verificar UFW
        result = subprocess.run(['sudo', 'ufw', 'status'], 
                              capture_output=True, text=True,
                              stderr=subprocess.DEVNULL)
        
        if result.returncode == 0:
            if 'Status: active' in result.stdout:
                print_warning("UFW (firewall) está ACTIVO")
                print_info("Esto puede bloquear paquetes de Link-Chat")
                print_info("\nPara desactivar temporalmente:")
                print_info("  sudo ufw disable")
                print_info("\nPara volver a activar:")
                print_info("  sudo ufw enable")
                return False
            else:
                print_success("UFW está inactivo (no bloqueará paquetes)")
                return True
        else:
            print_info("UFW no instalado o no disponible")
            return True
    
    except Exception as e:
        print_warning(f"No se pudo verificar firewall: {e}")
        return True


def test_arp_table():
    """Muestra tabla ARP para verificar descubrimiento"""
    print_header("5. TABLA ARP (Dispositivos descubiertos)")
    
    try:
        interface = utils.find_network_interface()
        
        import subprocess
        result = subprocess.run(['arp', '-i', interface, '-n'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            print_info("Dispositivos en la red local:")
            print(result.stdout)
            
            lines = result.stdout.split('\n')
            device_count = len([l for l in lines if l and not l.startswith('Address')])
            
            if device_count > 0:
                print_success(f"Se encontraron {device_count} dispositivos")
                return True
            else:
                print_warning("No se encontraron otros dispositivos")
                print_info("Esto es normal si las laptops no han intercambiado tráfico IP")
                return True
        else:
            print_info("Tabla ARP vacía o no disponible")
            return True
    
    except Exception as e:
        print_warning(f"No se pudo obtener tabla ARP: {e}")
        return True


def main():
    """Ejecuta diagnóstico completo para Ethernet"""
    print(Colors.BOLD + Colors.CYAN)
    print("=" * 70)
    print("  DIAGNÓSTICO ETHERNET - LINK-CHAT")
    print("  Cable directo entre dos laptops")
    print("=" * 70)
    print(Colors.RESET)
    
    # Verificar permisos
    if os.geteuid() != 0:
        print_error("Este script requiere permisos de root")
        print_info("Ejecuta con: sudo python3 ethernet_diagnostic.py")
        sys.exit(1)
    
    results = []
    
    # Test 1: Verificar interfaz Ethernet
    results.append(("Interfaz Ethernet", test_interface_cable_ethernet()))
    
    # Test 2: Verificar link físico
    results.append(("Enlace físico", test_ethernet_link()))
    
    # Test 3: Verificar firewall
    results.append(("Firewall", test_firewall()))
    
    # Test 4: Tabla ARP
    results.append(("Tabla ARP", test_arp_table()))
    
    # Test 5: Prueba de envío/recepción
    results.append(("Envío/Recepción", test_send_receive_pattern()))
    
    # Resumen
    print_header("RESUMEN")
    
    for name, result in results:
        if result:
            print_success(f"PASS - {name}")
        else:
            print_error(f"FAIL - {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} pruebas exitosas{Colors.RESET}\n")
    
    if passed == total:
        print_success("✓✓✓ TODO FUNCIONA CORRECTAMENTE ✓✓✓")
        print_info("\nSi Link-Chat no funciona, verifica:")
        print_info("  1. Ambas laptops ejecutan: sudo python3 main.py")
        print_info("  2. Usas 'discover' para encontrar dispositivos")
        print_info("  3. Usas la MAC correcta en 'send <mac> <mensaje>'")
    else:
        print_error("✗ Hay problemas que resolver")
        print_info("\nRevisa los errores arriba y sigue las recomendaciones")


if __name__ == "__main__":
    import os
    main()