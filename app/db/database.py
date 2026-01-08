import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

def get_db_connection(dbname=None):
    return psycopg2.connect(
        host=DB_HOST,
        database=dbname or DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def init_db():
    target_db = DB_NAME
    
    # Connect to default 'postgres' db to check/create target db
    conn = psycopg2.connect(
        host=DB_HOST,
        database='postgres',
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {target_db}")
            print(f"Database {target_db} created.")
    finally:
        cursor.close()
        conn.close()

    # Now connect to target db to create table
    conn = get_db_connection(target_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengeluaran (
            id INTEGER PRIMARY KEY,
            description TEXT,
            category TEXT,
            expenses NUMERIC,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add column if it doesn't exist (for existing DBs)
    cursor.execute("ALTER TABLE pengeluaran ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
    cursor.close()
    conn.close()
