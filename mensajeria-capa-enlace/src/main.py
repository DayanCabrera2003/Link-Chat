import os
import sys
from .menu import (
    mostrar_menu, seleccionar_mac, enviar_mensaje, enviar_archivo,
    receive_frame, receive_file, escanear_arp, calcular_checksum
)


def main():
    # Modo automático por argumentos para pruebas
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "send_msg" and len(sys.argv) >= 4:
            mac_destino = sys.argv[2]
            mensaje = sys.argv[3]
            enviar_mensaje(mac_destino, mensaje)
        elif cmd == "send_file" and len(sys.argv) >= 4:
            mac_destino = sys.argv[2]
            ruta = sys.argv[3]
            enviar_archivo(mac_destino, ruta)
        elif cmd == "recv_msg":
            print("Esperando mensaje...")
            # Permitir timeout personalizado por argumento
            timeout = 3
            if len(sys.argv) > 2 and sys.argv[2].startswith('--timeout'):
                try:
                    timeout = int(sys.argv[2].split('=')[1])
                except Exception:
                    pass
            mac_origen, datos = receive_frame(timeout=timeout)
            if datos is None:
                print("No se recibió ningún mensaje.")
            else:
                checksum_recibido = datos[0]
                mensaje = datos[1:]
                if calcular_checksum(mensaje) == checksum_recibido:
                    print(f"Mensaje recibido de {mac_origen}: {mensaje.decode(errors='ignore')}")
                else:
                    print("¡Error de integridad! El checksum no coincide.")
        elif cmd == "recv_file" and len(sys.argv) >= 3:
            ruta_destino = sys.argv[2]
            receive_file(ruta_destino)
        elif cmd == "scan":
            escanear_arp()
        elif cmd == "broadcast" and len(sys.argv) >= 3:
            mensaje = sys.argv[2].encode()
            checksum = calcular_checksum(mensaje)
            datos = bytes([checksum]) + mensaje
            from .ethernet import BROADCAST_MAC, send_frame
            send_frame(BROADCAST_MAC, datos)
            print("Mensaje broadcast enviado.")
        else:
            print("Comando automático no válido o faltan argumentos.")
        return

    # Modo interactivo (menú)
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ")

        if opcion == '1':
            mac_destino = seleccionar_mac()
            enviar_mensaje(mac_destino)

        elif opcion == '2':
            mac_destino = seleccionar_mac()
            enviar_archivo(mac_destino)

        elif opcion == '3':
            print("Esperando mensaje...")
            mac_origen, datos = receive_frame()
            checksum_recibido = datos[0]
            mensaje = datos[1:]
            if calcular_checksum(mensaje) == checksum_recibido:
                print(f"Mensaje recibido de {mac_origen}: {mensaje.decode(errors='ignore')}")
            else:
                print("¡Error de integridad! El checksum no coincide.")

        elif opcion == '4':
            ruta_destino = input("Ingrese la ruta donde guardar el archivo recibido: ")
            receive_file(ruta_destino)

        elif opcion == '5':
            escanear_arp()

        elif opcion == '6':
            mensaje = input("Mensaje a enviar por broadcast: ").encode()
            checksum = calcular_checksum(mensaje)
            datos = bytes([checksum]) + mensaje
            from .ethernet import BROADCAST_MAC, send_frame
            send_frame(BROADCAST_MAC, datos)
            print("Mensaje broadcast enviado.")

        elif opcion == '7':
            print("Saliendo de la aplicación.")
            break

        else:
            print("Opción no válida. Intente de nuevo.")
if __name__ == "__main__":
    main()