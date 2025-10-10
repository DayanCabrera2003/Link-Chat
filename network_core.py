"""
Núcleo de red para Link-Chat
Manejo de sockets crudos (raw sockets) en Capa 2 (Enlace de Datos)
"""

import socket
import struct
import threading

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
        self.src_mac = utils.get_mac_address(self.interface_name)
    
    def send_frame(self, dest_mac_str: str, payload: bytes):
        """
        Envía una trama Ethernet con el payload especificado a la dirección MAC destino.
        
        Construye una trama Ethernet completa con:
        - Dirección MAC destino (6 bytes)
        - Dirección MAC origen (6 bytes)
        - EtherType (2 bytes)
        - Payload (datos a transmitir)
        
        Args:
            dest_mac_str (str): Dirección MAC destino en formato 'xx:xx:xx:xx:xx:xx'
                               (ej: 'ff:ff:ff:ff:ff:ff' para broadcast)
            payload (bytes): Datos a enviar en la trama
        
        Example:
            >>> adapter = NetworkAdapter('eth0')
            >>> adapter.send_frame('ff:ff:ff:ff:ff:ff', b'Hello, Network!')
        """
        # Convertir dirección MAC de destino de string a bytes
        # Formato: 'aa:bb:cc:dd:ee:ff' -> b'\xaa\xbb\xcc\xdd\xee\xff'
        dest_mac_bytes = bytes.fromhex(dest_mac_str.replace(':', ''))
        
        # Convertir dirección MAC de origen de string a bytes
        src_mac_bytes = bytes.fromhex(self.src_mac.replace(':', ''))
        
        # Construir la cabecera Ethernet (14 bytes total)
        # Formato: !6s6sH
        # ! = Network byte order (big-endian)
        # 6s = Secuencia de 6 bytes (MAC destino)
        # 6s = Secuencia de 6 bytes (MAC origen)
        # H = Unsigned short de 2 bytes (EtherType)
        ethernet_header = struct.pack(
            '!6s6sH',
            dest_mac_bytes,
            src_mac_bytes,
            config.ETHTYPE_CUSTOM
        )
        
        # Construir la trama completa concatenando header + payload
        frame = ethernet_header + payload
        
        # Enviar la trama a través del socket crudo
        self.socket.send(frame)
    
    def receive_frame(self):
        """
        Recibe una trama Ethernet desde el socket crudo.
        
        Espera (bloquea) hasta recibir una trama Ethernet completa, luego
        desempaqueta la cabecera Ethernet y extrae la información relevante.
        
        Returns:
            tuple: (src_mac: str, dest_mac: str, payload: bytes)
                - src_mac: Dirección MAC de origen en formato 'xx:xx:xx:xx:xx:xx'
                - dest_mac: Dirección MAC destino en formato 'xx:xx:xx:xx:xx:xx'
                - payload: Datos recibidos (bytes) sin la cabecera Ethernet
        
        Example:
            >>> adapter = NetworkAdapter('eth0')
            >>> src, dest, data = adapter.receive_frame()
            >>> print(f"From: {src}, To: {dest}, Data: {data}")
        """
        # Recibir datos del socket crudo
        # recvfrom(65535) recibe hasta 65535 bytes (tamaño máximo razonable para una trama)
        # Retorna tupla: (packet, address)
        # - packet: bytes con la trama completa (header Ethernet + payload)
        # - address: información de la dirección (no la usamos aquí)
        packet, address = self.socket.recvfrom(65535)
        
        # Tamaño de la cabecera Ethernet: 14 bytes
        # - 6 bytes: MAC destino
        # - 6 bytes: MAC origen
        # - 2 bytes: EtherType
        ethernet_header_size = 14
        
        # Extraer la cabecera Ethernet de los primeros 14 bytes
        ethernet_header = packet[:ethernet_header_size]
        
        # Desempaquetar la cabecera Ethernet
        # Formato: !6s6sH (igual que en send_frame)
        dest_mac_bytes, src_mac_bytes, ethertype = struct.unpack(
            '!6s6sH',
            ethernet_header
        )
        
        # Convertir las direcciones MAC de bytes a formato string 'xx:xx:xx:xx:xx:xx'
        # bytes.hex() convierte bytes a hexadecimal: b'\xaa\xbb' -> 'aabb'
        # Luego insertamos ':' cada 2 caracteres
        src_mac_str = ':'.join(src_mac_bytes.hex()[i:i+2] for i in range(0, 12, 2))
        dest_mac_str = ':'.join(dest_mac_bytes.hex()[i:i+2] for i in range(0, 12, 2))
        
        # Extraer el payload (todo después de la cabecera Ethernet)
        payload = packet[ethernet_header_size:]
        
        # Retornar tupla con MAC origen, MAC destino y payload
        return src_mac_str, dest_mac_str, payload


def start_listener_thread(adapter: NetworkAdapter, packet_handler_callback):
    """
    Inicia un hilo (thread) que escucha continuamente tramas Ethernet entrantes.
    
    Crea un hilo daemon que ejecuta un bucle infinito esperando tramas de red.
    Cada trama recibida se procesa mediante la función callback proporcionada.
    
    Args:
        adapter (NetworkAdapter): Instancia del adaptador de red configurado
        packet_handler_callback: Función callback que procesa los paquetes recibidos.
                                 Debe aceptar dos argumentos:
                                 - src_mac (str): Dirección MAC de origen
                                 - payload (bytes): Datos recibidos
    
    Returns:
        threading.Thread: El hilo creado e iniciado (útil para debugging o join)
    
    Example:
        >>> def handle_packet(src_mac, payload):
        ...     print(f"Recibido de {src_mac}: {payload}")
        >>> adapter = NetworkAdapter('eth0')
        >>> thread = start_listener_thread(adapter, handle_packet)
    """
    
    def _listener_loop():
        """
        Bucle interno que escucha continuamente tramas entrantes.
        
        Este bucle se ejecuta indefinidamente en un hilo separado,
        recibiendo tramas y procesándolas con el callback.
        """
        while True:
            # Recibir una trama desde el adaptador de red
            # Retorna: (src_mac, dest_mac, payload)
            src_mac, dest_mac, payload = adapter.receive_frame()
            
            # Llamar al callback con la MAC de origen y el payload
            # El callback es responsable de procesar estos datos
            # (ej: decodificar mensajes, manejar archivos, etc.)
            packet_handler_callback(src_mac, payload)
    
    # Crear un nuevo hilo que ejecutará la función _listener_loop
    listener_thread = threading.Thread(target=_listener_loop)
    
    # Configurar como daemon: el hilo se cerrará automáticamente
    # cuando el programa principal termine, sin necesidad de join()
    listener_thread.daemon = True
    
    # Iniciar el hilo (comienza a ejecutar _listener_loop)
    listener_thread.start()
    
    # Retornar el hilo creado
    return listener_thread
