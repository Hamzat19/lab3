import os
from dotenv import load_dotenv
load_dotenv()                            # ← ДО чтения os.getenv

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME", "lab3"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

def q(sql, params=(), fetch=True):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()