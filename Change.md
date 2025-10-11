# 📘 Actualización de Fiabilidad en Transferencia de Archivos – Link-Chat

## 🧩 Descripción General

Esta actualización mejora el sistema de envío de archivos del proyecto **Link-Chat**, añadiendo **fiabilidad a nivel de fragmento**.  
El nuevo mecanismo implementa **ACK/NACK**, **checksum CRC32**, y **retransmisión automática** en caso de errores o pérdida de paquetes.  

Todo se desarrolló **usando solo librerías estándar de Python**, sin dependencias externas, y se integró en los archivos existentes:  
`protocol.py` y `app_logic.py`.

---

## 🧠 Objetivos Técnicos

| Objetivo | Descripción |
|-----------|-------------|
| ✅ Confirmaciones | Confirmar la recepción exitosa de cada fragmento con `ACK`. |
| ⚠️ Reenvío automático | Reenviar fragmentos dañados o perdidos con `NACK` o `timeout`. |
| 🔒 Integridad | Verificar cada bloque con checksum CRC32 (`zlib.crc32`). |
| 🧩 Compatibilidad | Mantener estructura existente del proyecto (sin romper `Main.py`). |
| 💬 Transparencia | Mostrar mensajes detallados en consola sobre progreso y errores. |

---

## 📂 Archivos Modificados

| Archivo | Descripción |
|----------|--------------|
| `protocol.py` | Se añadieron nuevos tipos de paquete (`FILE_ACK` y `FILE_NACK`). |
| `app_logic.py` | Se implementaron el control de reintentos, confirmaciones, y validación CRC32. |

---

## ⚙️ Detalles de Implementación

### 1. Nuevos tipos de paquete (`protocol.py`)

Se agregaron dos nuevos tipos para la comunicación de estado de fragmentos:

```python
class PacketType(Enum):
    FILE_ACK = 0x07     # Confirmación de fragmento recibido correctamente
    FILE_NACK = 0x08    # Aviso de fragmento dañado o perdido
```

Esto permite distinguir si un fragmento fue aceptado (`ACK`) o rechazado (`NACK`).

---

### 2. Estructura de un fragmento (`FILE_DATA`)

Cada fragmento de archivo se envía con la siguiente estructura binaria:

| Campo | Tamaño | Descripción |
|-------|---------|-------------|
| `seq_num` | 2 bytes | Número de secuencia del fragmento |
| `checksum` | 4 bytes | Checksum CRC32 del contenido |
| `data` | Variable | Datos reales del fragmento |

Ejemplo de empaquetado:

```python
seq_num, checksum = struct.unpack('!HI', content[:6])
chunk_data = content[6:]
```

---

### 3. Cálculo y validación del checksum (CRC32)

Antes de enviar cada fragmento:

```python
checksum = zlib.crc32(chunk)
chunk_payload = struct.pack('!HI', seq, checksum) + chunk
```

En el destino, el receptor recalcula el CRC32 y lo compara:

```python
calc_checksum = zlib.crc32(chunk_data)
if calc_checksum != checksum:
    self._send_ack(src_mac, seq_num, success=False)
```

Si hay diferencia → se envía un `FILE_NACK`.

---

### 4. Confirmación por fragmento (ACK/NACK)

Cada fragmento correctamente recibido genera un **ACK**, mientras que uno dañado genera un **NACK**.

```python
def _send_ack(self, dest_mac, seq_num, success=True):
    pkt_type = protocol.PacketType.FILE_ACK if success else protocol.PacketType.FILE_NACK
    payload = struct.pack('!H', seq_num)
    header = protocol.LinkChatHeader.pack(pkt_type, len(payload))
    self.adapter.send_frame(dest_mac, header + payload)
    print(f"↩️ Enviado {'ACK' if success else 'NACK'} para fragmento #{seq_num}.")
```

---

### 5. Retransmisión automática

Si un fragmento no recibe `ACK` o recibe `NACK`, el emisor lo reenvía automáticamente.

```python
for attempt in range(MAX_RETRIES):
    with self.lock:
        self.pending_acks[seq_num] = None

    adapter.send_frame(dest_mac, packet)

    start_time = time.time()
    while time.time() - start_time < ACK_TIMEOUT:
        with self.lock:
            status = self.pending_acks.get(seq_num)
        if status is not None:
            if status:
                print(f"✅ ACK recibido para fragmento #{seq_num}")
                return
            else:
                print(f"❌ NACK recibido, reintentando fragmento #{seq_num}")
                break
        time.sleep(0.1)
```

Si tras 3 intentos no se confirma, se aborta la transferencia de ese fragmento:

```python
print(f"🚨 No se pudo confirmar fragmento #{seq_num} tras {MAX_RETRIES} intentos.")
```

---

### 6. Control concurrente seguro con `threading.Lock()`

El diccionario `pending_acks` guarda los fragmentos pendientes de confirmación.  
Para evitar condiciones de carrera entre hilos emisores y receptores, se usa un **bloqueo (`Lock`)**:

```python
self.lock = threading.Lock()
```

y cada acceso se protege con `with self.lock:`.

---

### 7. Indicadores visuales en consola

Durante el envío y recepción se muestran estados detallados:

**En el emisor:**
```
🚀 Enviando 'archivo.zip' (1.2 MB) a [AA:BB:CC:DD:EE:FF]...
📤 Fragmento #3 enviado (4096 bytes) [27.1%]
✅ ACK recibido para fragmento #3
⚠️ Timeout esperando ACK de fragmento #5 (intento 2/3)
```

**En el receptor:**
```
📥 Iniciando recepción de 'archivo.zip' (1.2 MB)
✅ Recibido fragmento #3 (4096 bytes) [27.1%]
↩️ Enviado ACK para fragmento #3
⚠️ Checksum incorrecto en fragmento #4 → solicitando reenvío
```

---

### 8. Flujo general de transferencia (actualizado)

```
1️⃣ Emisor → FILE_START
2️⃣ Emisor → FILE_DATA (#1)
3️⃣ Receptor → Verifica CRC32 → envía ACK o NACK
4️⃣ Emisor → Espera ACK → reintenta si es necesario
5️⃣ Emisor → FILE_END
6️⃣ Receptor → Cierra archivo y confirma finalización
```

---

## 🧰 Parámetros configurables

| Parámetro | Valor | Descripción |
|------------|--------|-------------|
| `MAX_RETRIES` | 3 | Número máximo de reenvíos por fragmento |
| `ACK_TIMEOUT` | 2.0 s | Tiempo máximo para esperar confirmación |
| `config.CHUNK_SIZE` | Configurable | Tamaño de cada fragmento leído del archivo |

---

## 📦 Librerías estándar utilizadas

| Módulo | Propósito |
|---------|------------|
| `struct` | Empaquetado de datos binarios |
| `zlib` | Cálculo de checksum CRC32 |
| `os` | Gestión de archivos |
| `time` | Control de tiempos de espera |
| `threading` | Sincronización de ACK/NACK |
| `enum` | Definición de tipos de paquete |

---

## 🧩 Ventajas de esta implementación

- 🔁 **Fiabilidad garantizada** sin depender de TCP ni capas superiores.  
- 🧱 **Totalmente compatible** con Docker, red física o Wi-Fi.  
- ⚙️ **Modular y reutilizable**, con mínimo impacto en la arquitectura existente.  
- 📡 **Transparente al usuario final**, mostrando estado en tiempo real.  
- 🧠 **Simple de mantener**, sin dependencias externas ni librerías adicionales.

---

## 🚀 Resultado

Con esta mejora, Link-Chat ahora soporta **transferencias de archivos confiables a nivel de Capa 2**, con detección automática de errores y retransmisión controlada, manteniendo la simplicidad y el rendimiento original del sistema.
