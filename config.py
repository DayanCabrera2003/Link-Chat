"""
Configuración de constantes para Link-Chat
Aplicación de chat y transferencia de archivos en Capa 2 (Enlace de Datos)
"""

# EtherType personalizado para identificar nuestros paquetes en la red
# Valor: 0x1234 - Se usa en la trama Ethernet para distinguir nuestro protocolo
# de otros protocolos (IP: 0x0800, ARP: 0x0806, etc.)
ETHTYPE_CUSTOM = 0x1234

# Dirección MAC de broadcast para enviar mensajes a todos los dispositivos
# en el segmento de red local. Todos los bits en 1 (ff:ff:ff:ff:ff:ff)
# permite que todas las interfaces de red reciban el paquete
BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'

# Tamaño de los fragmentos de archivo en bytes para la transferencia
# 1024 bytes (1 KB) es un tamaño óptimo que permite:
# - Fragmentación eficiente de archivos grandes
# - Evitar exceder el MTU (Maximum Transmission Unit) de Ethernet (1500 bytes)
# - Balance entre eficiencia y manejo de errores
CHUNK_SIZE = 1024
