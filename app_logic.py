"""
Lógica de aplicación para Link-Chat
Manejo de paquetes y procesamiento de mensajes
"""

import os
import struct

import config
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
        
        Mantiene un registro de las transferencias de archivos en curso,
        usando la dirección MAC de origen como clave.
        """
        # Diccionario para rastrear transferencias de archivos activas
        # Estructura: {src_mac: {'file': file_object, 'filename': str, 'size': int, 'received': int}}
        self.file_transfers = {}
    
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
        
        elif packet_type_value == protocol.PacketType.FILE_START.value:
            # Inicio de transferencia de archivo
            try:
                # Desempaquetar el payload del FILE_START
                # Estructura: [longitud_nombre (2B)] + [nombre_archivo] + [tamaño_archivo (8B)]
                
                # Extraer longitud del nombre del archivo (primeros 2 bytes)
                filename_len = struct.unpack('!H', content[:2])[0]
                
                # Extraer el nombre del archivo
                filename_bytes = content[2:2 + filename_len]
                filename = filename_bytes.decode('utf-8')
                
                # Extraer el tamaño total del archivo (últimos 8 bytes)
                file_size = struct.unpack('!Q', content[2 + filename_len:2 + filename_len + 8])[0]
                
                # Crear un nombre único para el archivo recibido (evitar sobrescribir)
                # Agregar prefijo con la MAC del remitente
                safe_filename = f"received_{filename}"
                
                # Abrir archivo para escritura binaria
                file_object = open(safe_filename, 'wb')
                
                # Guardar información de la transferencia en el diccionario
                self.file_transfers[src_mac] = {
                    'file': file_object,
                    'filename': filename,
                    'safe_filename': safe_filename,
                    'size': file_size,
                    'received': 0
                }
                
                print(f"\n📥 Recibiendo archivo '{filename}' ({file_size} bytes) de [{src_mac}]...")
            
            except Exception as e:
                print(f"[Error] No se pudo iniciar recepción de archivo de [{src_mac}]: {e}")
        
        elif packet_type_value == protocol.PacketType.FILE_DATA.value:
            # Fragmento de datos del archivo
            try:
                # Buscar la transferencia activa para este remitente
                if src_mac not in self.file_transfers:
                    print(f"[Advertencia] Recibido FILE_DATA de [{src_mac}] sin FILE_START previo. Ignorando.")
                    return
                
                transfer = self.file_transfers[src_mac]
                file_object = transfer['file']
                
                # Escribir el fragmento de datos en el archivo
                file_object.write(content)
                
                # Actualizar contador de bytes recibidos
                transfer['received'] += len(content)
                
                # Mostrar progreso
                progress = (transfer['received'] / transfer['size']) * 100 if transfer['size'] > 0 else 100
                print(f"  Recibiendo... {transfer['received']}/{transfer['size']} bytes ({progress:.1f}%)")
            
            except Exception as e:
                print(f"[Error] Error al escribir datos de archivo de [{src_mac}]: {e}")
        
        elif packet_type_value == protocol.PacketType.FILE_END.value:
            # Fin de transferencia de archivo
            # Este caso se implementará en el siguiente prompt
            pass
    
    def send_file(self, adapter, dest_mac: str, filepath: str):
        """
        Envía un archivo a través de la red en Capa 2.
        
        El archivo se envía en múltiples paquetes:
        1. FILE_START: Metadatos del archivo (nombre y tamaño)
        2. FILE_DATA: Fragmentos de datos del archivo
        3. FILE_END: Señal de finalización
        
        Args:
            adapter: Instancia de NetworkAdapter para enviar tramas
            dest_mac (str): Dirección MAC destino en formato 'xx:xx:xx:xx:xx:xx'
            filepath (str): Ruta del archivo a enviar
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            IOError: Si hay problemas al leer el archivo
        
        Example:
            >>> handler = PacketHandler()
            >>> handler.send_file(adapter, 'ff:ff:ff:ff:ff:ff', '/path/to/file.txt')
        """
        # Verificar que el archivo existe
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"El archivo '{filepath}' no existe")
        
        # Obtener el nombre del archivo (sin la ruta completa)
        filename = os.path.basename(filepath)
        
        # Obtener el tamaño total del archivo en bytes
        file_size = os.path.getsize(filepath)
        
        # Codificar el nombre del archivo a bytes UTF-8
        filename_bytes = filename.encode('utf-8')
        filename_len = len(filename_bytes)
        
        # Construir el payload para el paquete FILE_START
        # Estructura:
        # - 2 bytes: Longitud del nombre del archivo (!H = unsigned short)
        # - N bytes: Nombre del archivo en UTF-8
        # - 8 bytes: Tamaño total del archivo (!Q = unsigned long long)
        
        # Empaquetar la longitud del nombre del archivo (2 bytes)
        filename_len_bytes = struct.pack('!H', filename_len)
        
        # Empaquetar el tamaño total del archivo (8 bytes)
        file_size_bytes = struct.pack('!Q', file_size)
        
        # Construir el payload completo del FILE_START
        file_start_payload = filename_len_bytes + filename_bytes + file_size_bytes
        
        # Crear la cabecera Link-Chat para FILE_START
        file_start_header = protocol.LinkChatHeader.pack(
            protocol.PacketType.FILE_START,
            len(file_start_payload)
        )
        
        # Construir el paquete completo: cabecera + payload
        file_start_packet = file_start_header + file_start_payload
        
        # Enviar el paquete FILE_START
        adapter.send_frame(dest_mac, file_start_packet)
        
        print(f"✓ FILE_START enviado: '{filename}' ({file_size} bytes) -> [{dest_mac}]")
        
        # Abrir el archivo en modo lectura binaria
        with open(filepath, 'rb') as file:
            # Contador para seguimiento de progreso
            bytes_sent = 0
            chunk_count = 0
            
            # Leer y enviar el archivo en fragmentos
            while True:
                # Leer un fragmento del archivo del tamaño especificado en config.CHUNK_SIZE
                chunk = file.read(config.CHUNK_SIZE)
                
                # Si no hay más datos que leer, salir del bucle
                if not chunk:
                    break
                
                # Incrementar contador de fragmentos
                chunk_count += 1
                bytes_sent += len(chunk)
                
                # Crear la cabecera Link-Chat para FILE_DATA
                file_data_header = protocol.LinkChatHeader.pack(
                    protocol.PacketType.FILE_DATA,
                    len(chunk)
                )
                
                # Construir el paquete completo: cabecera + fragmento de datos
                file_data_packet = file_data_header + chunk
                
                # Enviar el paquete FILE_DATA
                adapter.send_frame(dest_mac, file_data_packet)
                
                # Mostrar progreso
                progress = (bytes_sent / file_size) * 100 if file_size > 0 else 100
                print(f"  Enviando... {bytes_sent}/{file_size} bytes ({progress:.1f}%) - Fragmento #{chunk_count}")
        
        print(f"✓ Archivo '{filename}' enviado completamente: {chunk_count} fragmentos, {bytes_sent} bytes")
        
        # Enviar paquete FILE_END para notificar fin de transferencia
        # Este paquete no tiene payload, solo la cabecera
        file_end_header = protocol.LinkChatHeader.pack(
            protocol.PacketType.FILE_END,
            0  # Longitud del payload = 0 (sin datos adicionales)
        )
        
        # Enviar el paquete FILE_END (solo cabecera)
        adapter.send_frame(dest_mac, file_end_header)
        
        print(f"✓ FILE_END enviado. Transferencia de '{filename}' completada.")
