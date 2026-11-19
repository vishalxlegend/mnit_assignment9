"""Authenticated toy catalog with private, persistent shopping carts."""

from datetime import timedelta
from pathlib import Path
import os
import re
import secrets
import sqlite3
from urllib.parse import urlsplit

from flask import (Flask, abort, current_app, g, jsonify, redirect,
                   render_template, request, send_from_directory, session, url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_user,
                         logout_user)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from observability import install_monitoring
from db_migrations import upgrade_database

ROOT = Path(__file__).resolve().parent


def get_database():
    if "database" not in g:
        g.database = sqlite3.connect(current_app.config["DATABASE"])
        g.database.row_factory = sqlite3.Row
        g.database.execute("PRAGMA foreign_keys = ON")
    return g.database


def initialize_database(app):
    """Apply pending Alembic revisions without recreating existing tables."""
    upgrade_database(app.config["DATABASE"])


def local_secret():
    """Persist a random development key, without committing it to source control."""
    path = ROOT / ".session-secret"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text().strip()
    with os.fdopen(fd, "w") as output:
        key = secrets.token_hex(32)
        output.write(key)
    return key


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.username = row["username"]


def safe_next(value):
    """Only redirect to known local pages, preserving their query strings."""
    if not value or value.startswith("//") or "\\" in value or any(ord(c) < 32 for c in value):
        return "/products/index.html"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "/products/index.html"
    allowed = {"/", "/index.html", "/products/", "/products/index.html",
               "/products/details", "/products/details.html", "/cart", "/cart.html"}
    if parsed.scheme or parsed.netloc or parsed.path not in allowed:
        return "/products/index.html"
    return parsed.path + ("?" + parsed.query if parsed.query else "")


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        MONITORING_LOG_DIR=os.environ.get("MONITORING_LOG_DIR"),
        MONITORING_DATABASE=os.environ.get("MONITORING_DATABASE"),
        METRICS_TOKEN=os.environ.get("METRICS_TOKEN"),
        ENABLE_FAILURE_DEMO=os.environ.get("ENABLE_FAILURE_DEMO") == "1",
        DATABASE=os.environ.get("DATABASE_PATH") or ROOT / "products.db",
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = local_secret()

    monitor = install_monitoring(app)

    login_manager = LoginManager(app)
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id.isascii() or not user_id.isdigit() or len(user_id) > 18:
            return None
        row = get_database().execute(
            "SELECT id, name, username FROM users WHERE id = ?", (int(user_id),)
        ).fetchone()
        return User(row) if row else None

    @app.before_request
    def require_authentication():
        # Protect pages, images and APIs on the server, not just in JavaScript.
        if request.endpoint in {"login", "register", "public_file", "metrics", "healthz"}:
            return None
        if request.endpoint is not None and not current_user.is_authenticated:
            if request.path.startswith("/api/"):
                abort(401, description="Please log in to continue.")
            return redirect(url_for("login", next=safe_next(request.full_path)))

    CSRFProtect(app)

    @app.teardown_appcontext
    def close_database(error=None):
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    @app.after_request
    def response_security(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.endpoint != "public_file":
            response.headers["Cache-Control"] = "no-store"
        return response

    def start_session(user):
        session.clear()
        login_user(user, remember=False, fresh=True)
        session.permanent = True

    def auth_page(mode, error=None, status=200):
        return render_template("auth.html", mode=mode, error=error,
                               next_url=safe_next(request.values.get("next"))), status

    @app.route("/login", methods=["GET", "POST"])
    @app.route("/login.html", methods=["GET", "POST"])
    def login():
        destination = safe_next(request.values.get("next"))
        if current_user.is_authenticated:
            return redirect(destination)
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            if not re.fullmatch(r"[a-z0-9_]{3,30}", username) or not 1 <= len(password) <= 128:
                monitor.auth_failed()
                return auth_page("login", "Invalid username or password.", 401)
            row = get_database().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if row is None or not check_password_hash(row["password_hash"], password):
                monitor.auth_failed()
                return auth_page("login", "Invalid username or password.", 401)
            start_session(User(row))
            return redirect(destination)
        return auth_page("login")

    @app.route("/register", methods=["GET", "POST"])
    @app.route("/register.html", methods=["GET", "POST"])
    def register():
        destination = safe_next(request.values.get("next"))
        if current_user.is_authenticated:
            return redirect(destination)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            if not 1 <= len(name) <= 100:
                return auth_page("register", "Enter a name between 1 and 100 characters.", 400)
            if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
                return auth_page("register", "Use 3–30 letters, numbers or underscores for your username.", 400)
            if not 8 <= len(password) <= 128:
                return auth_page("register", "Use a password between 8 and 128 characters.", 400)
            if password != request.form.get("confirm_password"):
                return auth_page("register", "Passwords do not match.", 400)
            password_hash = generate_password_hash(password, method="scrypt")
            db = get_database()
            try:
                with db:
                    cursor = db.execute(
                        "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)",
                        (name, username, password_hash),
                    )
                    user_id = cursor.lastrowid
                    db.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
            except sqlite3.IntegrityError:
                return auth_page("register", "That username is already taken.", 409)
            start_session(User({"id": user_id, "name": name, "username": username}))
            return redirect(destination)
        return auth_page("register")

    @app.post("/api/logout")
    def logout():
        logout_user()
        session.clear()
        return jsonify(message="Logged out.")

    @app.get("/api/session")
    def session_info():
        return jsonify(user={"id": current_user.id, "name": current_user.name,
                             "username": current_user.username}, csrf_token=generate_csrf())

    @app.get("/")
    @app.get("/index.html")
    def home():
        return send_from_directory(ROOT, "index.html")

    @app.get("/products/")
    @app.get("/products/index.html")
    def catalog():
        return send_from_directory(ROOT / "products", "index.html")

    @app.get("/products/details")
    @app.get("/products/details.html")
    def details():
        return send_from_directory(ROOT / "products", "details.html")

    @app.get("/cart")
    @app.get("/cart.html")
    def cart_page():
        return send_from_directory(ROOT, "cart.html")

    @app.get("/products/images/<int:product_id>.jpg")
    def product_image(product_id):
        return send_from_directory(ROOT / "products/images", f"{product_id}.jpg")

    @app.get("/<filename>")
    def public_file(filename):
        if filename not in {"style.css", "script.js", "vehicle.svg"}:
            abort(404)
        return send_from_directory(ROOT, filename)

    @app.get("/api/products")
    def products_api():
        search = request.args.get("q", "").strip()
        if len(search) > 100:
            abort(400, description="Search must be 100 characters or fewer.")
        rows = get_database().execute(
            "SELECT id, name, description, price_paise, image_url, stock "
            "FROM products WHERE instr(lower(name), lower(?)) > 0 "
            "OR instr(lower(description), lower(?)) > 0 ORDER BY id", (search, search),
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    def valid_id(value):
        if (not value.isascii() or not value.isdigit() or len(value) > 19
                or not 1 <= int(value) <= 9223372036854775807):
            abort(400, description="ID must be a positive integer in range.")
        return int(value)

    @app.get("/api/products/<product_id>")
    def product_api(product_id):
        row = get_database().execute(
            "SELECT * FROM products WHERE id = ?", (valid_id(product_id),)
        ).fetchone()
        if row is None:
            abort(404, description="Product not found.")
        return jsonify(dict(row))

    def owned_cart(cart_id=None):
        # Ownership comes only from the authenticated session. A URL ID is never enough.
        if cart_id is None:
            row = get_database().execute(
                "SELECT id FROM carts WHERE user_id = ?", (current_user.id,)
            ).fetchone()
        else:
            row = get_database().execute(
                "SELECT id FROM carts WHERE id = ? AND user_id = ?",
                (valid_id(cart_id), current_user.id),
            ).fetchone()
        if row is None:
            abort(404, description="Cart not found.")
        return row["id"]

    def cart_data(cart_id):
        items = [dict(row) for row in get_database().execute(
            "SELECT p.id AS product_id, p.name, p.price_paise, p.image_url, p.stock, i.quantity "
            "FROM cart_items i JOIN products p ON p.id = i.product_id "
            "WHERE i.cart_id = ? ORDER BY p.id", (cart_id,)
        )]
        for item in items:
            item["subtotal_paise"] = item["price_paise"] * item["quantity"]
        return {"id": cart_id, "items": items,
                "total_paise": sum(item["subtotal_paise"] for item in items)}

    @app.get("/api/cart", defaults={"cart_id": None})
    @app.get("/api/carts/<cart_id>")
    def read_cart(cart_id):
        return jsonify(cart_data(owned_cart(cart_id)))

    def json_fields(allowed):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != set(allowed):
            abort(400, description="Expected JSON fields: " + ", ".join(allowed))
        return data

    def quantity_value(value):
        if type(value) is not int or not 1 <= value <= 99:
            abort(400, description="Quantity must be an integer between 1 and 99.")
        return value

    def check_stock(product_id, quantity):
        row = get_database().execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            abort(404, description="Product not found.")
        if quantity > row["stock"]:
            abort(409, description="Requested quantity exceeds available stock.")

    @app.post("/api/cart/items", defaults={"cart_id": None})
    @app.post("/api/carts/<cart_id>/items")
    def add_item(cart_id):
        cart_id = owned_cart(cart_id)
        data = json_fields(("product_id", "quantity"))
        if type(data["product_id"]) is not int:
            abort(400, description="Product ID must be an integer.")
        product_id = valid_id(str(data["product_id"]))
        quantity = quantity_value(data["quantity"])
        db = get_database()
        with db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                             (cart_id, product_id)).fetchone()
            quantity = quantity_value(quantity + (old["quantity"] if old else 0))
            check_stock(product_id, quantity)
            db.execute("INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?) "
                       "ON CONFLICT(cart_id, product_id) DO UPDATE SET quantity = excluded.quantity",
                       (cart_id, product_id, quantity))
        monitor.cart_completed("add", added=data["quantity"])
        return jsonify(cart_data(cart_id)), 201

    @app.route("/api/cart/items/<product_id>", methods=["PATCH", "DELETE"], defaults={"cart_id": None})
    @app.route("/api/carts/<cart_id>/items/<product_id>", methods=["PATCH", "DELETE"])
    def change_item(cart_id, product_id):
        cart_id = owned_cart(cart_id)
        product_id = valid_id(product_id)
        db = get_database()
        with db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM cart_items WHERE cart_id = ? AND product_id = ?",
                          (cart_id, product_id)).fetchone() is None:
                abort(404, description="Cart item not found.")
            if request.method == "DELETE":
                db.execute("DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?", (cart_id, product_id))
            else:
                quantity = quantity_value(json_fields(("quantity",))["quantity"])
                check_stock(product_id, quantity)
                db.execute("UPDATE cart_items SET quantity = ? WHERE cart_id = ? AND product_id = ?",
                           (quantity, cart_id, product_id))
        monitor.cart_completed("remove" if request.method == "DELETE" else "update")
        return jsonify(cart_data(cart_id))

    @app.errorhandler(HTTPException)
    def handle_error(error):
        if request.path.startswith("/api/"):
            message = "Unable to complete the request." if error.code == 500 else error.description
            return jsonify(error=message), error.code
        if error.code == 400 and request.endpoint in {"login", "register"}:
            return auth_page(request.endpoint, "Your form expired or was invalid. Please try again.", 400)
        return error

    @app.post("/api/demo/failure")
    def controlled_failure():
        if not app.config["ENABLE_FAILURE_DEMO"]:
            abort(404)
        # Auth + CSRF are enforced by the normal middleware. No data is changed.
        if request.args.get("kind") == "database":
            raise sqlite3.OperationalError("Controlled database failure")
        raise RuntimeError("Controlled application failure")

    try:
        initialize_database(app)
    except Exception as error:
        monitor.failure(error, database=True)
        monitor.close()
        raise RuntimeError("Database initialization failed; inspect structured monitoring logs.") from None
    return app


if __name__ == "__main__":
    import signal
    from waitress import serve

    def stop_application(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop_application)
    application = create_app()
    try:
        serve(application, host=os.environ.get("APP_HOST", "127.0.0.1"),
              port=int(os.environ.get("APP_PORT", "5000")), threads=8)
    finally:
        application.extensions["monitoring"].close()
