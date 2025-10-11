"""
Protocolo de Link-Chat
Definición de la estructura de paquetes para comunicación en Capa 2
"""

import struct
from enum import Enum


class PacketType(Enum):
    """
    Enumeración de tipos de paquetes soportados por el protocolo Link-Chat.
    
    Cada tipo identifica el propósito del paquete en la comunicación:
    - TEXT: Mensaje de texto simple
    - FILE_START: Inicio de transferencia de archivo (contiene metadatos)
    - FILE_DATA: Fragmento de datos del archivo
    - FILE_END: Fin de transferencia de archivo
    - FOLDER_START: Inicio de una carpeta (nombre y ruta relativa)
    - FOLDER_END: Fin de una carpeta
    - FILE_ACK: Confirmación de recepción de fragmento
    - FILE_NACK: Notificación de fragmento corrupto o perdido
    - DISCOVERY_REQUEST: Solicitud de descubrimiento broadcast (quién está en la red)
    - DISCOVERY_RESPONSE: Respuesta a solicitud de descubrimiento (identificación)
    """
    TEXT = 0x01
    FILE_START = 0x02
    FILE_DATA = 0x03
    FILE_END = 0x04
    DISCOVERY_REQUEST = 0x05
    DISCOVERY_RESPONSE = 0x06
    FILE_ACK = 0x07
    FILE_NACK = 0x08
    FOLDER_START = 0x09
    FOLDER_END = 0x0A


class LinkChatHeader:
    """
    Cabecera del protocolo Link-Chat.
    
    Estructura de la cabecera (3 bytes total):
    - Byte 0: Tipo de paquete (PacketType) - 1 byte
    - Bytes 1-2: Longitud del payload - 2 bytes (unsigned short)
    
    Formato: Big-endian (!BH)
    - ! = Network byte order (big-endian)
    - B = unsigned char (1 byte)
    - H = unsigned short (2 bytes)
    
    -----------------------------
    Tipos de paquete para carpetas:
    
    FOLDER_START:
        Indica el inicio de una carpeta en la estructura a transferir.
        Payload:
            - 2 bytes: Longitud de la ruta relativa (!H = unsigned short)
            - N bytes: Ruta relativa de la carpeta en UTF-8 (ej: 'fotos/vacaciones')
        Ejemplo de uso: Para crear la carpeta 'fotos/vacaciones' en el receptor.
    
    FOLDER_END:
        Indica el fin de la carpeta actual.
        Payload:
            - 0 bytes (no contiene datos)
        Ejemplo de uso: Señala que se ha terminado de enviar el contenido de la carpeta actual.
    -----------------------------
    """
    
    # Tamaño total de la cabecera en bytes
    HEADER_SIZE = 3
    
    @staticmethod
    def pack(packet_type: PacketType, payload_len: int) -> bytes:
        """
        Empaqueta la cabecera del protocolo en bytes.
        
        Args:
            packet_type (PacketType): Tipo de paquete a enviar
            payload_len (int): Longitud del payload en bytes (0-65535)
        
        Returns:
            bytes: Cabecera empaquetada de 3 bytes
        
        Example:
            >>> header = LinkChatHeader.pack(PacketType.TEXT, 100)
            >>> len(header)
            3
        """
        # Formato: !BH = Big-endian, unsigned char (1 byte), unsigned short (2 bytes)
        # packet_type.value extrae el valor numérico del enum
        return struct.pack('!BH', packet_type.value, payload_len)
    
    @staticmethod
    def unpack(header_bytes: bytes) -> tuple:
        """
        Desempaqueta la cabecera del protocolo desde bytes.
        
        Args:
            header_bytes (bytes): Cabecera empaquetada de 3 bytes
        
        Returns:
            tuple: (packet_type: int, payload_len: int)
                - packet_type: Valor numérico del tipo de paquete
                - payload_len: Longitud del payload en bytes
        
        Raises:
            struct.error: Si header_bytes no tiene exactamente 3 bytes
        
        Example:
            >>> header = LinkChatHeader.pack(PacketType.TEXT, 100)
            >>> pkt_type, payload_len = LinkChatHeader.unpack(header)
            >>> pkt_type == PacketType.TEXT.value
            True
            >>> payload_len
            100
        """
        # Formato: !BH = Big-endian, unsigned char (1 byte), unsigned short (2 bytes)
        # Retorna tupla con (packet_type, payload_len)
        return struct.unpack('!BH', header_bytes)