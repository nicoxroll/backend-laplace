import os
import psycopg2
from dotenv import load_dotenv

def run_migrations():
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener credenciales
    db_host = os.getenv("POSTGRES_HOST", "db")
    db_name = os.getenv("POSTGRES_DB", "laplace")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )
    conn.autocommit = True
    
    try:
        # Obtener lista de archivos SQL ordenados
        migration_dir = os.path.join(os.path.dirname(__file__), "migrations", "sql")
        if not os.path.exists(migration_dir):
            migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
            
        sql_files = [f for f in os.listdir(migration_dir) if f.endswith('.sql')]
        sql_files.sort()  # Esto ordenará 001_*, 002_*, etc.
        
        cursor = conn.cursor()
        
        # Crear tabla para seguimiento de migraciones si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_history (
                file_name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ejecutar cada archivo SQL en orden
        for sql_file in sql_files:
            # Verificar si esta migración ya fue aplicada
            cursor.execute("SELECT COUNT(*) FROM migration_history WHERE file_name = %s", (sql_file,))
            if cursor.fetchone()[0] > 0:
                print(f"Omitiendo migración ya aplicada: {sql_file}")
                continue
            
            print(f"Ejecutando migración: {sql_file}")
            file_path = os.path.join(migration_dir, sql_file)
            
            try:
                with open(file_path, 'r') as f:
                    sql = f.read()
                    cursor.execute(sql)
                
                # Registrar que la migración fue aplicada exitosamente
                cursor.execute("INSERT INTO migration_history (file_name) VALUES (%s)", (sql_file,))
                print(f"Migración exitosa: {sql_file}")
                
            except psycopg2.errors.DuplicateTable as e:
                print(f"Advertencia en {sql_file}: {str(e).strip()}")
                conn.rollback()  # Rollback la transacción fallida
                
                # Aun así registramos la migración como aplicada para no intentarla de nuevo
                cursor.execute("INSERT INTO migration_history (file_name) VALUES (%s)", (sql_file,))
                conn.commit()
                
            except Exception as e:
                print(f"Error en migración {sql_file}: {str(e)}")
                conn.rollback()
                raise
        
        print("Todas las migraciones completadas exitosamente")
    
    finally:
        conn.close()

if __name__ == "__main__":
    run_migrations()