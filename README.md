# 💬 Link-Chat

> **Chat y transferencia de archivos en Capa 2 (Enlace de Datos) usando Python puro**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Network](https://img.shields.io/badge/Network-Layer%202-orange.svg)
![Status](https://img.shields.io/badge/Status-Functional-success.svg)

Link-Chat es una aplicación de mensajería y transferencia de archivos que opera directamente en la **Capa 2 del modelo OSI** (Enlace de Datos), sin usar TCP/IP. Se comunica usando **tramas Ethernet crudas** y un **protocolo personalizado**, demostrando los fundamentos de las redes de bajo nivel.

---

## 📚 Tabla de Contenidos

- [¿Qué es Link-Chat?](#-qué-es-link-chat)
- [Teoría de Redes](#-teoría-de-redes)
  - [Modelo OSI y Capa 2](#modelo-osi-y-capa-2)
  - [Tramas Ethernet](#tramas-ethernet)
  - [Protocolo Link-Chat](#protocolo-link-chat)
- [Características](#-características)
- [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Guía de Uso](#-guía-de-uso)
- [Ejemplos Prácticos](#-ejemplos-prácticos)
- [Limitaciones Conocidas](#-limitaciones-conocidas)
- [Troubleshooting](#-troubleshooting)
- [Pruebas y Diagnóstico](#-pruebas-y-diagnóstico)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)

---

## 🎯 ¿Qué es Link-Chat?

Link-Chat es una aplicación educativa que demuestra la comunicación en **red a nivel de enlace de datos** (Capa 2 del modelo OSI). A diferencia de las aplicaciones de chat tradicionales que usan TCP/IP (Capas 3 y 4), Link-Chat opera directamente sobre Ethernet.

### ¿Por qué es especial?

- 🚀 **Sin TCP/IP**: No usa protocolos de red estándar (IP, TCP, UDP)
- 🔧 **Raw Sockets**: Acceso directo a la interfaz de red
- 📦 **Protocolo Personalizado**: Implementación de un protocolo propio desde cero
- 🐍 **Python Puro**: Solo biblioteca estándar, sin dependencias externas
- 🎓 **Educativo**: Perfecto para entender redes de bajo nivel

---

## 📖 Teoría de Redes

### Modelo OSI y Capa 2

El **modelo OSI** (Open Systems Interconnection) divide la comunicación en red en 7 capas:

```
┌─────────────────────────────────────────┐
│  7. Aplicación    (HTTP, FTP, SMTP)    │  ← Aplicaciones normales
├─────────────────────────────────────────┤
│  6. Presentación  (SSL, ASCII)          │
├─────────────────────────────────────────┤
│  5. Sesión        (NetBIOS, RPC)        │
├─────────────────────────────────────────┤
│  4. Transporte    (TCP, UDP)            │  ← Comunicación normal
├─────────────────────────────────────────┤
│  3. Red           (IP, ICMP, ARP)       │
├─────────────────────────────────────────┤
│  2. Enlace        (Ethernet, WiFi)      │  ← ¡Link-Chat opera aquí!
├─────────────────────────────────────────┤
│  1. Física        (Cables, ondas)       │
└─────────────────────────────────────────┘
```

**Link-Chat opera en la Capa 2**, lo que significa:

- ✅ Comunicación directa mediante **direcciones MAC**
- ✅ Solo funciona en la **red local** (mismo segmento)
- ✅ **No necesita** direcciones IP ni routing
- ✅ Máximo control sobre el formato de datos

### Tramas Ethernet

Una **trama Ethernet** es la unidad básica de datos en Capa 2:

```
┌──────────────┬──────────────┬────────────┬──────────┬─────┐
│  MAC Destino │  MAC Origen  │ EtherType  │ Payload  │ FCS │
│   (6 bytes)  │  (6 bytes)   │ (2 bytes)  │ (Datos)  │(4 B)│
└──────────────┴──────────────┴────────────┴──────────┴─────┘
```

**Ejemplo de trama Link-Chat:**

```
┌────────────────────┬────────────────────┬──────────┬─────────────────┐
│ ff:ff:ff:ff:ff:ff  │ ec:8e:77:1c:d9:6e  │  0x1234  │  [Datos Chat]   │
│   (Broadcast)      │   (Mi MAC)         │ (Custom) │                 │
└────────────────────┴────────────────────┴──────────┴─────────────────┘
```

**Componentes:**

1. **MAC Destino**: Dirección física del destinatario
   - `ff:ff:ff:ff:ff:ff` = Broadcast (todos los dispositivos)
   - `aa:bb:cc:dd:ee:ff` = Unicast (dispositivo específico)

2. **MAC Origen**: Tu dirección MAC (asignada por el fabricante)

3. **EtherType**: Identifica el protocolo (`0x1234` para Link-Chat)
   - `0x0800` = IPv4
   - `0x0806` = ARP
   - `0x1234` = Link-Chat (personalizado)

4. **Payload**: Los datos del mensaje o archivo

### Protocolo Link-Chat

Link-Chat define su propio protocolo de aplicación dentro del payload Ethernet:

#### Estructura del Protocolo

```
┌──────────────────────────┬───────────────────────────────┐
│   Cabecera Link-Chat     │         Contenido             │
│       (3 bytes)          │       (Variable)              │
└──────────────────────────┴───────────────────────────────┘

Cabecera (3 bytes):
┌─────────────┬──────────────────────┐
│ Tipo Pkt    │  Longitud Payload    │
│  (1 byte)   │     (2 bytes)        │
└─────────────┴──────────────────────┘
```

#### Tipos de Paquetes

| Tipo | Código | Descripción | Payload |
|------|--------|-------------|---------|
| **TEXT** | `0x01` | Mensaje de texto | String UTF-8 |
| **FILE_START** | `0x02` | Inicio de archivo | Nombre + tamaño |
| **FILE_DATA** | `0x03` | Fragmento de archivo | Datos binarios |
| **FILE_END** | `0x04` | Fin de archivo | Vacío |
| **DISCOVERY_REQUEST** | `0x05` | Buscar dispositivos | Nombre de usuario |
| **DISCOVERY_RESPONSE** | `0x06` | Respuesta descubrimiento | Nombre de usuario |

#### Ejemplo: Mensaje de Texto

```python
# Paso 1: Crear cabecera Link-Chat
mensaje = "Hola mundo"
mensaje_bytes = mensaje.encode('utf-8')  # 10 bytes

cabecera = [
    0x01,        # Tipo: TEXT
    0x00, 0x0A   # Longitud: 10 bytes (big-endian)
]

# Paso 2: Construir payload completo
payload_linkchat = cabecera + mensaje_bytes
# [0x01, 0x00, 0x0A, 'H', 'o', 'l', 'a', ' ', 'm', 'u', 'n', 'd', 'o']

# Paso 3: Construir trama Ethernet
trama = [
    MAC_destino,        # 6 bytes
    MAC_origen,         # 6 bytes  
    0x12, 0x34,        # EtherType Link-Chat
    payload_linkchat   # Cabecera + mensaje
]

# Paso 4: Enviar por raw socket
socket.send(trama)
```

#### Ejemplo: Transferencia de Archivo

La transferencia de archivos usa una secuencia de 3 tipos de paquetes:

```
┌──────────────┐
│ FILE_START   │  → Metadatos (nombre: "foto.jpg", tamaño: 2048 bytes)
└──────────────┘
       ↓
┌──────────────┐
│ FILE_DATA    │  → Fragmento 1 (1024 bytes)
└──────────────┘
       ↓
┌──────────────┐
│ FILE_DATA    │  → Fragmento 2 (1024 bytes)
└──────────────┘
       ↓
┌──────────────┐
│ FILE_END     │  → Señal de finalización
└──────────────┘
```

**Estructura del FILE_START:**

```
┌──────────────────────────────────────────────────────────┐
│ Cabecera Link-Chat (3 bytes)                             │
├──────────────────────────────────────────────────────────┤
│ Longitud nombre (2 bytes) │ Nombre archivo (N bytes)    │
├───────────────────────────┴──────────────────────────────┤
│ Tamaño total del archivo (8 bytes)                       │
└──────────────────────────────────────────────────────────┘
```

---

## ✨ Características

### 💬 Chat
- ✅ Mensajes broadcast (a todos)
- ✅ Mensajes unicast (a un dispositivo específico)
- ✅ Identificación por dirección MAC
- ✅ Sin necesidad de servidor central

### 📁 Transferencia de Archivos
- ✅ Envío de archivos de cualquier tipo
- ✅ Fragmentación automática (chunks de 1KB)
- ✅ Barra de progreso en tiempo real
- ✅ Recepción automática con prefijo `received_`

### 🔍 Descubrimiento de Dispositivos
- ✅ Protocolo discovery broadcast
- ✅ Respuesta automática con nombre de usuario
- ✅ Lista de dispositivos activos en la red

### 🛠️ Características Técnicas
- ✅ **Raw Sockets (AF_PACKET)**: Acceso directo a Ethernet
- ✅ **Protocolo Personalizado**: Diseño desde cero
- ✅ **Multithreading**: Listener asíncrono no bloqueante
- ✅ **Solo Python Estándar**: Sin dependencias externas
- ✅ **EtherType Personalizado**: `0x1234`

---

## 🏗️ Arquitectura del Proyecto

```
Link-Chat/
│
├── 📄 config.py              # Constantes de configuración
│   ├── ETHTYPE_CUSTOM        # EtherType personalizado (0x1234)
│   ├── BROADCAST_MAC         # MAC broadcast (ff:ff:ff:ff:ff:ff)
│   └── CHUNK_SIZE            # Tamaño fragmentos (1024 bytes)
│
├── 🛠️ utils.py               # Utilidades de red
│   ├── get_mac_address()     # Obtiene MAC local
│   └── find_network_interface() # Encuentra interfaz activa
│
├── 📡 protocol.py            # Definición del protocolo
│   ├── PacketType            # Enum de tipos de paquetes
│   └── LinkChatHeader        # Empaquetado/desempaquetado
│
├── 🔌 network_core.py        # Core de comunicación
│   ├── NetworkAdapter        # Manejo de raw sockets
│   │   ├── send_frame()      # Envío de tramas
│   │   └── receive_frame()   # Recepción de tramas
│   └── start_listener_thread() # Hilo de escucha
│
├── 🧠 app_logic.py           # Lógica de aplicación
│   └── PacketHandler         # Procesamiento de paquetes
│       ├── handle_packet()   # Callback para paquetes
│       └── send_file()       # Envío de archivos
│
├── 🎮 main.py                # Interfaz de usuario
│   └── main()                # Loop principal de comandos
│
└── 🧪 test_link_chat.py      # Suite de pruebas
    └── 10 tests automáticos
```

### Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                         ENVÍO                               │
└─────────────────────────────────────────────────────────────┘
                              
Usuario escribe comando
        ↓
main.py procesa entrada
        ↓
Crea cabecera Link-Chat (protocol.py)
        ↓
NetworkAdapter.send_frame() construye trama Ethernet
        ↓
socket.send() → Interfaz de red → Red física

┌─────────────────────────────────────────────────────────────┐
│                       RECEPCIÓN                             │
└─────────────────────────────────────────────────────────────┘

Red física → Interfaz de red
        ↓
NetworkAdapter.receive_frame() (en thread separado)
        ↓
Desempaqueta trama Ethernet
        ↓
PacketHandler.handle_packet() procesa según tipo
        ↓
Muestra mensaje o guarda archivo
```

---

## 📋 Requisitos

### Sistema Operativo
- 🐧 **Linux** (Ubuntu, Debian, Fedora, Arch, etc.)
- ⚠️ **Windows**: No soportado (AF_PACKET es específico de Linux)
- 🍎 **macOS**: No soportado (AF_PACKET no disponible)

### Python
- 🐍 **Python 3.8+**
- 📦 **Solo biblioteca estándar** (sin pip install)

### Permisos
- 👑 **Permisos de root (sudo)**: Requerido para raw sockets

### Red
- 🔌 **Ethernet**: Cable ethernet (recomendado)
- 📡 **WiFi**: Router doméstico (con limitaciones)
- ❌ **NO**: Hotspot móvil (aislamiento de clientes)

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/DayanCabrera2003/Link-Chat.git
cd Link-Chat
```

### 2. Verificar Python

```bash
python3 --version
# Debe ser 3.8 o superior
```

### 3. Dar permisos de ejecución (opcional)

```bash
chmod +x main.py
chmod +x test_link_chat.py
```

### 4. ¡Listo para usar!

No necesitas instalar dependencias. Todo usa la biblioteca estándar de Python.

---

## 📖 Guía de Uso

### Inicio Rápido

```bash
# IMPORTANTE: Requiere sudo para raw sockets
sudo python3 main.py
```

### Interfaz de Usuario

```
=== Link-Chat - Chat en Capa 2 ===
Inicializando...

✓ Interfaz de red encontrada: wlo1
✓ Adaptador de red inicializado
  Dirección MAC local: ec:8e:77:1c:d9:6e
✓ Manejador de paquetes creado
✓ Listener iniciado en segundo plano

Link-Chat está listo para usar.
Comandos disponibles:
  - discover: Descubrir dispositivos en la red local
  - broadcast <mensaje>: Enviar mensaje a todos
  - send <dest_mac> <mensaje>: Enviar mensaje a MAC específica
  - sendfile <dest_mac> <filepath>: Enviar archivo
  - status: Mostrar información del sistema
  - exit: Salir

> _
```

### Comandos Disponibles

#### 🔍 `discover` - Descubrir dispositivos

Busca otros dispositivos Link-Chat en la red local.

```bash
> discover
Ingresa tu nombre de usuario: Alice
✓ Solicitud de descubrimiento enviada como 'Alice' a la red
  Esperando respuestas...

👤 Usuario encontrado: 'Bob' en [08:00:27:7d:2b:8c]
```

**¿Cómo funciona?**
1. Envía un paquete `DISCOVERY_REQUEST` por broadcast
2. Otros dispositivos responden automáticamente con `DISCOVERY_RESPONSE`
3. Muestra lista de usuarios activos con sus MACs

#### 📢 `broadcast <mensaje>` - Mensaje a todos

Envía un mensaje a todos los dispositivos en la red local.

```bash
> broadcast Hola a todos!
✓ Mensaje broadcast enviado a toda la red

# Los demás verán:
💬 Mensaje de [ec:8e:77:1c:d9:6e]: Hola a todos!
```

**¿Cómo funciona?**
- Usa MAC destino `ff:ff:ff:ff:ff:ff` (broadcast)
- Todos los dispositivos en el mismo segmento reciben el mensaje
- Ideal para mensajes públicos

#### 💌 `send <dest_mac> <mensaje>` - Mensaje privado

Envía un mensaje a un dispositivo específico.

```bash
> send 08:00:27:7d:2b:8c Hola Bob, mensaje privado!
✓ Mensaje enviado a [08:00:27:7d:2b:8c]

# Bob verá:
💬 Mensaje de [ec:8e:77:1c:d9:6e]: Hola Bob, mensaje privado!
```

**¿Cómo funciona?**
- Usa la MAC específica del destinatario
- Solo ese dispositivo procesa el mensaje
- Más eficiente que broadcast

#### 📁 `sendfile <dest_mac> <filepath>` - Enviar archivo

Transfiere un archivo a otro dispositivo.

```bash
> sendfile 08:00:27:7d:2b:8c /home/user/foto.jpg

Iniciando transferencia de archivo...
✓ FILE_START enviado: 'foto.jpg' (2048576 bytes) -> [08:00:27:7d:2b:8c]
  Enviando... 1024/2048576 bytes (0.1%) - Fragmento #1
  Enviando... 2048/2048576 bytes (0.2%) - Fragmento #2
  ...
✓ Archivo 'foto.jpg' enviado completamente: 2000 fragmentos, 2048576 bytes
✓ FILE_END enviado. Transferencia de 'foto.jpg' completada.
✓ Transferencia completada exitosamente.

# Bob verá:
📥 Recibiendo archivo 'foto.jpg' (2048576 bytes) de [ec:8e:77:1c:d9:6e]...
  Recibiendo... 1024/2048576 bytes (0.1%)
  Recibiendo... 2048/2048576 bytes (0.2%)
  ...
✅ Archivo 'foto.jpg' recibido correctamente y guardado como 'received_foto.jpg'
```

**¿Cómo funciona?**
1. **FILE_START**: Envía metadatos (nombre, tamaño)
2. **FILE_DATA**: Envía fragmentos de 1024 bytes
3. **FILE_END**: Señala finalización
4. El receptor ensambla automáticamente el archivo

#### ℹ️ `status` - Información del sistema

Muestra el estado actual de Link-Chat.

```bash
> status

=== Estado del Sistema ===
Interfaz: wlo1
MAC local: ec:8e:77:1c:d9:6e
EtherType: 0x1234
Verbose: Desactivado
Transferencias activas: 0
Usuario: Alice
```

#### 🚪 `exit` - Salir

Cierra Link-Chat de forma ordenada.

```bash
> exit

Cerrando Link-Chat...
Link-Chat finalizado.
```

---

## 💡 Ejemplos Prácticos

### Escenario 1: Chat entre dos computadoras

**Configuración:**
```
[Laptop A] ──[Cable Ethernet]── [Laptop B]
   Alice                            Bob
```

**Laptop A (Alice):**
```bash
sudo python3 main.py

> discover
Ingresa tu nombre de usuario: Alice
✓ Solicitud enviada

👤 Usuario encontrado: 'Bob' en [08:00:27:7d:2b:8c]

> send 08:00:27:7d:2b:8c Hola Bob!
✓ Mensaje enviado

💬 Mensaje de [08:00:27:7d:2b:8c]: Hola Alice, ¿cómo estás?

> send 08:00:27:7d:2b:8c Bien, gracias!
✓ Mensaje enviado
```

**Laptop B (Bob):**
```bash
sudo python3 main.py

🔍 Solicitud de descubrimiento de 'Alice' [ec:8e:77:1c:d9:6e]
✓ Respuesta enviada como 'Bob'

💬 Mensaje de [ec:8e:77:1c:d9:6e]: Hola Bob!

> send ec:8e:77:1c:d9:6e Hola Alice, ¿cómo estás?
✓ Mensaje enviado

💬 Mensaje de [ec:8e:77:1c:d9:6e]: Bien, gracias!
```

### Escenario 2: Broadcast a múltiples dispositivos

**Configuración:**
```
[Laptop A] ─┐
            ├─ Switch Ethernet
[Laptop B] ─┤
            │
[Laptop C] ─┘
```

**Laptop A:**
```bash
> broadcast ¡Reunión en 5 minutos!
✓ Mensaje broadcast enviado a toda la red
```

**Laptop B y C reciben:**
```
💬 Mensaje de [ec:8e:77:1c:d9:6e]: ¡Reunión en 5 minutos!
```

### Escenario 3: Transferencia de archivo

**Laptop A (envía documento.pdf):**
```bash
> sendfile 08:00:27:7d:2b:8c /home/alice/documento.pdf

Iniciando transferencia de archivo...
✓ FILE_START enviado: 'documento.pdf' (524288 bytes)
  Enviando... 1024/524288 bytes (0.2%) - Fragmento #1
  Enviando... 2048/524288 bytes (0.4%) - Fragmento #2
  ...
  Enviando... 524288/524288 bytes (100.0%) - Fragmento #512
✓ Archivo enviado completamente: 512 fragmentos
✓ Transferencia completada
```

**Laptop B (recibe automáticamente):**
```bash
📥 Recibiendo archivo 'documento.pdf' (524288 bytes) de [ec:8e:77:1c:d9:6e]...
  Recibiendo... 1024/524288 bytes (0.2%)
  Recibiendo... 2048/524288 bytes (0.4%)
  ...
  Recibiendo... 524288/524288 bytes (100.0%)

✅ Archivo 'documento.pdf' recibido correctamente y guardado como 'received_documento.pdf'
```

El archivo se guarda automáticamente con el prefijo `received_` en el directorio actual.

---

## ⚠️ Limitaciones Conocidas

### 🌐 Red Local Únicamente

Link-Chat **solo funciona en la misma red local (LAN)**:

```
✅ Funciona:
   Laptop A ──[Mismo Switch/Router]── Laptop B

❌ NO funciona:
   Laptop A ──[Internet]── Laptop B (diferente red)
```

**Razón**: La Capa 2 no tiene routing. Los paquetes no cruzan routers.

### 📡 Problemas con WiFi

**Broadcast puede no funcionar en WiFi** debido a:

1. **Filtrado de EtherTypes personalizados**: Drivers WiFi filtran protocolos no estándar
2. **Modo de operación 802.11**: Diferencias con Ethernet cableado
3. **Puntos de acceso**: Pueden descartar paquetes desconocidos

**Solución**: Usa **cable Ethernet** o **comunicación unicast** directa.

### 📱 Hotspot Móvil NO Funciona

Los hotspots de celular tienen **aislamiento de clientes activado**:

```
❌ NO funciona:
   Laptop A ─┐
             ├─ 📱 Hotspot Celular
   Laptop B ─┘
   
   Las laptops NO se ven entre sí
```

**Razón**: El hotspot bloquea comunicación peer-to-peer por seguridad.

**Solución**: Usa router WiFi doméstico o cable Ethernet.

### 💻 Solo Linux

Link-Chat usa **AF_PACKET**, que es específico de Linux:

- ✅ **Linux**: Ubuntu, Debian, Fedora, Arch, etc.
- ❌ **Windows**: AF_PACKET no existe (usar WinPcap requeriría dependencias)
- ❌ **macOS**: AF_PACKET no disponible (usar BPF requeriría código específico)

### 🔒 Requiere Permisos de Root

Raw sockets requieren privilegios elevados:

```bash
# ❌ Error sin sudo
$ python3 main.py
✗ Error de permisos

# ✅ Correcto
$ sudo python3 main.py
✓ Link-Chat iniciado
```

---

## 🔧 Troubleshooting

### Problema: "No se encontró ninguna interfaz de red válida"

**Causa**: Solo existe la interfaz loopback (`lo`).

**Solución**:
```bash
# Verificar interfaces disponibles
ip link show

# Si solo aparece 'lo', conecta cable ethernet o activa WiFi
```

### Problema: "Error de permisos"

**Causa**: Raw sockets requieren root.

**Solución**:
```bash
sudo python3 main.py
```

### Problema: "Timeout: No se recibió respuesta"

**Causas posibles**:
1. Firewall bloqueando paquetes
2. Aislamiento de clientes activo
3. Hotspot móvil

**Solución**:
```bash
# Desactiva firewall temporalmente
sudo ufw disable

# O usa cable ethernet
```

### Problema: Broadcast no funciona

**Causa**: WiFi o hotspot.

**Solución**: Usa cable Ethernet o comunicación unicast (`send` en lugar de `broadcast`).

### Problema: Las laptops no se ven entre sí

**Diagnóstico**:
```bash
# Verifica conectividad básica
ping <IP_otra_laptop>

# Si ping falla, hay problema de red, no de Link-Chat
```

**Solución**: Verifica cables, switch, o configuración del router.

---

## 🧪 Pruebas y Diagnóstico

### Test Suite Automático

Ejecuta la suite completa de pruebas:

```bash
sudo python3 test_link_chat.py
```

**Salida esperada:**

```
======================================================================
                         LINK-CHAT TEST SUITE
======================================================================

1. VERIFICACIÓN DE PERMISOS
✓ Ejecutando con permisos de root

2. CONFIGURACIÓN BÁSICA
✓ Configuración cargada correctamente

3. DIRECCIÓN MAC
✓ Dirección MAC obtenida: ec:8e:77:1c:d9:6e

4. INTERFAZ DE RED
✓ Interfaz seleccionada: eth0

5. PROTOCOLO LINK-CHAT
✓ Protocolo empaqueta/desempaqueta correctamente

6. RAW SOCKET
✓ Raw socket creado

7. TEST LOOPBACK (CRÍTICO)
✓ ¡Paquete recibido correctamente!
✓✓✓ TEST LOOPBACK EXITOSO ✓✓✓

8. TEST BROADCAST
✓ Broadcast enviado

9. CAPTURA DE TRÁFICO
✓ La interfaz está activa

10. CLASE NETWORKADAPTER
✓ NetworkAdapter creado correctamente

======================================================================
                          RESUMEN DE PRUEBAS
======================================================================

Total: 10/10 pruebas exitosas (100%)

✓✓✓ ¡TODAS LAS PRUEBAS PASARON! ✓✓✓
```

### Test Rápido de Red

Verifica si hay aislamiento de clientes:

```bash
python3 quick_network_test.py
```

Este script detecta:
- ✅ Tipo de red (Ethernet, WiFi, hotspot)
- ✅ Aislamiento de clientes
- ✅ Conectividad entre dispositivos

### Modo Verbose

Para debugging detallado:

```bash
sudo python3 main.py --verbose
```

Muestra:
- 📡 Todos los paquetes recibidos
- 📤 Detalles de envío
- 🔍 Información de debugging

---

## 🎓 Conceptos Aprendidos

Al usar Link-Chat, aprenderás:

### Redes de Bajo Nivel
- ✅ Funcionamiento de la Capa 2 (Enlace de Datos)
- ✅ Estructura de tramas Ethernet
- ✅ Direcciones MAC vs direcciones IP
- ✅ Broadcast vs Unicast

### Programación de Redes
- ✅ Raw sockets en Linux
- ✅ Empaquetado/desempaquetado binario (`struct`)
- ✅ Diseño de protocolos personalizados
- ✅ Programación asíncrona con threads

### Conceptos Avanzados
- ✅ EtherTypes y su propósito
- ✅ Fragmentación de datos
- ✅ Manejo de errores en comunicación
- ✅ Limitaciones de diferentes capas OSI

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

### Cómo contribuir

1. **Fork** el repositorio
2. **Crea** una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abre** un Pull Request

### Ideas para contribuir

- 🔐 Encriptación de mensajes
- 📊 Interfaz gráfica (GUI)
- 🎨 Colores en la terminal
- 📜 Historial de mensajes
- 🔔 Notificaciones de sistema
- 🌍 Soporte para otros sistemas operativos

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

```
MIT License

Copyright (c) 2025 Dayan Cabrera

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👨‍💻 Autor

**Dayan Cabrera**
- GitHub: [@DayanCabrera2003](https://github.com/DayanCabrera2003)
- Proyecto: [Link-Chat](https://github.com/DayanCabrera2003/Link-Chat)

---

## 🙏 Agradecimientos

- Python Software Foundation por la excelente documentación
- Comunidad de redes de bajo nivel
- Todos los que prueban y contribuyen al proyecto

---



<div align="center">

### ⭐ Si te gustó el proyecto, dale una estrella en GitHub!

**Made with ❤️ and 🐍 by Dayan Cabrera**

</div>
