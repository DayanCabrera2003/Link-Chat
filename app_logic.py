"""
Lógica de aplicación para Link-Chat
Manejo de paquetes y procesamiento de mensajes
"""

import protocol


class PacketHandler:
    """
    Manejador de paquetes para Link-Chat.
    
    Esta clase procesa los paquetes recibidos desde la red, decodifica
    sus cabeceras y ejecuta las acciones apropiadas según el tipo de paquete
    (mensajes de texto, transferencia de archivos, etc.).
    """
    
    def __init__(self):
        """
        Inicializa el manejador de paquetes.
        
        Por ahora no requiere configuración inicial, pero puede extenderse
        en el futuro para mantener estado de transferencias de archivos,
        historial de mensajes, etc.
        """
        pass
    
    def handle_packet(self, src_mac: str, payload: bytes):
        """
        Procesa un paquete recibido desde la red.
        
        Este método actúa como callback para el listener de red. Decodifica
        la cabecera del protocolo Link-Chat y procesa el contenido según
        el tipo de paquete.
        
        Args:
            src_mac (str): Dirección MAC de origen del paquete en formato 'xx:xx:xx:xx:xx:xx'
            payload (bytes): Datos recibidos incluyendo cabecera Link-Chat y contenido
        
        Example:
            >>> handler = PacketHandler()
            >>> # Simulando un paquete TEXT recibido
            >>> header = protocol.LinkChatHeader.pack(protocol.PacketType.TEXT, 5)
            >>> payload = header + b'Hola!'
            >>> handler.handle_packet('aa:bb:cc:dd:ee:ff', payload)
            Mensaje de [aa:bb:cc:dd:ee:ff]: Hola!
        """
        # Verificar que el payload tenga al menos el tamaño de la cabecera
        if len(payload) < protocol.LinkChatHeader.HEADER_SIZE:
            # Payload demasiado pequeño, ignorar
            return
        
        # Extraer la cabecera Link-Chat (primeros 3 bytes)
        header_bytes = payload[:protocol.LinkChatHeader.HEADER_SIZE]
        
        # Desempaquetar la cabecera para obtener tipo de paquete y longitud
        packet_type_value, payload_len = protocol.LinkChatHeader.unpack(header_bytes)
        
        # Extraer el contenido real (después de la cabecera)
        content = payload[protocol.LinkChatHeader.HEADER_SIZE:]
        
        # Procesar según el tipo de paquete
        if packet_type_value == protocol.PacketType.TEXT.value:
            # Es un mensaje de texto
            try:
                # Decodificar los bytes a string UTF-8
                message = content.decode('utf-8')
                
                # Imprimir el mensaje formateado con la MAC de origen
                print(f"Mensaje de [{src_mac}]: {message}")
            except UnicodeDecodeError:
                # Si falla la decodificación, ignorar el mensaje
                print(f"[Advertencia] Mensaje corrupto recibido de [{src_mac}]")
        
        # Aquí añadiran más tipos de paquetes en el futuro:
        # elif packet_type_value == protocol.PacketType.FILE_START.value:
        #     # Manejar inicio de transferencia de archivo
        #     pass
        # elif packet_type_value == protocol.PacketType.FILE_DATA.value:
        #     # Manejar fragmento de archivo
        #     pass
        # elif packet_type_value == protocol.PacketType.FILE_END.value:
        #     # Manejar fin de transferencia de archivo
        #     pass
