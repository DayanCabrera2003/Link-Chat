"""
Utilidades para Link-Chat
Funciones auxiliares para operaciones de red en Capa 2
"""

import socket
import uuid


def get_mac_address() -> str:
    """
    Obtiene la dirección MAC de la máquina actual.
    
    Utiliza uuid.getnode() que retorna la dirección MAC como un número entero
    de 48 bits. Este número se convierte a formato hexadecimal estándar
    separado por dos puntos.
    
    Returns:
        str: Dirección MAC en formato 'xx:xx:xx:xx:xx:xx' (ejemplo: '08:00:27:7d:2b:8c')
    
    Example:
        >>> mac = get_mac_address()
        >>> print(mac)
        '08:00:27:7d:2b:8c'
    """
    # Obtener el identificador único del nodo (dirección MAC) como entero
    mac_int = uuid.getnode()
    
    # Convertir el entero a hexadecimal (48 bits = 12 dígitos hex)
    # El formato '{:012x}' asegura 12 caracteres hexadecimales con ceros a la izquierda
    mac_hex = '{:012x}'.format(mac_int)
    
    # Formatear como 'xx:xx:xx:xx:xx:xx' insertando ':' cada 2 caracteres
    mac_address = ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))
    
    return mac_address


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
