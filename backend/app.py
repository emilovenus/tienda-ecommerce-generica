import os,sqlite3
from flask import Flask,jsonify,request,session
from werkzeug.security import generate_password_hash,check_password_hash
from database import get_db,init_db
app=Flask(__name__); app.secret_key=os.getenv("SECRET_KEY","change-this-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax")
def user():
    uid=session.get("uid")
    if not uid:return None
    c=get_db(); r=c.execute("SELECT id,name,email,role FROM users WHERE id=?",(uid,)).fetchone(); c.close()
    return dict(r) if r else None
def auth():
    u=user()
    if not u:return None, (jsonify(error="Autenticación requerida"),401)
    return u,None
@app.get("/api/health")
def health():return jsonify(status="ok",service="ecommerce")
@app.post("/api/auth/register")
def register():
    d=request.get_json() or {}; name=d.get("name","").strip(); email=d.get("email","").strip().lower(); pw=d.get("password","")
    if not name or not email or len(pw)<8:return jsonify(error="Datos inválidos; contraseña mínima de 8 caracteres"),400
    c=get_db()
    try:
        cur=c.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",(name,email,generate_password_hash(pw))); c.commit(); session["uid"]=cur.lastrowid
        return jsonify(message="Usuario registrado",user=user()),201
    except sqlite3.IntegrityError:return jsonify(error="El correo ya está registrado"),409
    finally:c.close()
@app.post("/api/auth/login")
def login():
    d=request.get_json() or {}; c=get_db(); r=c.execute("SELECT * FROM users WHERE email=?",(d.get("email","").lower(),)).fetchone(); c.close()
    if not r or not check_password_hash(r["password_hash"],d.get("password","")):return jsonify(error="Credenciales incorrectas"),401
    session.clear(); session["uid"]=r["id"]; return jsonify(user=user())
@app.post("/api/auth/logout")
def logout():session.clear(); return jsonify(message="Sesión cerrada")
@app.get("/api/auth/me")
def me():return jsonify(user=user())
@app.get("/api/products")
def products():
    q=request.args.get("search",""); cat=request.args.get("category",""); c=get_db()
    sql="SELECT * FROM products WHERE active=1"; p=[]
    if q:sql+=" AND (name LIKE ? OR description LIKE ?)";p += [f"%{q}%",f"%{q}%"]
    if cat:sql+=" AND category=?";p.append(cat)
    r=c.execute(sql,p).fetchall(); c.close(); return jsonify(products=[dict(x) for x in r])
@app.get("/api/categories")
def categories():
    c=get_db(); r=c.execute("SELECT DISTINCT category FROM products WHERE active=1 ORDER BY category").fetchall(); c.close()
    return jsonify(categories=[x["category"] for x in r])
@app.post("/api/orders")
def order():
    u,e=auth()
    if e:return e
    items=(request.get_json() or {}).get("items",[])
    if not items:return jsonify(error="Carrito vacío"),400
    c=get_db()
    try:
        c.execute("BEGIN"); total=0; checked=[]
        for i in items:
            p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(int(i["product_id"]),)).fetchone(); q=int(i["quantity"])
            if not p or q<=0 or p["stock"]<q:raise ValueError("Producto no disponible o stock insuficiente")
            total+=p["price"]*q;checked.append((p,q))
        cur=c.execute("INSERT INTO orders(user_id,total,status) VALUES(?,?,?)",(u["id"],total,"pending"))
        for p,q in checked:
            c.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)",(cur.lastrowid,p["id"],q,p["price"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(q,p["id"]))
        c.commit();return jsonify(order_id=cur.lastrowid,total=round(total,2),status="pending"),201
    except ValueError as x:c.rollback();return jsonify(error=str(x)),400
    finally:c.close()
@app.get("/api/orders")
def orders():
    u,e=auth()
    if e:return e
    c=get_db(); rows=c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall(); out=[]
    for r in rows:
        it=c.execute("SELECT oi.quantity,oi.price,p.name FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?",(r["id"],)).fetchall()
        out.append({**dict(r),"items":[dict(x) for x in it]})
    c.close();return jsonify(orders=out)
@app.post("/api/products")
def create_product():
    u,e=auth()
    if e:return e
    if u["role"]!="admin":return jsonify(error="Se requiere administrador"),403
    d=request.get_json() or {}; c=get_db()
    cur=c.execute("INSERT INTO products(name,description,price,category,stock,image) VALUES(?,?,?,?,?,?)",(d["name"],d.get("description",""),float(d["price"]),d["category"],int(d["stock"]),d.get("image","")));c.commit()
    r=c.execute("SELECT * FROM products WHERE id=?",(cur.lastrowid,)).fetchone();c.close();return jsonify(product=dict(r)),201
if __name__=="__main__":init_db();app.run("0.0.0.0",5000)
else:init_db()
