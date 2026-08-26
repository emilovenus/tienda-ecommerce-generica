import sqlite3
from pathlib import Path
DB=Path("/app/data/store.db")
def get_db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def init_db():
    c=get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'customer',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT DEFAULT '',price REAL NOT NULL,category TEXT NOT NULL,stock INTEGER NOT NULL DEFAULT 0,image TEXT DEFAULT '',active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,total REAL NOT NULL,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,product_id INTEGER NOT NULL,quantity INTEGER NOT NULL,price REAL NOT NULL,FOREIGN KEY(order_id) REFERENCES orders(id),FOREIGN KEY(product_id) REFERENCES products(id));
    """)
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0]==0:
        c.executemany("INSERT INTO products(name,description,price,category,stock,image) VALUES(?,?,?,?,?,?)",[
        ("Audífonos Nova","Audífonos inalámbricos con estuche.",799,"Tecnología",15,"https://placehold.co/600x400?text=Audifonos"),
        ("Teclado Mecánico RGB","Teclado compacto.",1199,"Tecnología",10,"https://placehold.co/600x400?text=Teclado"),
        ("Mochila Urbana","Mochila resistente.",649,"Accesorios",20,"https://placehold.co/600x400?text=Mochila"),
        ("Sudadera Essential","Sudadera unisex.",599,"Ropa",12,"https://placehold.co/600x400?text=Sudadera"),
        ("Botella Térmica","Acero inoxidable, 750 ml.",399,"Hogar",25,"https://placehold.co/600x400?text=Botella")])
    c.commit(); c.close()
