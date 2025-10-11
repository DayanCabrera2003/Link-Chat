

# 🧩 Link-Chat — Mejoras en Fiabilidad de Transferencia de Archivos

## 📄 Descripción General

Esta actualización mejora la fiabilidad de la transferencia de archivos en Link-Chat al añadir confirmaciones (ACKs), verificación de integridad mediante checksum, y reintentos automáticos en caso de error o pérdida de fragmentos.

Todo esto se implementa usando solo la librería estándar de Python, sin dependencias externas.

---

## ⚙️ Objetivos de la mejora

* 📬 Confirmar que cada fragmento (FILE_DATA) fue recibido correctamente por el destino.
* 🔁 Reenviar fragmentos automáticamente si no se recibe confirmación (ACK) en un tiempo determinado.
* 🧮 Verificar integridad de cada fragmento mediante checksum SHA-256.
* 🧱 Mantener compatibilidad completa con la estructura actual del protocolo (Protocol.py).
* 🧰 Usar solo librerías estándar (sin requests, hashlib y struct son suficientes).

---

## 🧠 Cambios principales

### 1. Nuevo tipo de paquete

Se añadió un nuevo tipo de paquete en Protocol.py dentro de la clase PacketType:

class PacketType(Enum):
    ...
    ACK = 0x07  # Confirmación de recepción de fragmento
📘 Propósito: Indicar al emisor que un fragmento (FILE_DATA) fue recibido correctamente.

---

### 2. Cálculo de checksum

Cada fragmento enviado ahora incluye un checksum SHA-256 calculado con hashlib.

Formato del payload de FILE_DATA modificado:

[32 bytes] checksum SHA-256
[N bytes]  datos del fragmento
📗 Ejemplo:

import hashlib

checksum = hashlib.sha256(chunk).digest()
file_data_payload = checksum + chunk
Esto permite que el receptor valide la integridad del fragmento antes de confirmarlo.

---

### 3. Confirmación (ACK)

Después de recibir y validar un fragmento (FILE_DATA), el receptor envía un paquete ACK con esta estructura:

[4 bytes] Número de secuencia del fragmento confirmado (unsigned int)
📘 Ejemplo de envío:

ack_payload = struct.pack('!I', seq_num)
ack_header = protocol.LinkChatHeader.pack(protocol.PacketType.ACK, len(ack_payload))
adapter.send_frame(src_mac, ack_header + ack_payload)
---

### 4. Retransmisión automática

El emisor mantiene un diccionario de fragmentos enviados y espera confirmación (ACK) para cada uno.
Si no llega el ACK dentro de config.ACK_TIMEOUT (por ejemplo, 1.5 s), el fragmento se reenvía automáticamente hasta un máximo de config.MAX_RETRIES.

📘 Variables añadidas en config.py:

ACK_TIMEOUT = 1.5       # Tiempo máximo de espera por ACK (segundos)
MAX_RETRIES = 3         # Número máximo de reintentos por fragmento
---

### 5. Recepción con validación

Cuando el receptor recibe un FILE_DATA:

1. Extrae el checksum (32 bytes) y los datos reales.
2. Calcula el checksum del contenido.
3. Si coincide:

   * Guarda los datos en el archivo.
   * Envía ACK con el número de fragmento correspondiente.
4. Si no coincide:

   * Ignora el fragmento (no envía ACK, el emisor lo reintentará).

📗 Ejemplo:

recv_checksum = content[:32]
data = content[32:]
calc_checksum = hashlib.sha256(data).digest()

if recv_checksum == calc_checksum:
    # OK → escribir en archivo y enviar ACK
else:
    print("[Advertencia] Fragmento corrupto, se solicitará reenvío automático.")
---

### 6. Lógica de envío robusta

El método send_file() en Lógica de aplicación ahora:

* Asigna un número de secuencia (seq_num) a cada fragmento.
* Espera su ACK antes de continuar.
* Si no llega el ACK → reenvía hasta MAX_RETRIES.
* Si falla todos los intentos → cancela transferencia y muestra error.

📘 Ejemplo simplificado:

Ronal, [11/10/25 2:57]
for seq_num, chunk in enumerate(chunks):
    send_fragment(seq_num)
    if not wait_for_ack(seq_num, timeout=config.ACK_TIMEOUT):
        retries += 1
        if retries > config.MAX_RETRIES:
            print(f"[Error] Fragmento {seq_num} no confirmado tras {config.MAX_RETRIES} intentos.")
            break
---

## 📊 Flujo de transferencia (resumen)

1️⃣ Emisor → FILE_START
2️⃣ Emisor → FILE_DATA (con checksum + seq_num)
3️⃣ Receptor → Calcula checksum y envía ACK(seq_num)
4️⃣ Emisor → Espera ACK
     ├─ Si lo recibe: envía siguiente fragmento
     └─ Si no: reintenta hasta MAX_RETRIES
5️⃣ Emisor → FILE_END
6️⃣ Receptor → Cierra archivo, confirma recepción completa
---

## 🧾 Mensajes de consola agregados

Durante la transferencia, verás mensajes más detallados:

* En el emisor:

 
  📤 Fragmento #3 enviado (4096 bytes) [OK]
  🔁 Reintentando fragmento #3 (intento 2/3)...
  ✅ Fragmento #3 confirmado correctamente.
  
* En el receptor:

 
  📥 Fragmento #3 recibido correctamente (checksum válido)
  ⚠️ Fragmento #3 corrupto. Se solicitará reenvío.
  
---

## 🧰 Librerías utilizadas

Solo módulos estándar de Python:

| Módulo      | Uso                                         |
| ----------- | ------------------------------------------- |
| struct    | Empaquetar cabeceras y números de secuencia |
| hashlib   | Cálculo de checksum SHA-256                 |
| time      | Control de espera y temporización de ACK    |
| threading | Sincronización de envío/recepción           |
| os        | Acceso a archivos                           |
| enum      | Tipos de paquete                            |

---

