"""
Núcleo de red para Link-Chat
Manejo de sockets crudos (raw sockets) en Capa 2 (Enlace de Datos)
"""

import socket

import config
import utils


class NetworkAdapter:
    """
    Adaptador de red para comunicación en Capa 2 usando sockets crudos.
    
    Esta clase encapsula la funcionalidad de bajo nivel necesaria para enviar
    y recibir tramas Ethernet directamente, sin pasar por las capas superiores
    del stack TCP/IP.
    
    Attributes:
        interface_name (str): Nombre de la interfaz de red (ej: 'eth0', 'wlan0')
        socket: Socket crudo AF_PACKET para comunicación en Capa 2
        src_mac (str): Dirección MAC de origen de esta máquina
    """
    
    def __init__(self, interface_name: str):
        """
        Inicializa el adaptador de red con la interfaz especificada.
        
        Args:
            interface_name (str): Nombre de la interfaz de red a utilizar
                                 (ej: 'eth0', 'enp0s3', 'wlan0')
        
        Raises:
            OSError: Si no se puede crear el socket o hacer bind a la interfaz
                    (puede requerir privilegios de root/sudo)
        
        Example:
            >>> adapter = NetworkAdapter('eth0')
            >>> print(adapter.interface_name)
            'eth0'
        """
        # Almacenar el nombre de la interfaz de red
        self.interface_name = interface_name
        
        # Crear un socket crudo (raw socket) en Capa 2
        # AF_PACKET: Permite acceso directo a la capa de enlace de datos
        # SOCK_RAW: Socket crudo que incluye la cabecera de la capa de enlace
        # socket.htons(): Convierte el EtherType a network byte order (big-endian)
        # ETHTYPE_CUSTOM: Nuestro EtherType personalizado (0x1234) para identificar paquetes
        self.socket = socket.socket(
            socket.AF_PACKET,
            socket.SOCK_RAW,
            socket.htons(config.ETHTYPE_CUSTOM)
        )
        
        # Vincular (bind) el socket a la interfaz de red especificada
        # El formato es (interface_name, protocol)
        # protocol=0 significa que escuchamos todos los protocolos en esta interfaz
        self.socket.bind((interface_name, 0))
        
        # Obtener y almacenar la dirección MAC de origen de esta máquina
        # Se usará como dirección MAC de origen en todas las tramas enviadas
        self.src_mac = utils.get_mac_address()
