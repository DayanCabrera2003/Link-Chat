"""
Lógica de aplicación para Link-Chat
Manejo de paquetes y procesamiento de mensajes
"""

import os
import struct

import config
import protocol
import threading
import folder_utils

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
        self._folder_stack = []  # Pila de rutas absolutas
        self._folder_base = None  # Carpeta base de recepción
    
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
                
                # MODIFICACIÓN: Si estamos dentro de una carpeta, guardar ahí
                if self._folder_stack:
                    # Guardar en la carpeta actual de la pila
                    current_folder = self._folder_stack[-1]
                    safe_filename = os.path.join(current_folder, filename)
                else:
                    # Comportamiento original: prefijo "received_"
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
        
        elif packet_type_value == protocol.PacketType.FOLDER_START.value:
            # Inicio de una carpeta
            try:
                # Extraer longitud y ruta relativa
                path_len = struct.unpack('!H', content[:2])[0]
                rel_path = content[2:2 + path_len].decode('utf-8')
                
                # Si es la primera carpeta, establecer base
                if not self._folder_stack:
                    self._folder_base = f"received_{os.path.basename(rel_path)}" if rel_path else "received_folder"
                    current_path = self._folder_base
                else:
                    # Construir ruta desde la base
                    current_path = os.path.join(self._folder_base, rel_path) if rel_path else self._folder_base
                
                # Crear carpeta si no existe
                if not os.path.exists(current_path):
                    os.makedirs(current_path, exist_ok=True)
                    print(f"📁 Creando carpeta: {current_path}")
                
                # Añadir a la pila
                self._folder_stack.append(current_path)
                
            except Exception as e:
                print(f"[Error] Error al procesar FOLDER_START de [{src_mac}]: {e}")
        
        elif packet_type_value == protocol.PacketType.FOLDER_END.value:
            # Fin de carpeta
            try:
                if self._folder_stack:
                    closed_folder = self._folder_stack.pop()
                    print(f"✅ Carpeta completada: {closed_folder}")
                    
                    # Si se cerró la carpeta raíz, limpiar estado
                    if not self._folder_stack:
                        print(f"\n🎉 Recepción de carpeta completada: {self._folder_base}\n")
                        self._folder_base = None
                else:
                    print(f"[Advertencia] FOLDER_END sin FOLDER_START de [{src_mac}]")
            
            except Exception as e:
                print(f"[Error] Error al procesar FOLDER_END de [{src_mac}]: {e}")
    
    def send_file(self, adapter, dest_mac: str, filepath: str):
        """
        Envía un archivo a través de la red en Capa 2.
        El archivo se envía en múltiples paquetes:
        1. FILE_START: Metadatos del archivo (nombre y tamaño)
        2. FILE_DATA: Fragmentos de datos del archivo
        3. FILE_END: Señal de finalización
        """
        # Verificar que el archivo existe
        if not os.path.exists(filepath):
            print(f"[ERROR] El archivo '{filepath}' no existe.")
            return
        
        filename = os.path.basename(filepath)
        
        try:
            file_size = os.path.getsize(filepath)
        except Exception as e:
            print(f"[ERROR] No se pudo obtener el tamaño de '{filepath}': {e}")
            return
        
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
        
        print(f"✓ [FILE] FILE_START enviado: '{filename}' ({file_size} bytes) -> [{dest_mac}]")
        
        try:
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
                    print(f"  [FILE] Enviando... {bytes_sent}/{file_size} bytes ({progress:.1f}%) - Fragmento #{chunk_count}")
            
            print(f"✓ [FILE] Archivo '{filename}' enviado completamente: {chunk_count} fragmentos, {bytes_sent} bytes")
            
            # Enviar paquete FILE_END para notificar fin de transferencia
            # Este paquete no tiene payload, solo la cabecera
            file_end_header = protocol.LinkChatHeader.pack(
                protocol.PacketType.FILE_END,
                0  # Longitud del payload = 0 (sin datos adicionales)
            )
            
            # Enviar el paquete FILE_END (solo cabecera)
            adapter.send_frame(dest_mac, file_end_header)
            
            print(f"✓ [FILE] FILE_END enviado. Transferencia de '{filename}' completada.")
        
        except PermissionError:
            print(f"[ERROR] Permisos insuficientes para leer el archivo '{filepath}'.")
        except OSError as e:
            print(f"[ERROR] Error de sistema al leer/enviar '{filepath}': {e}")
        except Exception as e:
            print(f"[ERROR] Error inesperado durante el envío de archivo '{filepath}': {e}")
    
    def _send_file_with_path(self, adapter, dest_mac: str, filepath: str, filename_for_header: str):
        """
        Versión interna de send_file que permite especificar el nombre en el header.
        Usado para enviar archivos dentro de carpetas preservando la ruta relativa.
        
        Args:
            adapter: Instancia de NetworkAdapter
            dest_mac (str): Dirección MAC destino
            filepath (str): Ruta absoluta del archivo a enviar
            filename_for_header (str): Nombre/ruta relativa a usar en el paquete FILE_START
        """
        if not os.path.exists(filepath):
            print(f"[ERROR] El archivo '{filepath}' no existe.")
            return
        
        try:
            file_size = os.path.getsize(filepath)
        except Exception as e:
            print(f"[ERROR] No se pudo obtener el tamaño de '{filepath}': {e}")
            return
        
        # Usar filename_for_header en lugar de basename
        filename_bytes = filename_for_header.encode('utf-8')
        filename_len = len(filename_bytes)
        
        # Construir el payload para FILE_START
        filename_len_bytes = struct.pack('!H', filename_len)
        file_size_bytes = struct.pack('!Q', file_size)
        file_start_payload = filename_len_bytes + filename_bytes + file_size_bytes
        
        # Crear y enviar cabecera FILE_START
        file_start_header = protocol.LinkChatHeader.pack(protocol.PacketType.FILE_START, len(file_start_payload))
        file_start_packet = file_start_header + file_start_payload
        adapter.send_frame(dest_mac, file_start_packet)
        
        print(f"  → FILE_START: {filename_for_header} ({file_size} bytes)")
        
        # Enviar datos del archivo
        try:
            with open(filepath, 'rb') as file:
                bytes_sent = 0
                chunk_count = 0
                
                while True:
                    chunk = file.read(config.CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    chunk_count += 1
                    bytes_sent += len(chunk)
                    
                    file_data_header = protocol.LinkChatHeader.pack(protocol.PacketType.FILE_DATA, len(chunk))
                    file_data_packet = file_data_header + chunk
                    adapter.send_frame(dest_mac, file_data_packet)
                    
                    progress = (bytes_sent / file_size) * 100 if file_size > 0 else 100
                    print(f"    Enviando... {bytes_sent}/{file_size} bytes ({progress:.1f}%)")
            
            # FILE_END
            file_end_header = protocol.LinkChatHeader.pack(protocol.PacketType.FILE_END, 0)
            adapter.send_frame(dest_mac, file_end_header)
            print(f"  → FILE_END: {filename_for_header}")
            
        except Exception as e:
            print(f"[ERROR] Error al enviar '{filepath}': {e}")
    
    def send_folder(self, adapter, dest_mac: str, folder_path: str):
        """
        Envía una carpeta completa (estructura y archivos) a través de la red.
        
        Flujo de envío de carpetas:
        1. Se recorre recursivamente la carpeta origen usando walk_folder (ver folder_utils.py).
        2. Por cada evento:
           - FOLDER_START: Se envía un paquete FOLDER_START con la ruta relativa de la carpeta.
           - FILE: Se envía el archivo preservando la ruta relativa.
           - FOLDER_END: Se envía un paquete FOLDER_END para indicar el cierre de la carpeta actual.
        3. Todo el proceso se ejecuta en un hilo para no bloquear la CLI.
        
        Args:
            adapter: Instancia de NetworkAdapter para enviar tramas
            dest_mac (str): Dirección MAC destino
            folder_path (str): Ruta de la carpeta a enviar
        """
        
        def _send():
            base_path = os.path.abspath(folder_path)
            
            for event, relpath in folder_utils.walk_folder(folder_path):
                if event == 'FOLDER_START':
                    # Payload: 2 bytes longitud + ruta relativa UTF-8
                    rel_bytes = relpath.encode('utf-8')
                    payload = struct.pack('!H', len(rel_bytes)) + rel_bytes
                    header = protocol.LinkChatHeader.pack(protocol.PacketType.FOLDER_START, len(payload))
                    adapter.send_frame(dest_mac, header + payload)
                    print(f"→ FOLDER_START: {relpath if relpath else '(raíz)'}")
                    
                elif event == 'FILE':
                    # Construir ruta absoluta del archivo
                    abs_file = os.path.join(base_path, relpath)
                    
                    # IMPORTANTE: Enviar con ruta relativa preservada
                    self._send_file_with_path(adapter, dest_mac, abs_file, relpath)
                    
                elif event == 'FOLDER_END':
                    header = protocol.LinkChatHeader.pack(protocol.PacketType.FOLDER_END, 0)
                    adapter.send_frame(dest_mac, header)
                    print(f"→ FOLDER_END: {relpath if relpath else '(raíz)'}")

        thread = threading.Thread(target=_send, daemon=True)
        thread.start()
        print(f"[INFO] Enviando carpeta '{folder_path}' a {dest_mac} en segundo plano...")
