"""
Lógica de aplicación para Link-Chat
Manejo de paquetes y procesamiento de mensajes
Confirmaciones (ACK/NACK)
Reensamblado de archivos en el receptor
"""

import os
import struct
import time
import zlib
import threading
import config
import protocol
# CONFIGURACION GLOBAL
MAX_RETRIES = 3   #Maximo de reenvios por fragmento
ACK_TIMEOUT = 2.0  #Tiempo de espera por ACK antes de reintentar



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
        
        # Almacenar referencia al adaptador de red para poder enviar respuestas
        self.adapter = None
        
        # Nombre de usuario para respuestas de descubrimiento
        self.username = None
        # Control de ACK/NACK : mapa de fragmentos en espera
        self.pending_acks = {} 
        self.lock = threading.Lock()
    
    def set_adapter(self, adapter):
        """
        Configura el adaptador de red para poder enviar respuestas.
        
        Args:
            adapter: Instancia de NetworkAdapter
        """
        self.adapter = adapter
    
    def set_username(self, username: str):
        """
        Configura el nombre de usuario para respuestas de descubrimiento.
        
        Args:
            username (str): Nombre de usuario local
        """
        self.username = username
    
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
                # Estructura: [2B seq_num] + [4B checksum] + [datos]
                seq_num, checksum = struct.unpack('!HI',content[:6])
                chunk_data = content[6:]
                #Verificar checksum
                calc_checksum = zlib.crc32(chunk_data)
                if calc_checksum != checksum:
                    print(f"Checksum incorrecto en fragmento #{seq_num} de [{src_mac}] -> solicitando reenvio")
                    self._send_ack(src_mac, seq_num, success=False)
                # Buscar la transferencia activa para este remitente
                if src_mac not in self.file_transfers:
                    print(f"[Advertencia] Recibido FILE_DATA de [{src_mac}] sin FILE_START previo. Ignorando.")
                    return
                
                transfer = self.file_transfers[src_mac]
                file_object = transfer['file']
                
                # Escribir el fragmento de datos en el archivo
                file_object.write(chunk_data)
                
                # Actualizar contador de bytes recibidos
                transfer['received'] += len(chunk_data)
                
                # Mostrar progreso
                progress = (transfer['received'] / transfer['size']) * 100 if transfer['size'] > 0 else 100
                print(f"  Recibido fragmento #{seq_num}({len(chunk_data)} bytes) [{progress:.1f}%]")
                self._send_ack(src_mac, seq_num, success=True)
            
            except Exception as e:
                print(f"[Error] Error en recepcion de fragmento de [{src_mac}]: {e}")
        
        elif packet_type_value == protocol.PacketType.FILE_END.value:
            # Fin de transferencia de archivo
            try:
                # Buscar la transferencia activa para este remitente
                if src_mac not in self.file_transfers:
                    print(f"[Advertencia] Recibido FILE_END de [{src_mac}] sin transferencia activa. Ignorando.")
                    return
                
                transfer = self.file_transfers[src_mac]
                file_object = transfer['file']
                filename = transfer['filename']
                safe_filename = transfer['safe_filename']
                
                # Cerrar el archivo
                file_object.close()
                
                # Eliminar la entrada del diccionario de transferencias
                del self.file_transfers[src_mac]
                
                # Mensaje de confirmación
                print(f"\n✅ Archivo '{filename}' recibido correctamente y guardado como '{safe_filename}'\n")
            
            except Exception as e:
                print(f"[Error] Error al finalizar recepción de archivo de [{src_mac}]: {e}")
        
        elif packet_type_value in (protocol.PacketType.FILE_ACK.value, protocol.PacketType.FILE_NACK.value):
            seq_num = struct.unpack('!H',content)[0]
            with self.lock:
                if seq_num in self.pending_acks:
                    self.pending_acks[seq_num] = (packet_type_value == protocol.PacketType.FILE_ACK.value)
        
        elif packet_type_value == protocol.PacketType.DISCOVERY_REQUEST.value:
            # Solicitud de descubrimiento recibida
            try:
                # Decodificar el nombre de usuario del solicitante
                requester_username = content.decode('utf-8')
                
                print(f"\n🔍 Solicitud de descubrimiento de '{requester_username}' [{src_mac}]")
                
                # Verificar que tengamos un adaptador y nombre de usuario configurados
                if self.adapter is None:
                    print("[Advertencia] No se puede responder: adaptador no configurado")
                    return
                
                if self.username is None:
                    print("[Advertencia] No se puede responder: nombre de usuario no configurado")
                    return
                
                # Preparar respuesta con nuestro nombre de usuario
                response_username_bytes = self.username.encode('utf-8')
                
                # Crear cabecera DISCOVERY_RESPONSE
                response_header = protocol.LinkChatHeader.pack(
                    protocol.PacketType.DISCOVERY_RESPONSE,
                    len(response_username_bytes)
                )
                
                # Construir payload completo
                response_payload = response_header + response_username_bytes
                
                # Enviar respuesta directamente al solicitante (unicast a src_mac)
                self.adapter.send_frame(src_mac, response_payload)
                
                print(f"✓ Respuesta enviada como '{self.username}' a [{src_mac}]\n")
            
            except UnicodeDecodeError:
                print(f"[Advertencia] DISCOVERY_REQUEST corrupto recibido de [{src_mac}]")
            except Exception as e:
                print(f"[Error] Error al procesar DISCOVERY_REQUEST de [{src_mac}]: {e}")
        
        elif packet_type_value == protocol.PacketType.DISCOVERY_RESPONSE.value:
            # Respuesta de descubrimiento recibida
            try:
                # Decodificar el nombre de usuario del que respondió
                responder_username = content.decode('utf-8')
                
                # Mostrar usuario encontrado
                print(f"👤 Usuario encontrado: '{responder_username}' en [{src_mac}]")
            
            except UnicodeDecodeError:
                print(f"[Advertencia] DISCOVERY_RESPONSE corrupto recibido de [{src_mac}]")
            except Exception as e:
                print(f"[Error] Error al procesar DISCOVERY_RESPONSE de [{src_mac}]: {e}")
    
    def send_file(self, adapter, dest_mac: str, filepath: str):
        """
        Envía un archivo a través de la red en Capa 2.
        
        El archivo se envía en múltiples paquetes:
        1. FILE_START: Metadatos del archivo (nombre y tamaño)
        2. FILE_DATA: Fragmentos de datos del archivo con verificacion y reintento
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
            seq = 0
            
            # Leer y enviar el archivo en fragmentos
            while True:
                # Leer un fragmento del archivo del tamaño especificado en config.CHUNK_SIZE
                chunk = file.read(config.CHUNK_SIZE)
                
                # Si no hay más datos que leer, salir del bucle
                if not chunk:
                    break
                seq += 1
                checksum = zlib.crc32(chunk)
                chunk_payload = struct.pack('!HI',seq, checksum) + chunk
                header = protocol.LinkChatHeader.pack(protocol.PacketType.FILE_DATA,len(chunk_payload))
                packet = header + chunk_payload
                #Enviar con reintento
                self._send_with_ack(adapter,dest_mac,packet,seq)
                bytes_sent += len(chunk)
                
                # Mostrar progreso
                progress = (bytes_sent / file_size) * 100 if file_size > 0 else 100
                print(f"Fragmento #{seq} enviado ({len(chunk)} bytes) [{progress:.1f}%]")
        
        
        # Enviar paquete FILE_END para notificar fin de transferencia
        # Este paquete no tiene payload, solo la cabecera
        file_end_header = protocol.LinkChatHeader.pack(
            protocol.PacketType.FILE_END,
            0  # Longitud del payload = 0 (sin datos adicionales)
        )
        
        # Enviar el paquete FILE_END (solo cabecera)
        adapter.send_frame(dest_mac, file_end_header)
        
        print(f"✓ FILE_END enviado. Transferencia de '{filename}' completada.")

    def _send_ack(self, dest_mac: str ,seq_num: int, success=True):
        #Envia un ACK o NACK segun el resultado de recepcion.
        pkt_type = protocol.PacketType.FILE_ACK if success else protocol.PacketType.FILE_NACK
        payload = struct.pack('!H',seq_num)
        header = protocol.LinkChatHeader.pack(pkt_type,len(payload))
        self.adapter.send_frame(dest_mac,header+payload)
        print(f"Enviado {'ACK' if success else 'NACK'} para fragmento #{seq_num}")
    
    def _send_with_ack(self, adapter, dest_mac: str, packet: bytes, seq_num: int):
        #Envia un paquete y espera ACK/NACK con reintento automatico
        for attempt in range(MAX_RETRIES):
            with self.lock:
                self.pending_acks[seq_num] = None
            adapter.send_frame(dest_mac,packet)
            start_time = time.time()
            while time.time() - start_time < ACK_TIMEOUT:
                with self.lock:
                    status = self.pending_acks.get(seq_num)
                if status is not None:
                    if status:
                        print(f"ACK recibido para fragmento #{seq_num}")
                        return
                    else:
                        print(f"NACK recibido , reintentando fragmento #{seq_num}")
                        break
                time.sleep(0.1)
            print(f"Timeout esperando ACk de fragmento #{seq_num} (intento {attempt+1}/{MAX_RETRIES})")
        print(f"No se pudo confirmar fragmento #{seq_num} tras {MAX_RETRIES} intentos")
        
