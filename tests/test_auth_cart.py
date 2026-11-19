"""Run: python -m unittest discover -s tests -v (uses temporary databases)."""
import html
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from flask.testing import FlaskClient
from werkzeug.security import check_password_hash
from app import create_app, ROOT


class BufferedClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs.setdefault("buffered", True)
        return super().open(*args, **kwargs)


class AuthenticationAndCartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "test.db"
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret",
                               "DATABASE": self.database})
        self.app.test_client_class = BufferedClient
        self.client = self.app.test_client()

    def form_token(self, client, page):
        response = client.get(page)
        self.assertEqual(response.status_code, 200)
        return html.unescape(re.search(r'name="csrf_token" value="([^"]+)"', response.text)[1])

    def register(self, client, username="alice", name="Alice", **extra):
        data = {"name": name, "username": username, "password": "Strong test password!",
                "confirm_password": "Strong test password!",
                "csrf_token": self.form_token(client, "/register")}
        data.update(extra)
        return client.post("/register", data=data)

    def headers(self, client):
        return {"X-CSRFToken": client.get("/api/session").json["csrf_token"]}

    def test_pages_and_apis_require_authentication(self):
        for page in ["/", "/index.html", "/products/", "/products/index.html",
                     "/products/details?id=1", "/products/details.html?id=1",
                     "/cart", "/cart.html", "/products/images/1.jpg"]:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.location)
        for path in ["/api/products", "/api/products/1", "/api/cart", "/api/carts/1", "/api/session"]:
            self.assertEqual(self.client.get(path).status_code, 401)
        for method, path in [("POST", "/api/cart/items"), ("PATCH", "/api/cart/items/1"),
                             ("DELETE", "/api/carts/1/items/1"), ("POST", "/api/logout")]:
            self.assertEqual(self.client.open(path, method=method).status_code, 401)
        for path in ["/login", "/register", "/style.css", "/script.js", "/vehicle.svg"]:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ["/app.py", "/products.db", "/.session-secret", "/schema.sql", "/templates/auth.html"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_register_hash_session_and_return_destination(self):
        destination = "/products/details.html?id=2"
        response = self.register(self.client, next=destination)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, destination)
        with closing(sqlite3.connect(self.database)) as db:
            row = db.execute("SELECT name, username, password_hash FROM users").fetchone()
            self.assertEqual(row[:2], ("Alice", "alice"))
            self.assertTrue(row[2].startswith("scrypt:"))
            self.assertTrue(check_password_hash(row[2], "Strong test password!"))
            self.assertNotEqual(row[2], "Strong test password!")
            self.assertEqual(db.execute("SELECT count(*) FROM carts").fetchone()[0], 1)
        info = self.client.get("/api/session")
        self.assertEqual(info.json["user"]["username"], "alice")
        self.assertNotIn("password", info.text)
        self.assertEqual(info.headers["Cache-Control"], "no-store")
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Expires=", cookie)
        for path in ["/", "/products/", destination, "/cart.html", "/products/images/1.jpg"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_registration_validation_and_case_insensitive_duplicates(self):
        for data in [{"name": " "}, {"username": "ab"}, {"username": "bad username"},
                     {"password": "short"}, {"confirm_password": "different"}]:
            self.assertEqual(self.register(self.client, **data).status_code, 400)
        self.assertEqual(self.register(self.client).status_code, 302)
        other = self.app.test_client()
        self.assertEqual(self.register(other, username="ALICE").status_code, 409)
        self.assertEqual(other.get("/api/session").status_code, 401)

    def test_login_logout_and_cart_persistence(self):
        self.register(self.client)
        self.client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=self.headers(self.client))
        response = self.client.post("/api/logout", headers=self.headers(self.client))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/cart").status_code, 401)
        for username, password in [("alice", "wrong password"), ("nobody", "wrong password")]:
            response = self.client.post("/login", data={"username": username, "password": password,
                                                       "csrf_token": self.form_token(self.client, "/login")})
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid username or password", response.text)
        response = self.client.post("/login", data={"username": "ALICE", "password": "Strong test password!",
                                      "csrf_token": self.form_token(self.client, "/login"), "next": "/cart.html"})
        self.assertEqual(response.location, "/cart.html")
        self.assertEqual(self.client.get("/api/cart").json["items"][0]["quantity"], 2)

    def test_csrf_is_required_for_forms_and_all_mutations(self):
        self.assertEqual(self.client.post("/register", data={}).status_code, 400)
        self.assertEqual(self.client.post("/login", data={}).status_code, 400)
        self.register(self.client)
        for method, path, data in [("POST", "/api/cart/items", {"product_id": 1, "quantity": 1}),
                                   ("PATCH", "/api/cart/items/1", {"quantity": 2}),
                                   ("DELETE", "/api/cart/items/1", None), ("POST", "/api/logout", None)]:
            self.assertEqual(self.client.open(path, method=method, json=data).status_code, 400)
        other = self.app.test_client()
        self.register(other, username="bob")
        self.assertEqual(self.client.post("/api/logout", headers=self.headers(other)).status_code, 400)
        self.assertEqual(self.client.get("/api/session").status_code, 200)

    def test_cart_add_update_remove_and_validation(self):
        self.register(self.client)
        headers = self.headers(self.client)
        def add(data):
            return self.client.post("/api/cart/items", json=data, headers=headers)
        response = add({"product_id": 1, "quantity": 2})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["total_paise"], 130000)
        self.assertEqual(add({"product_id": 1, "quantity": 1}).json["items"][0]["quantity"], 3)
        for data in [{"product_id": 1, "quantity": 0}, {"product_id": 1, "quantity": True},
                     {"product_id": 1, "quantity": 1.5}, {"product_id": "1", "quantity": 1},
                     {"product_id": 1, "quantity": 1, "user_id": 2}, {"product_id": 1}]:
            self.assertEqual(add(data).status_code, 400)
        self.assertEqual(add({"product_id": 1, "quantity": 3}).status_code, 409)
        self.assertEqual(add({"product_id": 20, "quantity": 1}).status_code, 409)
        self.assertEqual(add({"product_id": 999, "quantity": 1}).status_code, 404)
        response = self.client.patch("/api/cart/items/1", json={"quantity": 4}, headers=headers)
        self.assertEqual(response.json["total_paise"], 260000)
        self.assertEqual(self.client.patch("/api/cart/items/1", json={"quantity": 6}, headers=headers).status_code, 409)
        response = self.client.delete("/api/cart/items/1", headers=headers)
        self.assertEqual(response.json["items"], [])
        self.assertEqual(response.json["total_paise"], 0)
        self.assertEqual(self.client.delete("/api/cart/items/1", headers=headers).status_code, 404)

    def test_cart_survives_application_restart(self):
        self.register(self.client)
        expected = self.client.post(
            "/api/cart/items", json={"product_id": 1, "quantity": 2},
            headers=self.headers(self.client),
        ).json
        restarted = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret",
                                "DATABASE": self.database})
        restarted.test_client_class = BufferedClient
        client = restarted.test_client()
        response = client.post("/login", data={
            "username": "alice", "password": "Strong test password!",
            "csrf_token": self.form_token(client, "/login"),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/api/cart").json, expected)

    def test_prices_come_from_database_and_client_prices_are_rejected(self):
        self.register(self.client)
        headers = self.headers(self.client)
        for field in ["price", "price_paise", "subtotal_paise", "total_paise"]:
            response = self.client.post("/api/cart/items", headers=headers, json={
                "product_id": 1, "quantity": 2, field: 1,
            })
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/cart").json["items"], [])
        self.client.post("/api/cart/items", headers=headers,
                         json={"product_id": 1, "quantity": 2})
        self.client.post("/api/cart/items", headers=headers,
                         json={"product_id": 2, "quantity": 1})
        self.assertEqual(self.client.get("/api/cart").json["total_paise"], 228000)
        response = self.client.patch("/api/cart/items/1", headers=headers,
                                     json={"quantity": 1, "price_paise": 1})
        self.assertEqual(response.status_code, 400)
        # A server-side price change must be reflected in the next calculation.
        with closing(sqlite3.connect(self.database)) as db:
            with db:
                db.execute("UPDATE products SET price_paise = 70000 WHERE id = 1")
        cart = self.client.get("/api/cart").json
        self.assertEqual(cart["items"][0]["quantity"], 2)
        self.assertEqual(cart["items"][0]["subtotal_paise"], 140000)
        self.assertEqual(cart["total_paise"], 238000)

    def test_cannot_read_or_modify_another_users_cart_by_manipulating_requests(self):
        alice, bob = self.client, self.app.test_client()
        self.register(alice)
        self.register(bob, username="bob", name="Bob")
        alice_cart = alice.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=self.headers(alice)).json
        alice_id = alice_cart["id"]
        bob_headers = self.headers(bob)
        # Bob supplies Alice's real cart ID, using Bob's valid session and CSRF token.
        attempts = [("GET", f"/api/carts/{alice_id}", None),
                    ("POST", f"/api/carts/{alice_id}/items", {"product_id": 2, "quantity": 1}),
                    ("PATCH", f"/api/carts/{alice_id}/items/1", {"quantity": 1}),
                    ("DELETE", f"/api/carts/{alice_id}/items/1", None)]
        for method, path, data in attempts:
            with self.subTest(method=method):
                response = bob.open(path, method=method, json=data, headers=bob_headers)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json, {"error": "Cart not found."})
        self.assertEqual(bob.get(f"/api/cart?user_id=1&cart_id={alice_id}").json["items"], [])
        self.assertEqual(bob.post("/api/cart/items", json={"product_id": 1, "quantity": 1, "cart_id": alice_id}, headers=bob_headers).status_code, 400)
        self.assertEqual(alice.get("/api/cart").json, alice_cart)
        bob_id = bob.get("/api/cart").json["id"]
        self.assertEqual(bob.post(f"/api/carts/{bob_id}/items", json={"product_id": 2, "quantity": 1}, headers=bob_headers).status_code, 201)
        self.assertEqual(bob.patch(f"/api/carts/{bob_id}/items/2", json={"quantity": 2}, headers=bob_headers).status_code, 200)
        self.assertEqual(bob.delete(f"/api/carts/{bob_id}/items/2", headers=bob_headers).status_code, 200)

    def test_redirects_cannot_leave_site_and_return_query_is_preserved(self):
        response = self.client.get("/products/details.html?id=3")
        self.assertEqual(parse_qs(urlsplit(response.location).query)["next"], ["/products/details.html?id=3"])
        for destination in ["https://example.com", "//example.com", "/\\example.com", "//[", "http://["]:
            client = self.app.test_client()
            self.form_token(client, "/login?next=" + destination)
            response = client.get("/register", query_string={"next": destination})
            self.assertIn('name="next" value="/products/index.html"', response.text)
        response = self.register(self.client, next="https://example.com")
        self.assertEqual(response.location, "/products/index.html")

    def test_product_api_still_searches_and_validates(self):
        self.register(self.client)
        products = self.client.get("/api/products").json
        self.assertEqual([p["id"] for p in products], list(range(1, 21)))
        self.assertEqual(products[0]["price_paise"], 65000)
        self.assertEqual(self.client.get("/api/products?q=SEDAN").json, self.client.get("/api/products?q=sedan").json)
        self.assertEqual(self.client.get("/api/products?q=nonexistentvehicle").json, [])
        for p in products:
            self.assertEqual(self.client.get(p["image_url"]).status_code, 200)
            self.assertEqual(self.client.get(f"/api/products/{p['id']}").json, p)
        for value in ["0", "-1", "abc", "9223372036854775808"]:
            self.assertEqual(self.client.get("/api/products/" + value).status_code, 400)
        self.assertEqual(self.client.get("/api/products/999").status_code, 404)
        self.assertEqual(self.client.get("/api/products", query_string={"q": "a" * 101}).status_code, 400)

    def test_migration_preserves_products_and_can_run_again(self):
        self.register(self.client)
        before = self.client.get("/api/products").json
        create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": self.database})
        self.assertEqual(self.client.get("/api/products").json, before)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 1)
        # Simulate an older database containing only the existing products table.
        old = Path(self.temp.name) / "old.db"
        with closing(sqlite3.connect(old)) as db:
            db.executescript((ROOT / "schema.sql").read_text().split('-- Idempotent:')[0])
            db.execute("UPDATE products SET stock = 42 WHERE id = 1")
            db.commit()
        create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": old})
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0], 42)
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
