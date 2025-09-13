from .ethernet import send_frame, receive_frame, send_ack, wait_for_ack, BROADCAST_MAC

# Tamaño máximo de datos por trama Ethernet (1500 bytes típico - 14 bytes cabecera)
MAX_FRAME_DATA = 1500 - 14

def split_file(file_path):
    """
    Divide el archivo en fragmentos del tamaño de una trama Ethernet.
    Devuelve una lista de fragmentos (bytes).
    """
    fragments = []
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(MAX_FRAME_DATA)
            if not data:
                break
            fragments.append(data)
    return fragments

def assemble_file(fragments, dest_path):
    """
    Une los fragmentos y reconstruye el archivo original.
    """
    with open(dest_path, 'wb') as f:
        for frag in fragments:
            f.write(frag)

def send_file(mac_dest, file_path, interface='eth0', use_ack=True, broadcast=False):
    """
    Fragmenta y envía el archivo o mensaje por tramas Ethernet.
    """
    fragments = split_file(file_path)
    total = len(fragments)
    print(f"Enviando archivo '{file_path}' en {total} fragmentos...")
    for i, frag in enumerate(fragments, 1):  # Empieza en 1
        header = f"{i}/{total}".encode().ljust(32, b'\x00')
        data = header + frag
        dest = BROADCAST_MAC if broadcast else mac_dest
        intentos = 0
        enviado = False
        while not enviado and intentos < 3:
            send_frame(dest, data)
            if use_ack and not broadcast:
                if wait_for_ack(interface=interface):
                    enviado = True
                else:
                    print(f"No se recibió ACK para fragmento {i}, reenviando...")
                    intentos += 1
            else:
                enviado = True
    print("Archivo/mensaje enviado.")

def receive_file(dest_path, interface='eth0', expect_ack=True, timeout=10):
    """
    Recibe fragmentos y reconstruye el archivo o mensaje.
    """
    fragment_dict = {}
    received = 0
    total_frag = None
    while True:
        mac_origin, data = receive_frame(interface=interface, timeout=timeout)
        if data is None:
            print(f"No se recibió ningún fragmento en {timeout} segundos. Abortando recepción.")
            break
        header = data[:32].decode(errors='ignore').strip('\x00')
        try:
            frag_num, total_frag = map(int, header.split('/'))
        except Exception:
            print("Error al interpretar el encabezado del fragmento. Abortando.")
            break
        fragment_dict[frag_num] = data[32:]
        received += 1
        print(f"Recibido fragmento {frag_num}/{total_frag}")
        if expect_ack:
            send_ack(mac_origin, interface=interface)
        if received >= total_frag:
            break
    if fragment_dict:
        # Ensamblar en orden
        fragments = [fragment_dict[i] for i in range(1, total_frag+1) if i in fragment_dict]
        assemble_file(fragments, dest_path)
        print(f"Archivo/mensaje reconstruido en '{dest_path}'")
    else:
        print("No se pudo reconstruir el archivo/mensaje: no se recibieron fragmentos.")
def fragmentar_archivo(ruta_archivo, tamano_fragmento):
    fragmentos = []
    with open(ruta_archivo, 'rb') as archivo:
        while True:
            fragmento = archivo.read(tamano_fragmento)
            if not fragmento:
                break
            fragmentos.append(fragmento)
    return fragmentos

def reensamblar_archivo(fragmentos, ruta_destino):
    with open(ruta_destino, 'wb') as archivo:
        for fragmento in fragmentos:
            archivo.write(fragmento)

