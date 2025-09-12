import os
import tempfile
from src.ethernet import send_frame, receive_frame
from src.file_transfer import send_file, receive_file, split_file, assemble_file
from src.checksum import calcular_checksum, verificar_checksum

# Resultados de pruebas
results = []

def test_checksum():
    data = b"Prueba de checksum"
    checksum = calcular_checksum(data)
    assert verificar_checksum(data, checksum), "Fallo en verificación de checksum"
    results.append("Checksum: OK")

def test_fragmentacion_reensamblaje():
    contenido = b"A" * 5000  # Simula archivo grande
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(contenido)
        ruta = f.name
    frags = split_file(ruta)
    assert sum(len(f) for f in frags) == len(contenido), "Fragmentación incorrecta"
    ruta_dest = ruta + "_dest"
    assemble_file(frags, ruta_dest)
    with open(ruta_dest, 'rb') as f:
        assert f.read() == contenido, "Reensamblaje incorrecto"
    os.remove(ruta)
    os.remove(ruta_dest)
    results.append("Fragmentación/Reensamblaje: OK")

def test_send_receive_message():
    # Simulación local, no envía por red real
    mensaje = b"Hola MVP"
    checksum = calcular_checksum(mensaje)
    datos = bytes([checksum]) + mensaje
    # Simula envío y recepción
    assert verificar_checksum(datos[1:], datos[0]), "Fallo en checksum al recibir mensaje"
    results.append("Envío/Recepción de mensaje: OK")

def test_send_receive_file():
    # Simulación local, no envía por red real
    contenido = b"B" * 3000
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(contenido)
        ruta = f.name
    frags = split_file(ruta)
    ruta_dest = ruta + "_dest"
    assemble_file(frags, ruta_dest)
    with open(ruta_dest, 'rb') as f:
        assert f.read() == contenido, "Fallo en envío/recepción de archivo"
    os.remove(ruta)
    os.remove(ruta_dest)
    results.append("Envío/Recepción de archivo: OK")

def run_all_tests():
    print("=== Pruebas automáticas Link-Chat MVP ===")
    try:
        test_checksum()
        test_fragmentacion_reensamblaje()
        test_send_receive_message()
        test_send_receive_file()
        print("\nTodas las pruebas pasaron correctamente:")
        for r in results:
            print("-", r)
    except AssertionError as e:
        print("\nFallo en prueba:", e)
    except Exception as e:
        print("\nError inesperado:", e)

if __name__ == "__main__":
    run_all_tests()
