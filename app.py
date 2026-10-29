"""A small Flask server for the HTML pages and SQLite product API."""

from contextlib import closing
from pathlib import Path
import sqlite3

from flask import Flask, abort, g, jsonify, request, send_from_directory


ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "products.db"
app = Flask(__name__, static_folder=None)


def initialize_database():
    """Create and seed the database on the first run."""
    if not DATABASE.exists():
        with closing(sqlite3.connect(DATABASE)) as connection:
            with connection:
                connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


def get_database():
    if "database" not in g:
        g.database = sqlite3.connect(DATABASE)
        g.database.row_factory = sqlite3.Row
    return g.database


@app.teardown_appcontext
def close_database(error=None):
    connection = g.pop("database", None)
    if connection is not None:
        connection.close()


@app.after_request
def allow_live_server(response):
    if request.path.startswith("/api/"):
        origin = request.headers.get("Origin")
        if origin in {"http://127.0.0.1:5500", "http://localhost:5500"}:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.vary.add("Origin")
    return response


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


@app.get("/products/images/<int:product_id>.jpg")
def product_image(product_id):
    return send_from_directory(ROOT / "products" / "images", f"{product_id}.jpg")


@app.get("/<filename>")
def public_file(filename):
    # Only these assets are public; never expose Python, SQL, or database files.
    if filename not in {"style.css", "script.js", "vehicle.svg"}:
        abort(404)
    return send_from_directory(ROOT, filename)


@app.get("/api/products")
def products_api():
    search = request.args.get("q", "").strip()
    if len(search) > 100:
        abort(400, description="Search must be 100 characters or fewer.")

    # Bind parameters so user input is never inserted into SQL code.
    rows = get_database().execute(
        "SELECT id, name, description, price_paise, image_url, stock "
        "FROM products WHERE instr(lower(name), lower(?)) > 0 "
        "OR instr(lower(description), lower(?)) > 0 ORDER BY id",
        (search, search),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/products/<product_id>")
def product_api(product_id):
    if not product_id.isascii() or not product_id.isdigit() or len(product_id) > 19:
        abort(400, description="Product ID must be a positive integer.")

    product_id = int(product_id)
    if not 1 <= product_id <= 9223372036854775807:
        abort(400, description="Product ID is out of range.")

    row = get_database().execute(
        "SELECT id, name, description, price_paise, image_url, stock "
        "FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if row is None:
        abort(404, description="Product not found.")
    return jsonify(dict(row))


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(error):
    if request.path.startswith("/api/"):
        message = "Unable to load products. Please try again." if error.code == 500 else error.description
        return jsonify(error=message), error.code
    return error


initialize_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
