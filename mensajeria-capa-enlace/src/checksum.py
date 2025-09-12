
def calcular_checksum(data):
    """Calcula un checksum simple sumando los valores ASCII de los bytes."""
    return sum(data) % 256

def verificar_checksum(data, checksum):
    """Verifica si el checksum calculado coincide con el proporcionado."""
    return calcular_checksum(data) == checksum