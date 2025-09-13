import time
import socket
import struct
import binascii
import os

ACK_TYPE = 0x9999
BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'

# Utilidades

def mac_str_to_bytes(mac_str):
    return binascii.unhexlify(mac_str.replace(':', ''))

def _list_candidate_interfaces():
    """Return a list of non-loopback interfaces, preferring those that are up."""
    candidates = []
    try:
        for name in os.listdir('/sys/class/net'):
            if name == 'lo' or name.startswith('veth'):
                continue
            # Deprioritize docker bridges unless nothing else
            if name.startswith('docker') or name.startswith('br-'):
                candidates.append((name, False))
                continue
            # Check if interface is up
            oper_path = f'/sys/class/net/{name}/operstate'
            is_up = False
            try:
                with open(oper_path) as f:
                    is_up = f.read().strip() == 'up'
            except Exception:
                pass
            candidates.append((name, is_up))
    except Exception:
        pass
    # Prefer interfaces that are up; keep original order otherwise
    up = [n for n, up in candidates if up]
    down = [n for n, up in candidates if not up]
    return up + down

def get_active_interface(default_hint: str | None = None) -> str | None:
    """
    Pick an active interface to use.
    Priority:
    - Env var LINKCHAT_IFACE
    - Provided default_hint if exists
    - First non-loopback interface that's up
    - Any non-loopback interface
    """
    env_iface = os.environ.get('LINKCHAT_IFACE')
    if env_iface:
        return env_iface
    if default_hint:
        # Validate default_hint exists
        if os.path.exists(f'/sys/class/net/{default_hint}'):
            return default_hint
    for name in _list_candidate_interfaces():
        return name if name else None
    return None

def get_local_mac(interface: str | None = None):
    if interface is None:
        interface = get_active_interface()
    if not interface:
        return None
    try:
        with open(f'/sys/class/net/{interface}/address') as f:
            mac = f.read().strip()
            if mac:
                return mac
    except Exception:
        pass
    # Intentar obtener la MAC usando ip link si la lectura directa falla
    try:
        import subprocess
        result = subprocess.getoutput(f"ip link show {interface}")
        for line in result.splitlines():
            if 'link/ether' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'link/ether' and i+1 < len(parts):
                        return parts[i+1]
    except Exception:
        pass
    return None

def crear_trama_ethernet(mac_destino, mac_origen, tipo, datos):
    eth_header = mac_str_to_bytes(mac_destino) + mac_str_to_bytes(mac_origen) + struct.pack('!H', tipo)
    return eth_header + datos

# Envío y recepción de tramas

def send_frame(mac_destino, datos, interface: str | None = None, tipo=0x1234):
    if interface is None:
        interface = get_active_interface('eth0')
    mac_origen = get_local_mac(interface)
    if not mac_origen:
        print("No se pudo obtener la MAC local.")
        return
    trama = crear_trama_ethernet(mac_destino, mac_origen, tipo, datos)
    # Padding para asegurar longitud mínima de 60 bytes (sin CRC)
    if len(trama) < 60:
        trama += b'\x00' * (60 - len(trama))
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        s.bind((interface, 0))
        s.send(trama)
        s.close()
        print(f"Trama enviada a {mac_destino}")
    except PermissionError:
        print("Permiso denegado. Ejecuta como root o con capacidades NET_RAW.")
    except Exception as e:
        print(f"Error al enviar trama: {e}")


import select
def receive_frame(interface: str | None = None, tipo=0x1234, timeout=15):
    if interface is None:
        interface = get_active_interface('eth0')
    if not interface:
        print("No hay interfaz de red disponible para recibir.")
        return None, None
    s = None
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(tipo))
        s.bind((interface, 0))
        s.setblocking(0)
        ready = select.select([s], [], [], timeout)
        if ready[0]:
            trama, addr = s.recvfrom(65535)
            mac_destino = binascii.hexlify(trama[0:6]).decode()
            mac_origen = binascii.hexlify(trama[6:12]).decode()
            tipo_trama = struct.unpack('!H', trama[12:14])[0]
            datos = trama[14:]
            if tipo_trama == tipo:
                print(f"Trama recibida de {mac_origen}: {datos}")
                return mac_origen, datos
        else:
            print(f"No se recibió ninguna trama en {timeout} segundos.")
            return None, None
    except PermissionError:
        print("Permiso denegado. Ejecuta como root o con capacidades NET_RAW.")
        return None, None
    except Exception as e:
        print(f"Error al recibir trama: {e}")
        return None, None
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass

# ACK y broadcast

def send_ack(mac_destino, interface: str | None = None):
    if interface is None:
        interface = get_active_interface('eth0')
    mac_origen = get_local_mac(interface)
    trama = crear_trama_ethernet(mac_destino, mac_origen, ACK_TYPE, b'ACK')
    if len(trama) < 60:
        trama += b'\x00' * (60 - len(trama))
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        s.bind((interface, 0))
        s.send(trama)
        s.close()
    except Exception:
        pass

def wait_for_ack(interface: str | None = None, timeout=2):
    if interface is None:
        interface = get_active_interface('eth0')
    start = time.time()
    while time.time() - start < timeout:
        try:
            mac_origen, datos, tipo = receive_frame_full(interface=interface, return_type=True)
            if tipo == ACK_TYPE:
                return True
        except Exception:
            pass
    return False

def receive_frame_full(interface: str | None = None, tipo=0x1234, return_type=False, timeout=3):
    if interface is None:
        interface = get_active_interface('eth0')
    if not interface:
        print("No hay interfaz de red disponible para recibir.")
        return (None, None, None) if return_type else (None, None)
    ETH_P_ALL = 0x0003
    s = None
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
        s.bind((interface, 0))
        s.setblocking(0)
        import select
        ready = select.select([s], [], [], timeout)
        if ready[0]:
            trama, addr = s.recvfrom(65535)
            mac_destino = binascii.hexlify(trama[0:6]).decode()
            mac_origen = binascii.hexlify(trama[6:12]).decode()
            tipo_trama = struct.unpack('!H', trama[12:14])[0]
            datos = trama[14:]
            if return_type:
                return mac_origen, datos, tipo_trama
            if tipo_trama == tipo:
                print(f"Trama recibida de {mac_origen}: {datos}")
                return mac_origen, datos
        else:
            print(f"No se recibió ninguna trama en {timeout} segundos.")
            return (None, None, None) if return_type else (None, None)
    except Exception as e:
        print(f"Error al recibir trama: {e}")
        return (None, None, None) if return_type else (None, None)
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass

def format_mac(mac_bytes_or_str):
    """Convierte MAC a formato estándar xx:xx:xx:xx:xx:xx"""
    if isinstance(mac_bytes_or_str, bytes):
        mac = mac_bytes_or_str.hex()
    else:
        mac = mac_bytes_or_str.replace(":", "").lower()
    return ":".join(mac[i:i+2] for i in range(0, 12, 2))
# Clase opcional para manipulación OO
class EthernetFrame:
    def __init__(self, destination_mac, source_mac, payload):
        self.destination_mac = destination_mac
        self.source_mac = source_mac
        self.payload = payload

    def create_frame(self):
        return {
            'destination_mac': self.destination_mac,
            'source_mac': self.source_mac,
            'payload': self.payload
        }
