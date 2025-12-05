import os, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from models import db, Product, Category

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}
# Hidden admin path (not linked on pages). Change to your own secret if you want.
ADMIN_PATH = os.environ.get("ADMIN_PATH", "/super-secret-admin-2025")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()

    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    def login_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get("is_admin"):
                return redirect(url_for("admin_login", next=request.path))
            return f(*args, **kwargs)
        return wrapper

    @app.route("/")
    def index():
        q = request.args.get("q", "").strip()
        cat = request.args.get("cat", type=int)
        products_q = Product.query.order_by(Product.created_at.desc())
        if cat:
            products_q = products_q.filter(Product.category_id == cat)
        if q:
            q_like = f"%{q}%"
            products_q = products_q.filter((Product.name.ilike(q_like)) | (Product.description.ilike(q_like)))
        products = products_q.all()
        categories = Category.query.order_by(Category.name).all()
        return render_template("index.html", products=products, categories=categories, shop_phone=app.config["SHOP_PHONE"], shop_name=app.config["SHOP_NAME"])

    @app.route("/about")
    def about():
        # Use SOP details for About (from proposal). :contentReference[oaicite:1]{index=1}
        return render_template("about.html", shop_phone=app.config["SHOP_PHONE"], shop_name=app.config["SHOP_NAME"])

    @app.route("/product/<int:id>")
    def product_detail(id):
        p = Product.query.get_or_404(id)
        return render_template("product.html", product=p, shop_phone=app.config["SHOP_PHONE"], shop_name=app.config["SHOP_NAME"])

    # Hidden admin login (not linked anywhere).
    @app.route(ADMIN_PATH + "/login", methods=["GET", "POST"])
    def admin_login():
        next_url = request.args.get("next") or url_for("admin_list")
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd == ADMIN_PASSWORD:
                session["is_admin"] = True
                flash("Logged in as admin.", "success")
                return redirect(next_url)
            flash("Incorrect password.", "error")
            return redirect(url_for("admin_login", next=next_url))
        return render_template("admin_login.html", next=next_url)

    @app.route(ADMIN_PATH + "/logout")
    def admin_logout():
        session.pop("is_admin", None)
        flash("Logged out.", "success")
        return redirect(url_for("index"))

    @app.route(ADMIN_PATH + "/admin")
    @login_required
    def admin_list():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template("admin_list.html", products=products)

    @app.route(ADMIN_PATH + "/add", methods=["GET", "POST"])
    @login_required
    def admin_add():
        categories = Category.query.order_by(Category.name).all()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description")
            price = request.form.get("price")
            category_id = request.form.get("category")
            file = request.files.get("image")
            filename = None
            if file and file.filename:
                raw = secure_filename(file.filename)
                ext = raw.rsplit(".", 1)[-1].lower() if "." in raw else ""
                if ext not in ALLOWED_EXT:
                    flash("Invalid image format.", "error")
                    return redirect(url_for("admin_add"))
                filename = f"{int(time.time())}_{raw}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            product = Product(
                name=name,
                description=description,
                price=float(price) if price else None,
                image_filename=filename,
                category_id=int(category_id) if category_id else None
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added.", "success")
            return redirect(url_for("admin_list"))
        return render_template("admin_add.html", categories=categories)

    @app.route(ADMIN_PATH + "/edit/<int:id>", methods=["GET", "POST"])
    @login_required
    def admin_edit(id):
        p = Product.query.get_or_404(id)
        categories = Category.query.order_by(Category.name).all()
        if request.method == "POST":
            p.name = request.form.get("name", "").strip()
            p.description = request.form.get("description")
            price = request.form.get("price")
            p.price = float(price) if price else None
            p.category_id = int(request.form.get("category")) if request.form.get("category") else None
            file = request.files.get("image")
            if file and file.filename:
                raw = secure_filename(file.filename)
                ext = raw.rsplit(".", 1)[-1].lower() if "." in raw else ""
                if ext not in ALLOWED_EXT:
                    flash("Invalid image format.", "error")
                    return redirect(url_for("admin_edit", id=id))
                filename = f"{int(time.time())}_{raw}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                p.image_filename = filename
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("admin_list"))
        return render_template("admin_add.html", categories=categories, product=p)

    @app.route(ADMIN_PATH + "/delete/<int:id>", methods=["POST"])
    @login_required
    def admin_delete(id):
        p = Product.query.get_or_404(id)
        try:
            if p.image_filename:
                path = os.path.join(app.config["UPLOAD_FOLDER"], p.image_filename)
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        db.session.delete(p)
        db.session.commit()
        flash("Product deleted.", "success")
        return redirect(url_for("admin_list"))

    @app.route(ADMIN_PATH + "/seed")
    @login_required
    def seed():
        if Category.query.count() == 0:
            c1 = Category(name="Transformers")
            c2 = Category(name="Batteries")
            c3 = Category(name="Stabilizers")
            db.session.add_all([c1, c2, c3])
            db.session.commit()
        if Product.query.count() == 0:
            p1 = Product(name="5 KVA Transformer", description="Oil-cooled 1-phase transformer — good for local stabilizer setups.", price=12000, category_id=1, stock=5)
            p2 = Product(name="150 Ah Tubular Battery", description="High capacity battery for home inverters.", price=8500, category_id=2, stock=12)
            p3 = Product(name="60 KVA 3-phase Stabilizer", description="Servo controlled 3-phase stabilizer for industrial use.", price=78000, category_id=3, stock=2)
            db.session.add_all([p1, p2, p3])
            db.session.commit()
        flash("Seed data added.", "success")
        return redirect(url_for("admin_list"))

    # serve uploaded images if needed (Flask static usually handles, but safe)
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
