"""
Utilidades para Link-Chat
Funciones auxiliares para operaciones de red en Capa 2
"""

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
