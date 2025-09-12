import subprocess
def escanear_arp(interface='eth0'):
    print("Escaneando hosts activos en la LAN...")
    resultado = subprocess.getoutput(f"arp -n")
    hosts = []
    for linea in resultado.splitlines():
        if 'ether' in linea or 'HWaddress' in linea:
            partes = linea.split()
            if len(partes) >= 3:
                ip = partes[0]
                mac = partes[2]
                hosts.append((ip, mac))
    print("Dispositivos detectados:")
    for ip, mac in hosts:
        print(f"IP: {ip} | MAC: {mac}")
    return hosts
from .ethernet import send_frame, receive_frame
from .file_transfer import send_file, receive_file
from .checksum import calcular_checksum, verificar_checksum

def mostrar_menu():
    print("=== Menú de Mensajería ===")
    print("1. Enviar mensaje")
    print("2. Enviar archivo")
    print("3. Recibir mensaje")
    print("4. Recibir archivo")
    print("5. Escanear hosts LAN")
    print("6. Enviar mensaje broadcast")
    print("7. Salir")

def seleccionar_mac():
    mac_destino = input("Ingrese la dirección MAC de destino (formato: XX:XX:XX:XX:XX:XX): ")
    return mac_destino

def enviar_mensaje(mac_destino, mensaje=None):
    if mensaje is None:
        mensaje = input("Ingrese el mensaje a enviar: ").encode()
    else:
        if not isinstance(mensaje, bytes):
            mensaje = str(mensaje).encode()
    checksum = calcular_checksum(mensaje)
    datos = bytes([checksum]) + mensaje
    send_frame(mac_destino, datos)
    print(f"Mensaje enviado a {mac_destino}")

def enviar_archivo(mac_destino, ruta_archivo=None):
    if ruta_archivo is None:
        ruta_archivo = input("Ingrese la ruta del archivo a enviar: ")
    send_file(mac_destino, ruta_archivo)

def main():
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
            mac_origen, datos = receive_frame(timeout=3)
            if datos is None:
                print("No se recibió ningún mensaje.")
            else:
                checksum_recibido = datos[0]
                mensaje = datos[1:]
                if verificar_checksum(mensaje, checksum_recibido):
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
            from .ethernet import BROADCAST_MAC
            send_frame(BROADCAST_MAC, datos)
            print("Mensaje broadcast enviado.")
        elif opcion == '7':
            print("Saliendo de la aplicación.")
            break
        else:
            print("Opción no válida. Intente de nuevo.")

if __name__ == "__main__":
    main()