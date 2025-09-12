# Mensajería a Nivel de Capa de Enlace

Este proyecto es una aplicación de mensajería y transferencia de archivos que opera a nivel de capa de enlace en una red local. La aplicación permite la comunicación directa entre dos PCs utilizando tramas Ethernet, sin depender de protocolos de capa de red superior como TCP/UDP o HTTP.

## Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

```
mensajeria-capa-enlace
├── src
│   ├── main.py          # Punto de entrada de la aplicación.
│   ├── ethernet.py      # Manejo de la comunicación a nivel de capa de enlace.
│   ├── file_transfer.py  # Lógica de transferencia de archivos.
│   ├── checksum.py      # Funciones para verificar la integridad de los datos.
│   └── menu.py         # Interfaz de consola básica.
├── Dockerfile           # Instrucciones para construir la imagen de Docker.
├── README.md            # Documentación del proyecto.
└── requirements.txt     # Dependencias del proyecto (sin dependencias externas).
```

## Funcionalidades

- **Mensajería punto a punto**: Permite la comunicación directa entre dos PCs en la misma LAN utilizando tramas Ethernet.
- **Transferencia de archivos**: Soporta la fragmentación de archivos en tramas y su reensamblaje en el destino.
- **Verificación de integridad**: Implementa un checksum simple para asegurar la integridad de los datos transferidos.
- **Interfaz de consola básica**: Proporciona un menú textual para seleccionar la MAC de destino, enviar mensajes, enviar archivos y salir de la aplicación.

## Ejecución

La aplicación puede ejecutarse en dos entornos:

1. **Docker**: Utilizando el archivo `Dockerfile`, se puede construir una imagen de Docker que permite la ejecución en un contenedor con red en modo bridge y acceso a NET_RAW.
2. **LAN física**: La aplicación puede ejecutarse directamente en dos PCs conectados a la misma red local.

### Ejecución en Docker

1. Construye la imagen:
   ```sh
   docker build -t link-chat .
   ```
2. Ejecuta el contenedor con privilegios NET_RAW y en modo bridge:
   ```sh
   docker run --rm -it --cap-add=NET_RAW --network bridge link-chat
   ```

### Ejecución en LAN física

1. Instala Python 3 en ambos PCs.
2. Ejecuta el programa como root:
   ```sh
   sudo python src/main.py
   ```
3. Asegúrate de que ambos equipos estén conectados a la misma red física y conozcan sus direcciones MAC.

## Instalación

Para instalar y ejecutar el proyecto, siga estos pasos:

1. Clonar el repositorio.
2. Navegar al directorio del proyecto.
3. (Opcional) Construir la imagen de Docker utilizando el `Dockerfile`.
4. Ejecutar el archivo `src/main.py` para iniciar la aplicación.

## Uso

Una vez que la aplicación esté en ejecución, se presentará un menú en la consola donde podrá:

- Seleccionar la dirección MAC de destino.
- Enviar un mensaje.
- Enviar un archivo.
- Salir de la aplicación.

## Notas

- El programa requiere permisos elevados para usar sockets RAW.
- La comunicación es directa por tramas Ethernet, sin usar TCP/UDP/HTTP.
- Puedes enviar y recibir mensajes y archivos entre dos PCs en la misma LAN.
- Este proyecto está diseñado para funcionar sin dependencias externas, utilizando únicamente la biblioteca estándar de Python.