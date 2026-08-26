import os
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada")

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )


def init_db():

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'customer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    price NUMERIC(10,2) NOT NULL,
                    category TEXT NOT NULL,
                    stock INTEGER NOT NULL DEFAULT 0,
                    image TEXT DEFAULT '',
                    active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    total NUMERIC(10,2) NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    price NUMERIC(10,2) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                    account_number TEXT NOT NULL UNIQUE,
                    balance NUMERIC(12,2) NOT NULL DEFAULT 5000.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    order_id INTEGER REFERENCES orders(id),
                    type TEXT NOT NULL,
                    amount NUMERIC(10,2) NOT NULL,
                    balance_before NUMERIC(12,2) NOT NULL,
                    balance_after NUMERIC(12,2) NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM products
            """)

            total = cur.fetchone()["total"]

            if total == 0:

                products = [
                    (
                        "Audífonos Nova",
                        "Audífonos inalámbricos con estuche.",
                        799,
                        "Tecnología",
                        15,
                        "/images/audifonos.jpg"
                    ),
                    (
                        "Teclado Mecánico RGB",
                        "Teclado compacto.",
                        1199,
                        "Tecnología",
                        10,
                        "/images/teclado.jpg"
                    ),
                    (
                        "Mochila Urbana",
                        "Mochila resistente.",
                        649,
                        "Accesorios",
                        20,
                        "/images/mochila.jpg"
                    ),
                    (
                        "Sudadera Essential",
                        "Sudadera unisex.",
                        599,
                        "Ropa",
                        12,
                        "/images/sudadera.jpg"
                    ),
                    (
                        "Botella Térmica",
                        "Acero inoxidable, 750 ml.",
                        399,
                        "Hogar",
                        25,
                        "/images/botella.jpg"
                    )
                ]

                cur.executemany("""
                    INSERT INTO products
                    (
                        name,
                        description,
                        price,
                        category,
                        stock,
                        image
                    )
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, products)

        c.commit()

    finally:

        c.close()
