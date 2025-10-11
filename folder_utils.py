"""
Utilidades para serialización y recorrido de carpetas en Link-Chat

Flujo de serialización de carpetas para envío:
--------------------------------------------------
1. walk_folder(folder_path) recorre recursivamente la carpeta origen.
2. Por cada carpeta encontrada:
    - Genera un evento ('FOLDER_START', ruta_relativa)
    - Para cada archivo, genera ('FILE', ruta_relativa)
    - Para cada subcarpeta, recursivamente repite el proceso.
    - Al terminar la carpeta, genera ('FOLDER_END', ruta_relativa)
3. El generador produce los eventos en el orden correcto para reconstrucción.

Esto permite que el emisor y receptor mantengan la jerarquía de carpetas y archivos.
"""

import os
from typing import Generator, Tuple

def walk_folder(folder_path: str, base_path: str = None) -> Generator[Tuple[str, str], None, None]:
    """
    Recorre recursivamente una carpeta, generando eventos ordenados para envío.
    
    Args:
        folder_path (str): Ruta absoluta o relativa de la carpeta a recorrer.
        base_path (str, opcional): Ruta base para calcular rutas relativas. Si es None, se usa folder_path.
    
    Yields:
        tuple: (evento, ruta_relativa)
            - evento: 'FOLDER_START', 'FILE', 'FOLDER_END'
            - ruta_relativa: Ruta relativa respecto a base_path
    
    Ejemplo de uso:
        for event, relpath in walk_folder('mi_carpeta'):
            print(event, relpath)
    """
    if base_path is None:
        base_path = os.path.abspath(folder_path)
    
    folder_path = os.path.abspath(folder_path)
    rel_folder = os.path.relpath(folder_path, base_path)
    if rel_folder == '.':
        rel_folder = ''
    
    # Evento de inicio de carpeta
    yield ('FOLDER_START', rel_folder)
    
    # Listar contenido ordenado: carpetas primero, luego archivos (alfabéticamente)
    entries = sorted(os.listdir(folder_path))
    dirs = [e for e in entries if os.path.isdir(os.path.join(folder_path, e))]
    files = [e for e in entries if os.path.isfile(os.path.join(folder_path, e))]
    
    # Archivos
    for fname in files:
        rel_file = os.path.join(rel_folder, fname) if rel_folder else fname
        yield ('FILE', rel_file)
    
    # Subcarpetas (recursivo)
    for dname in dirs:
        subfolder = os.path.join(folder_path, dname)
        yield from walk_folder(subfolder, base_path)
    
    # Evento de fin de carpeta
    yield ('FOLDER_END', rel_folder)
