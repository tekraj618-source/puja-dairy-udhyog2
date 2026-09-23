import os, sqlite3, uuid, base64, hmac, hashlib, json, requests
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,"puja_dairy.db")
app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key")

SHOP={"name":"Puja Dairy Udhyog","address":"Dhangadhi, Sudurpaschim, Nepal","phone":"9766100969","email":"tekraj618@gmail.com","trust":"5+ years of trust"}
ESEWA_PRODUCT_CODE=os.environ.get("ESEWA_PRODUCT_CODE","EPAYTEST")
ESEWA_SECRET_KEY=os.environ.get("ESEWA_SECRET_KEY","8gBm/:&EnhH.1/q")
ESEWA_PAYMENT_URL=os.environ.get("ESEWA_PAYMENT_URL","https://rc-epay.esewa.com.np/api/epay/main/v2/form")
ESEWA_STATUS_URL=os.environ.get("ESEWA_STATUS_URL","https://rc-epay.esewa.com.np/api/epay/transaction/status/")

SEED=[
("Milk","Fresh daily milk",90,"🥛"),("Dahi","Creamy traditional curd",140,"🥣"),
("Mahi","Refreshing buttermilk",70,"🥤"),("Paneer","Soft fresh paneer",800,"🧀"),
("Butter","Rich dairy butter",1000,"🧈"),("Ghee","Aromatic pure ghee",1200,"✨"),
("Cake 1 pound","Fresh celebration cake",700,"🎂"),("Cake half pound","Fresh half-pound cake",550,"🍰")]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE,description TEXT,price REAL,icon TEXT,active INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT,customer_name TEXT,phone TEXT,address TEXT,items TEXT,total REAL,note TEXT,
      payment_method TEXT DEFAULT 'COD',payment_status TEXT DEFAULT 'COD',transaction_uuid TEXT,
      status TEXT DEFAULT 'New',created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS inquiries(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,email TEXT,message TEXT,is_read INTEGER DEFAULT 0,created_at TEXT)""")
    for p in SEED:
        c.execute("INSERT OR IGNORE INTO products(name,description,price,icon) VALUES(?,?,?,?)",p)
    c.commit(); c.close()

def owner_required(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("owner_logged_in"): return redirect(url_for("owner_login"))
        return f(*a,**k)
    return w

@app.context_processor
def common(): return {"shop":SHOP}

@app.route("/")
def home():
    c=db(); p=c.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall(); c.close()
    return render_template("index.html",products=p)

@app.route("/products")
def products():
    c=db(); p=c.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall(); c.close()
    return render_template("products.html",products=p)

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/delivery")
def delivery(): return render_template("delivery.html")

@app.route("/contact",methods=["GET","POST"])
def contact():
    if request.method=="POST":
        name=request.form.get("name","").strip(); msg=request.form.get("message","").strip()
        if not name or not msg:
            flash("Please enter your name and message.","error"); return redirect(url_for("contact"))
        c=db(); c.execute("INSERT INTO inquiries(name,phone,email,message,created_at) VALUES(?,?,?,?,?)",
          (name,request.form.get("phone",""),request.form.get("email",""),msg,datetime.now().strftime("%Y-%m-%d %H:%M")))
        c.commit(); c.close(); flash("Your message has been sent.","success"); return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/order",methods=["GET","POST"])
def order():
    c=db(); products=c.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall(); c.close()
    if request.method=="POST":
        name=request.form.get("customer_name","").strip(); phone=request.form.get("phone","").strip(); address=request.form.get("address","").strip()
        if not name or not phone or not address:
            flash("Please complete your name, phone and address.","error"); return render_template("order.html",products=products)
        chosen=[]; total=0
        for p in products:
            try: q=max(0,int(request.form.get(f"qty_{p['id']}","0")))
            except: q=0
            if q:
                line=q*float(p["price"]); total+=line; chosen.append(f"{p['name']} x {q} = Rs. {line:.0f}")
        if not chosen:
            flash("Please select at least one product.","error"); return render_template("order.html",products=products)
        method=request.form.get("payment_method","COD")
        if method not in ("COD","ESEWA"): method="COD"
        tx=str(uuid.uuid4())
        pay="Pending" if method=="ESEWA" else "COD"; status="Payment Pending" if method=="ESEWA" else "New"
        c=db(); cur=c.execute("""INSERT INTO orders(customer_name,phone,address,items,total,note,payment_method,payment_status,transaction_uuid,status,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(name,phone,address," | ".join(chosen),total,request.form.get("note",""),method,pay,tx,status,datetime.now().strftime("%Y-%m-%d %H:%M")))
        oid=cur.lastrowid; c.commit(); c.close()
        if method=="ESEWA":
            session["payment_order_id"]=oid; return redirect(url_for("esewa_payment",order_id=oid))
        return render_template("order_success.html",order_id=oid,name=name,total=total,payment_method="Cash on Delivery")
    return render_template("order.html",products=products)

@app.route("/payment/esewa/<int:order_id>")
def esewa_payment(order_id):
    c=db(); o=c.execute("SELECT * FROM orders WHERE id=? AND payment_method='ESEWA'",(order_id,)).fetchone(); c.close()
    if not o: flash("Payment order not found.","error"); return redirect(url_for("order"))
    amount=f"{float(o['total']):.2f}"
    msg=f"total_amount={amount},transaction_uuid={o['transaction_uuid']},product_code={ESEWA_PRODUCT_CODE}"
    sig=base64.b64encode(hmac.new(ESEWA_SECRET_KEY.encode(),msg.encode(),hashlib.sha256).digest()).decode()
    return render_template("esewa_payment.html",order=o,payment_url=ESEWA_PAYMENT_URL,product_code=ESEWA_PRODUCT_CODE,
      signature=sig,success_url=url_for("esewa_success",_external=True),failure_url=url_for("esewa_failure",_external=True))

@app.route("/payment/esewa/success")
def esewa_success():
    raw=request.args.get("data")
    if not raw: return redirect(url_for("esewa_failure"))
    try: data=json.loads(base64.b64decode(raw).decode())
    except: return redirect(url_for("esewa_failure"))
    tx=data.get("transaction_uuid")
    if not tx: return redirect(url_for("esewa_failure"))
    c=db(); o=c.execute("SELECT * FROM orders WHERE transaction_uuid=?",(tx,)).fetchone(); c.close()
    if not o: flash("Order not found.","error"); return redirect(url_for("home"))
    try:
        r=requests.get(ESEWA_STATUS_URL,params={"product_code":ESEWA_PRODUCT_CODE,"total_amount":f"{float(o['total']):.2f}","transaction_uuid":tx},timeout=15)
        result=r.json()
    except:
        flash("Payment verification could not be completed.","error"); return redirect(url_for("home"))
    c=db()
    if result.get("status")=="COMPLETE":
        c.execute("UPDATE orders SET payment_status='Paid',status='New' WHERE id=?",(o["id"],))
        c.commit(); c.close()
        return render_template("payment_success.html",order_id=o["id"],name=o["customer_name"],total=o["total"])
    c.execute("UPDATE orders SET payment_status='Failed',status='Payment Failed' WHERE id=?",(o["id"],))
    c.commit(); c.close(); return render_template("payment_failed.html",order_id=o["id"])

@app.route("/payment/esewa/failure")
def esewa_failure():
    oid=session.get("payment_order_id")
    if oid:
        c=db(); c.execute("UPDATE orders SET payment_status='Failed',status='Payment Failed' WHERE id=? AND payment_status='Pending'",(oid,)); c.commit(); c.close()
    return render_template("payment_failed.html",order_id=oid)

@app.route("/track",methods=["GET","POST"])
def track():
    result=None
    if request.method=="POST":
        try: oid=int(request.form.get("order_id",""))
        except: oid=0
        c=db(); result=c.execute("""SELECT id,customer_name,total,payment_method,payment_status,status,created_at
          FROM orders WHERE id=? AND phone=?""",(oid,request.form.get("phone","").strip())).fetchone(); c.close()
        if not result: flash("No matching order was found.","error")
    return render_template("track.html",result=result)

@app.route("/owner/login",methods=["GET","POST"])
def owner_login():
    if request.method=="POST":
        password=request.form.get("password",""); expected=os.environ.get("OWNER_PASSWORD","ChangeMe123!")
        if hmac.compare_digest(password,expected):
            session["owner_logged_in"]=True; return redirect(url_for("dashboard"))
        flash("Incorrect password.","error")
    return render_template("login.html")

@app.route("/owner/logout")
def owner_logout(): session.pop("owner_logged_in",None); return redirect(url_for("home"))

@app.route("/owner")
@owner_required
def dashboard():
    c=db()
    orders=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    inquiries=c.execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    products=c.execute("SELECT * FROM products ORDER BY id").fetchall()
    stats={"orders":c.execute("SELECT COUNT(*) x FROM orders").fetchone()["x"],
           "new":c.execute("SELECT COUNT(*) x FROM orders WHERE status='New'").fetchone()["x"],
           "messages":c.execute("SELECT COUNT(*) x FROM inquiries WHERE is_read=0").fetchone()["x"],
           "revenue":c.execute("SELECT COALESCE(SUM(total),0) x FROM orders WHERE payment_status='Paid' OR payment_method='COD'").fetchone()["x"]}
    c.close(); return render_template("dashboard.html",orders=orders,inquiries=inquiries,products=products,stats=stats)

@app.post("/owner/order/<int:order_id>/status")
@owner_required
def update_order_status(order_id):
    allowed={"New","Confirmed","Preparing","Out for Delivery","Delivered","Cancelled"}
    s=request.form.get("status","New")
    if s not in allowed: flash("Invalid status.","error"); return redirect(url_for("dashboard"))
    c=db(); c.execute("UPDATE orders SET status=? WHERE id=?",(s,order_id)); c.commit(); c.close()
    flash("Order status updated.","success"); return redirect(url_for("dashboard"))

@app.post("/owner/product/<int:product_id>")
@owner_required
def update_product(product_id):
    try: price=max(0,float(request.form.get("price","0")))
    except: flash("Invalid price.","error"); return redirect(url_for("dashboard"))
    active=1 if request.form.get("active")=="1" else 0
    c=db(); c.execute("UPDATE products SET price=?,active=? WHERE id=?",(price,active,product_id)); c.commit(); c.close()
    flash("Product updated.","success"); return redirect(url_for("dashboard"))

@app.post("/owner/inquiry/<int:inquiry_id>/read")
@owner_required
def mark_inquiry_read(inquiry_id):
    c=db(); c.execute("UPDATE inquiries SET is_read=1 WHERE id=?",(inquiry_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

init_db()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=True)
