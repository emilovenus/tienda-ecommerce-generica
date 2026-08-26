import os

import psycopg2

from flask import (
    Flask,
    jsonify,
    request,
    session,
    send_from_directory
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from backend.database import get_db, init_db


app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)


# =========================================================
# USUARIO ACTUAL
# =========================================================

def user():

    uid = session.get("uid")

    if not uid:
        return None

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT id, name, email, role
                FROM users
                WHERE id=%s
                """,
                (uid,)
            )

            r = cur.fetchone()

            return dict(r) if r else None

    finally:

        c.close()


def auth():

    u = user()

    if not u:

        return None, (
            jsonify(
                error="Autenticación requerida"
            ),
            401
        )

    return u, None


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():

    return jsonify(
        status="ok",
        service="ecommerce"
    )


# =========================================================
# REGISTRO
# =========================================================

@app.post("/api/auth/register")
def register():

    d = request.get_json() or {}

    name = d.get("name", "").strip()
    email = d.get("email", "").strip().lower()
    pw = d.get("password", "")

    if not name or not email or len(pw) < 8:

        return jsonify(
            error="Datos inválidos; contraseña mínima de 8 caracteres"
        ), 400

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                INSERT INTO users(
                    name,
                    email,
                    password_hash
                )
                VALUES(%s,%s,%s)
                RETURNING id
                """,
                (
                    name,
                    email,
                    generate_password_hash(pw)
                )
            )

            user_id = cur.fetchone()["id"]

            account_number = (
                f"4582{user_id:08d}"
            )

            initial_balance = 5000.00

            cur.execute(
                """
                INSERT INTO accounts(
                    user_id,
                    account_number,
                    balance
                )
                VALUES(%s,%s,%s)
                """,
                (
                    user_id,
                    account_number,
                    initial_balance
                )
            )

        c.commit()

        session.clear()
        session["uid"] = user_id

        return jsonify(
            message="Usuario registrado",
            user=user(),
            bank={
                "bank": "NovaBank",
                "account_number": account_number,
                "balance": initial_balance
            }
        ), 201

    except psycopg2.IntegrityError:

        c.rollback()

        return jsonify(
            error="El correo ya está registrado"
        ), 409

    finally:

        c.close()


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/auth/login")
def login():

    d = request.get_json() or {}

    email = d.get(
        "email",
        ""
    ).lower()

    password = d.get(
        "password",
        ""
    )

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT *
                FROM users
                WHERE email=%s
                """,
                (email,)
            )

            r = cur.fetchone()

    finally:

        c.close()

    if (
        not r
        or not check_password_hash(
            r["password_hash"],
            password
        )
    ):

        return jsonify(
            error="Credenciales incorrectas"
        ), 401

    session.clear()
    session["uid"] = r["id"]

    return jsonify(
        user=user()
    )


# =========================================================
# LOGOUT
# =========================================================

@app.post("/api/auth/logout")
def logout():

    session.clear()

    return jsonify(
        message="Sesión cerrada"
    )


# =========================================================
# SESIÓN
# =========================================================

@app.get("/api/auth/me")
def me():

    return jsonify(
        user=user()
    )


# =========================================================
# NOVABANK
# =========================================================

@app.get("/api/bank")
def bank():

    u, e = auth()

    if e:
        return e

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT account_number, balance
                FROM accounts
                WHERE user_id=%s
                """,
                (u["id"],)
            )

            r = cur.fetchone()

    finally:

        c.close()

    if not r:

        return jsonify(
            error="Cuenta NovaBank no encontrada"
        ), 404

    return jsonify(
        account_number=r["account_number"],
        balance=float(r["balance"])
    )


# =========================================================
# PRODUCTOS
# =========================================================

@app.get("/api/products")
def products():

    q = request.args.get(
        "search",
        ""
    )

    cat = request.args.get(
        "category",
        ""
    )

    c = get_db()

    try:

        sql = """
            SELECT *
            FROM products
            WHERE active=1
        """

        params = []

        if q:

            sql += """
                AND (
                    name ILIKE %s
                    OR description ILIKE %s
                )
            """

            params.extend([
                f"%{q}%",
                f"%{q}%"
            ])

        if cat:

            sql += """
                AND category=%s
            """

            params.append(cat)

        sql += " ORDER BY id"

        with c.cursor() as cur:

            cur.execute(
                sql,
                params
            )

            rows = cur.fetchall()

            return jsonify(
                products=[
                    dict(x)
                    for x in rows
                ]
            )

    finally:

        c.close()


# =========================================================
# CATEGORÍAS
# =========================================================

@app.get("/api/categories")
def categories():

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT DISTINCT category
                FROM products
                WHERE active=1
                ORDER BY category
                """
            )

            rows = cur.fetchall()

            return jsonify(
                categories=[
                    x["category"]
                    for x in rows
                ]
            )

    finally:

        c.close()


# =========================================================
# CREAR PEDIDO / COBRO NOVABANK
# =========================================================

@app.post("/api/orders")
def order():

    u, e = auth()

    if e:
        return e

    items = (
        request.get_json() or {}
    ).get(
        "items",
        []
    )

    if not items:

        return jsonify(
            error="Carrito vacío"
        ), 400

    c = get_db()

    try:

        with c.cursor() as cur:

            total = 0
            checked = []

            # -------------------------------------------------
            # VERIFICAR PRODUCTOS
            # -------------------------------------------------

            for i in items:

                product_id = int(
                    i["product_id"]
                )

                quantity = int(
                    i["quantity"]
                )

                cur.execute(
                    """
                    SELECT *
                    FROM products
                    WHERE id=%s
                    AND active=1
                    FOR UPDATE
                    """,
                    (product_id,)
                )

                p = cur.fetchone()

                if (
                    not p
                    or quantity <= 0
                    or p["stock"] < quantity
                ):

                    raise ValueError(
                        "Producto no disponible o stock insuficiente"
                    )

                total += (
                    float(p["price"])
                    * quantity
                )

                checked.append(
                    (p, quantity)
                )

            total = round(
                total,
                2
            )

            # -------------------------------------------------
            # CUENTA NOVABANK
            # -------------------------------------------------

            cur.execute(
                """
                SELECT *
                FROM accounts
                WHERE user_id=%s
                FOR UPDATE
                """,
                (u["id"],)
            )

            account = cur.fetchone()

            if not account:

                raise ValueError(
                    "El usuario no tiene una cuenta NovaBank"
                )

            balance_before = float(
                account["balance"]
            )

            # -------------------------------------------------
            # VERIFICAR SALDO
            # -------------------------------------------------

            if balance_before < total:

                raise ValueError(
                    f"Saldo insuficiente. "
                    f"Saldo disponible: "
                    f"${balance_before:.2f}"
                )

            balance_after = round(
                balance_before - total,
                2
            )

            # -------------------------------------------------
            # DESCONTAR DINERO
            # -------------------------------------------------

            cur.execute(
                """
                UPDATE accounts
                SET balance=%s
                WHERE id=%s
                """,
                (
                    balance_after,
                    account["id"]
                )
            )

            # -------------------------------------------------
            # CREAR PEDIDO
            # -------------------------------------------------

            cur.execute(
                """
                INSERT INTO orders(
                    user_id,
                    total,
                    status
                )
                VALUES(%s,%s,%s)
                RETURNING id
                """,
                (
                    u["id"],
                    total,
                    "paid"
                )
            )

            order_id = cur.fetchone()["id"]

            # -------------------------------------------------
            # PRODUCTOS DEL PEDIDO
            # -------------------------------------------------

            for p, quantity in checked:

                cur.execute(
                    """
                    INSERT INTO order_items(
                        order_id,
                        product_id,
                        quantity,
                        price
                    )
                    VALUES(%s,%s,%s,%s)
                    """,
                    (
                        order_id,
                        p["id"],
                        quantity,
                        p["price"]
                    )
                )

                cur.execute(
                    """
                    UPDATE products
                    SET stock=stock-%s
                    WHERE id=%s
                    """,
                    (
                        quantity,
                        p["id"]
                    )
                )

            # -------------------------------------------------
            # TRANSACCIÓN NOVABANK
            # -------------------------------------------------

            cur.execute(
                """
                INSERT INTO transactions(
                    account_id,
                    order_id,
                    type,
                    amount,
                    balance_before,
                    balance_after,
                    description
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    account["id"],
                    order_id,
                    "purchase",
                    total,
                    balance_before,
                    balance_after,
                    f"Compra NovaStore #{order_id}"
                )
            )

        c.commit()

        return jsonify(
            order_id=order_id,
            total=total,
            status="paid",
            payment="NovaBank",
            balance_before=balance_before,
            balance_after=balance_after
        ), 201

    except ValueError as x:

        c.rollback()

        return jsonify(
            error=str(x)
        ), 400

    except Exception as x:

        c.rollback()

        return jsonify(
            error="Error procesando el pago: " + str(x)
        ), 500

    finally:

        c.close()


# =========================================================
# PEDIDOS
# =========================================================

@app.get("/api/orders")
def orders():

    u, e = auth()

    if e:
        return e

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT *
                FROM orders
                WHERE user_id=%s
                ORDER BY id DESC
                """,
                (u["id"],)
            )

            rows = cur.fetchall()

            out = []

            for r in rows:

                cur.execute(
                    """
                    SELECT
                        oi.quantity,
                        oi.price,
                        p.name
                    FROM order_items oi
                    JOIN products p
                        ON p.id=oi.product_id
                    WHERE oi.order_id=%s
                    """,
                    (r["id"],)
                )

                it = cur.fetchall()

                out.append({
                    **dict(r),
                    "items": [
                        dict(x)
                        for x in it
                    ]
                })

            return jsonify(
                orders=out
            )

    finally:

        c.close()


# =========================================================
# MOVIMIENTOS NOVABANK
# =========================================================

@app.get("/api/transactions")
def transactions():

    u, e = auth()

    if e:
        return e

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                SELECT
                    t.id,
                    t.order_id,
                    t.type,
                    t.amount,
                    t.balance_before,
                    t.balance_after,
                    t.description,
                    t.created_at
                FROM transactions t
                JOIN accounts a
                    ON a.id=t.account_id
                WHERE a.user_id=%s
                ORDER BY t.id DESC
                """,
                (u["id"],)
            )

            rows = cur.fetchall()

            return jsonify(
                transactions=[
                    dict(x)
                    for x in rows
                ]
            )

    finally:

        c.close()


# =========================================================
# CREAR PRODUCTO
# =========================================================

@app.post("/api/products")
def create_product():

    u, e = auth()

    if e:
        return e

    if u["role"] != "admin":

        return jsonify(
            error="Se requiere administrador"
        ), 403

    d = request.get_json() or {}

    c = get_db()

    try:

        with c.cursor() as cur:

            cur.execute(
                """
                INSERT INTO products(
                    name,
                    description,
                    price,
                    category,
                    stock,
                    image
                )
                VALUES(%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (
                    d["name"],
                    d.get(
                        "description",
                        ""
                    ),
                    float(
                        d["price"]
                    ),
                    d["category"],
                    int(
                        d["stock"]
                    ),
                    d.get(
                        "image",
                        ""
                    )
                )
            )

            product = cur.fetchone()

        c.commit()

        return jsonify(
            product=dict(product)
        ), 201

    finally:

        c.close()


# =========================================================
# FRONTEND
# =========================================================

FRONTEND_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    "frontend"
)


@app.get("/")
def frontend_index():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.get("/<path:filename>")
def frontend_files(filename):

    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# =========================================================
# INICIO
# =========================================================

init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
