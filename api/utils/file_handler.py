import os
import tempfile
import shutil
from loguru import logger

def get_writable_temp_dir():
    """Obtiene un directorio temporal que permite escritura"""
    try:
        # Intenta primero /tmp que suele estar disponible para escritura
        if os.access('/tmp', os.W_OK):
            temp_dir = '/tmp/laplace_uploads'
            os.makedirs(temp_dir, exist_ok=True)
            return temp_dir
        
        # Si no está disponible, usa el directorio temporal del sistema
        return tempfile.gettempdir()
    except:
        # Último recurso: usar el directorio actual
        return os.getcwd()

def safe_remove_file(file_path):
    """Elimina un archivo sin lanzar excepciones si falla"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except OSError as e:
        logger.warning(f"No se pudo eliminar el archivo {file_path}: {e}")
    return False

class TempFileManager:
    """Gestor de archivos temporales que asegura la limpieza"""
    
    def __init__(self):
        self.temp_dir = get_writable_temp_dir()
        self.files = []
    
    def create_temp_file(self, prefix="upload_", suffix=""):
        """Crea un archivo temporal y devuelve la ruta"""
        try:
            fd, path = tempfile.mkstemp(dir=self.temp_dir, prefix=prefix, suffix=suffix)
            os.close(fd)
            self.files.append(path)
            return path
        except:
            # Si falla, crear un nombre aleatorio en el directorio
            import uuid
            path = os.path.join(self.temp_dir, f"{prefix}{uuid.uuid4()}{suffix}")
            self.files.append(path)
            return path
    
    def cleanup(self):
        """Limpia todos los archivos temporales creados"""
        for file_path in self.files:
            safe_remove_file(file_path)
        self.files = []