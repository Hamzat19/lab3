import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "lab3",
    "user": "postgres",
    "password": "",     
    "host": "localhost",
    "port": 5432,
}

def q(sql, params=(), fetch=True):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()