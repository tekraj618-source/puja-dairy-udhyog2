import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "puja_dairy.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "owner")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

PRODUCTS = [
    ("Milk", "Fresh daily milk", 90, "per unit", "🥛"),
    ("Dahi", "Creamy traditional curd", 140, "per unit", "🥣"),
    ("Mahi", "Refreshing buttermilk", 70, "per unit", "🥛"),
    ("Paneer", "Fresh soft paneer", 800, "per unit", "🧀"),
    ("Butter", "Rich dairy butter", 1000, "per unit", "🧈"),
    ("Ghee", "Pure aromatic ghee", 1200, "per unit", "✨"),
    ("Cake 1 Pound", "Celebration cake", 700, "per cake", "🎂"),
    ("Cake Half Pound", "Small celebration cake", 550, "per cake", "🍰"),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        unit TEXT NOT NULL,
        icon TEXT NOT NULL,
        active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        items TEXT NOT NULL,
        total REAL NOT NULL,
        note TEXT,
        status TEXT DEFAULT 'New',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'Unread'
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        conn.executemany(
            "INSERT INTO products(name,description,price,unit,icon) VALUES(?,?,?,?,?)",
            PRODUCTS
        )
    conn.commit()
    conn.close()

def owner_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("owner"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_common():
    return {"shop_name": "Puja Dairy Udhyog", "phone": "9766100969", "email": "tekraj618@gmail.com"}

@app.route("/")
def home():
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    return render_template("index.html", products=products)

@app.route("/products")
def products():
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    return render_template("products.html", products=products)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/delivery")
def delivery():
    return render_template("delivery.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not phone or not message:
            flash("Please fill in your name, phone and message.", "error")
        else:
            conn = db()
            conn.execute(
                "INSERT INTO inquiries(name,phone,email,message,created_at) VALUES(?,?,?,?,?)",
                (name, phone, email, message, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()
            conn.close()
            flash("Your message has been sent. We will contact you soon.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/order", methods=["GET", "POST"])
def order():
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        items = request.form.get("items", "").strip()
        total = request.form.get("total", "0")
        note = request.form.get("note", "").strip()
        if not name or not phone or not address or not items:
            flash("Please complete the required delivery details.", "error")
            return render_template("order.html", products=products)
        try:
            total_num = float(total)
        except ValueError:
            total_num = 0
        conn = db()
        cur = conn.execute(
            "INSERT INTO orders(customer_name,phone,address,items,total,note,created_at) VALUES(?,?,?,?,?,?,?)",
            (name, phone, address, items, total_num, note,
             datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()
        return render_template("order_success.html", order_id=order_id, name=name)
    return render_template("order.html", products=products)

@app.route("/track", methods=["GET", "POST"])
def track():
    result = None
    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()
        phone = request.form.get("phone", "").strip()
        conn = db()
        result = conn.execute(
            "SELECT * FROM orders WHERE id=? AND phone=?", (order_id, phone)
        ).fetchone()
        conn.close()
        if not result:
            flash("No matching order was found.", "error")
    return render_template("track.html", result=result)

@app.route("/owner/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(generate_password_hash(ADMIN_PASSWORD), password):
            session["owner"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid owner login.", "error")
    return render_template("login.html")

@app.route("/owner/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/owner")
@owner_required
def dashboard():
    conn = db()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    inquiries = conn.execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    stats = {
        "orders": conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
        "new_orders": conn.execute("SELECT COUNT(*) c FROM orders WHERE status='New'").fetchone()["c"],
        "messages": conn.execute("SELECT COUNT(*) c FROM inquiries").fetchone()["c"],
        "unread": conn.execute("SELECT COUNT(*) c FROM inquiries WHERE status='Unread'").fetchone()["c"],
    }
    conn.close()
    return render_template("dashboard.html", orders=orders, inquiries=inquiries, products=products, stats=stats)

@app.post("/owner/order/<int:order_id>/status")
@owner_required
def order_status(order_id):
    status = request.form.get("status", "New")
    allowed = {"New", "Confirmed", "Preparing", "Out for Delivery", "Delivered", "Cancelled"}
    if status in allowed:
        conn = db()
        conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))

@app.post("/owner/message/<int:message_id>/read")
@owner_required
def message_read(message_id):
    conn = db()
    conn.execute("UPDATE inquiries SET status='Read' WHERE id=?", (message_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.post("/owner/product/<int:product_id>")
@owner_required
def product_update(product_id):
    price = request.form.get("price", "")
    active = 1 if request.form.get("active") == "on" else 0
    try:
        price = float(price)
    except ValueError:
        flash("Invalid price.", "error")
        return redirect(url_for("dashboard"))
    conn = db()
    conn.execute("UPDATE products SET price=?, active=? WHERE id=?", (price, active, product_id))
    conn.commit()
    conn.close()
    flash("Product price/status updated.", "success")
    return redirect(url_for("dashboard"))

@app.get("/api/products")
def api_products():
    conn = db()
    rows = conn.execute("SELECT id,name,price,unit,active FROM products ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
