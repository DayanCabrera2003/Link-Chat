import socket
import struct
import os
import subprocess
import platform
import threading
from queue import Queue
import ipaddress
import re

def obtener_red_local():
    """Obtiene la IP local, la máscara y la MAC de la interfaz activa."""
    try:
        # Usar 'ip route' para encontrar la interfaz por defecto, es más robusto
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True, check=True)
        default_route = [line for line in result.stdout.splitlines() if 'default' in line]
        if not default_route:
            raise Exception("No se encontró la ruta por defecto.")
        
        parts = default_route[0].split()
        interface = parts[4]
        
        # Obtener la IP y máscara
        result_ip = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True, check=True)
        inet_line = [line for line in result_ip.stdout.splitlines() if 'inet ' in line][0]
        ip_mask = inet_line.strip().split()[1]
        ip, mask_str = ip_mask.split('/')

        # Obtener la MAC address
        mac_line = [line for line in result_ip.stdout.splitlines() if 'link/ether' in line][0]
        mac = mac_line.strip().split()[1]
        
        print(f"Interfaz activa: {interface}, IP: {ip}, MAC: {mac}")
        return ip, int(mask_str), mac
        
    except Exception as e:
        print(f"⚠️ No se pudo obtener la red local automáticamente: {e}.")
        return None, None, None

def generar_ips_red(ip, mask):
    """Genera todas las IPs de hosts en la red dada la IP y la máscara."""
    if not ip or not mask:
        return []
    try:
        network = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
        print(f"Generando IPs para la red: {network}")
        return [str(host) for host in network.hosts()]
    except Exception as e:
        print(f"Error al generar IPs: {e}")
        return []

def obtener_mac_de_ip(ip):
    """
    Obtiene la dirección MAC para una IP dada consultando la caché ARP del sistema.
    """
    try:
        # Comando para buscar en la tabla ARP, funciona en Linux y macOS
        # Usamos 'ip neigh' que es más moderno que 'arp'
        result = subprocess.run(['ip', 'neigh', 'show', ip], capture_output=True, text=True, check=True)
        match = re.search(r'lladdr (\S+)', result.stdout)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback para sistemas que usan 'arp' o si 'ip neigh' falla
        try:
            # El ping previo debería haber poblado la caché
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, check=True)
            match = re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', result.stdout)
            if match:
                return match.group(0)
        except Exception:
            pass  # No se pudo obtener la MAC
    return None

# --- Implementación del escaneo en paralelo ---

# Lista para almacenar los hosts activos encontrados
hosts_activos_global = []
# Lock para evitar condiciones de carrera al escribir en la lista
lock = threading.Lock()

def ping_worker(q):
    """Toma IPs de una cola, les hace ping y agrega las activas (IP y MAC) a la lista global."""
    while not q.empty():
        ip = q.get()
        try:
            # Parámetro de ping varía según el SO para un timeout rápido
            param = '-n 1 -w 500' if platform.system().lower() == 'windows' else '-c 1 -W 0.5'
            command = ['ping', *param.split(), ip]
            
            # Ejecutar ping sin mostrar salida
            response = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
            
            if response.returncode == 0:
                # Host activo, ahora obtenemos su MAC
                mac = obtener_mac_de_ip(ip)
                with lock:
                    hosts_activos_global.append({'ip': ip, 'mac': mac})
        except subprocess.TimeoutExpired:
            pass  # El host no respondió
        except Exception:
            pass  # Otro error
        finally:
            q.task_done()

def escanear_hosts_ping():
    """Escanea la red local usando pings en paralelo para máxima velocidad."""
    global hosts_activos_global
    hosts_activos_global = []

    print("Escaneando hosts activos en la LAN (ping paralelo)...")
    local_ip, mask, _ = obtener_red_local() # Obtenemos la IP local para filtrarla
    if not local_ip:
        print("No se pudo iniciar el escaneo. Abortando.")
        return []

    ips_a_escanear = generar_ips_red(local_ip, mask)
    if not ips_a_escanear:
        print("No se generaron IPs para escanear.")
        return []

    q = Queue()
    for ip_addr in ips_a_escanear:
        q.put(ip_addr)

    threads = []
    num_threads = min(100, len(ips_a_escanear))  # Hasta 100 hilos

    for _ in range(num_threads):
        thread = threading.Thread(target=ping_worker, args=(q,))
        thread.start()
        threads.append(thread)

    q.join()  # Esperar a que la cola se vacíe

    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()

    # Filtrar la propia IP de los resultados
    resultados_filtrados = [host for host in hosts_activos_global if host['ip'] != local_ip]

    print("\n--- Escaneo completado ---")
    if not resultados_filtrados:
        print("No se detectaron otros hosts activos en la red.")
    else:
        print("Hosts activos detectados:")
        # Ordenar por IP para una mejor visualización
        sorted_hosts = sorted(resultados_filtrados, key=lambda h: socket.inet_aton(h['ip']))
        for host in sorted_hosts:
            mac_str = host['mac'] if host['mac'] else "No encontrada"
            print(f"  - IP: {host['ip']:<15} MAC: {mac_str}")
    return sorted_hosts
