"""
Utilidades para Link-Chat
Funciones auxiliares para operaciones de red en Capa 2
"""

import socket
import uuid


def get_mac_address(interface: str) -> str:
    """
    Obtiene la dirección MAC de una interfaz de red específica.
    
    Lee la dirección MAC del sistema de archivos sysfs de Linux, que es el
    método más fiable para una interfaz concreta.
    
    Args:
        interface (str): Nombre de la interfaz (ej: 'eth0')
        
    Returns:
        str: Dirección MAC en formato 'xx:xx:xx:xx:xx:xx'
    
    Raises:
        IOError: Si no se puede leer la dirección MAC para la interfaz dada.
    
    Example:
        >>> mac = get_mac_address('eth0')
        >>> print(mac)
        '08:00:27:7d:2b:8c'
    """
    try:
        # En sistemas Linux, la forma más fiable es leer desde sysfs
        with open(f'/sys/class/net/{interface}/address') as f:
            mac = f.read().strip()
        return mac
    except FileNotFoundError:
        raise IOError(f"No se pudo encontrar la dirección MAC para la interfaz '{interface}'. "
                      "Verifique que la interfaz existe y que está en un sistema Linux.")
    except Exception as e:
        raise IOError(f"Error al leer la dirección MAC para '{interface}': {e}")


def find_network_interface() -> str:
    """
    Encuentra una interfaz de red adecuada para usar (excluyendo loopback).
    
    Utiliza socket.if_nameindex() que retorna una lista de tuplas con el formato
    (index, name) para cada interfaz de red disponible en el sistema.
    Se excluye la interfaz 'lo' (loopback) ya que no es útil para comunicación
    en la red local.
    
    Returns:
        str: Nombre de la interfaz de red (ejemplo: 'eth0', 'wlan0', 'enp0s3')
    
    Raises:
        IOError: Si no se encuentra ninguna interfaz de red válida (diferente de 'lo')
    
    Example:
        >>> interface = find_network_interface()
        >>> print(interface)
        'eth0'
    """
    # Obtener lista de todas las interfaces de red del sistema
    # Retorna lista de tuplas: [(index, name), ...]
    interfaces = socket.if_nameindex()
    
    # Iterar sobre las interfaces disponibles
    for index, name in interfaces:
        # Excluir la interfaz loopback 'lo'
        if name != 'lo':
            return name
    
    # Si no se encuentra ninguna interfaz válida, lanzar excepción
    raise IOError("No se encontró ninguna interfaz de red válida (todas son 'lo' o no hay interfaces)")
