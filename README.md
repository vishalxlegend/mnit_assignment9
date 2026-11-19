# Legendry Toy Cars

For the complete submission documentation, prerequisites, full application and monitoring setup, architecture, migrations, verification and screenshots, see [readme/README.md](readme/README.md).

An authenticated toy vehicle catalog built with HTML, CSS, JavaScript, Flask and SQLite.
Users register, browse 20 toys, search products and maintain a private shopping cart.

## Run locally

Python 3.9+ with pip is required. On Linux/macOS, from the project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/ and create an account. Stop the server with Ctrl+C.
If the old server is running, restart it after installing the updated requirements.
Use Flask to serve the whole app. Live Server cannot enforce authentication and must
not be used to host this project; the page script redirects local port 5500 to Flask.

## Authentication and access

- Registration collects name, username, password and password confirmation. Usernames
  are unique without regard to case (3–30 letters, digits or underscores).
- Passwords are 8–128 characters. Only salted scrypt hashes are stored using
  Werkzeug's `generate_password_hash`; verification uses `check_password_hash`.
- Flask-Login maintains authentication in Flask's signed session cookie, with
  HttpOnly and SameSite=Lax flags. Sessions expire after eight hours without renewal.
  No persistent “remember me” cookie is used. Logging out clears the browser session.
- Flask-WTF protects login, registration, logout and cart changes against CSRF.
  The frontend obtains a token from `/api/session` and sends `X-CSRFToken` on writes.
- All application pages, product images and APIs require login. Only login,
  registration and the shared CSS/JS/favicon are public. Page requests redirect to
  login and then return to a validated local destination. API requests return JSON
  with HTTP 401 instead of redirecting to HTML.
- Password hashes never appear in API responses. SQL values use bound parameters,
  and user-provided text is escaped by Jinja or inserted with `textContent`.
- Authentication and cart responses use `Cache-Control: no-store`.

A random development signing key is generated in `.session-secret` with owner-only
permissions and is ignored by Git. Keep it private. For an HTTPS deployment, provide
an independent `SECRET_KEY` environment variable and set `COOKIE_SECURE=1` so cookies
are sent only over HTTPS. The included single-process Waitress server is configured for local use.

Libraries: [Flask-Login](https://flask-login.readthedocs.io/en/latest/),
[Werkzeug password hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash),
and [Flask-WTF CSRF](https://flask-wtf.readthedocs.io/en/stable/csrf/).

## Database and migrations

SQLite needs no separate database server. [Alembic](https://alembic.sqlalchemy.org/en/latest/)
now manages versioned migrations. Flask startup calls Alembic's `upgrade head` through
`db_migrations.py`; it applies pending revisions and records the current revision in
`alembic_version`. Existing application queries still use Python's `sqlite3` module.

From the project folder, apply and inspect migrations explicitly:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python -m alembic history
.venv/bin/python app.py
```

On Windows, replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`.
Both startup and the Alembic CLI default to this project's `products.db`. To use
another SQLite file, set `DATABASE_PATH` to its path for both commands.

The revision sequence is:

1. `0001_products`: adopts an existing Part 1 products table without changing any
   records. Only an empty database receives the frozen toy catalog seed snapshot
   from `migrations/data/part1_products.sql`.
2. `0002_users_and_carts`: creates users, carts and cart items. If the earlier SQL
   setup already created these tables, it checks required columns and adopts them,
   preserving existing accounts, password hashes and cart contents.

Running upgrades again does not rerun completed revisions or reseed products.
Schema changes and the revision marker run in an explicit SQLite transaction;
a failed upgrade is rolled back. Downgrades are intentionally disabled to avoid
removing product, account or cart data. Back up your SQLite database before manual
schema changes; restore that backup if a rollback is needed.

`schema.sql` is a reference schema, not the startup migration mechanism. The old
`migrations/002_users_and_carts.sql` is retained only as historical reference.
Future schema changes belong in new Alembic revisions; create one with
`.venv/bin/python -m alembic revision -m "describe change"` and implement its
`upgrade()` before running `upgrade head`.

| Table | Purpose |
| --- | --- |
| `products` | ID, name, description, integer price in paise, image URL and stock |
| `users` | ID, name, unique username, password hash and creation timestamp |
| `carts` | One cart per user, linked by a unique `user_id` foreign key |
| `cart_items` | Product and quantity per cart, with a composite primary key |

A user and their empty cart are created in the same transaction. Cart ownership is
always taken from the authenticated session. Cart quantities are integers from 1–99
and cannot exceed stock. Repeated additions increase quantity. Prices and totals are
calculated by the server; client-supplied prices or owner IDs are rejected.
Cart changes do not reserve or reduce inventory; checkout is not implemented.

Prices are ₹480–₹4,500, one-thousandth of the original full-size vehicle prices.
They remain stored as integer paise; the frontend divides by 100 to display rupees.
`migrations/001_toy_catalog.sql` is the earlier conversion, already applied locally;
its original-price guards prevent repeated reductions. It is not rerun on startup.

Images are illustrative placeholders named `/products/images/<id>.jpg`. Their numeric
IDs determine the mapping and catalog order. Some images share the same placeholder.
`update_product_images.sql` can reset image paths in an existing database.

## Pages and APIs

| Route | Purpose |
| --- | --- |
| `/login`, `/login.html` | Login form (GET/POST) |
| `/register`, `/register.html` | Registration form (GET/POST), logs in on success |
| `/`, `/index.html` | Protected homepage |
| `/products/`, `/products/index.html` | Protected catalog and search |
| `/products/details.html?id=1`, `/products/details?id=1` | Protected product details |
| `/cart`, `/cart.html` | Private cart with quantity updates and removal |
| `GET /api/session` | Current user profile and CSRF token |
| `POST /api/logout` | Log out (CSRF required) |
| `GET /api/products?q=sedan` | Product list/search (query optional) |
| `GET /api/products/1` | One product |
| `GET /api/cart` | Current user's cart, items and total |
| `POST /api/cart/items` | Add: `{"product_id": 1, "quantity": 1}` |
| `PATCH /api/cart/items/1` | Set quantity: `{"quantity": 2}` |
| `DELETE /api/cart/items/1` | Remove product 1 |

Explicit cart routes also exist: `GET /api/carts/<cart_id>`,
`POST /api/carts/<cart_id>/items`, and `PATCH`/`DELETE
/api/carts/<cart_id>/items/<product_id>`. Every one checks both cart ID and current
user ID in SQL. Other users' carts return 404, just like nonexistent carts.

Errors use `{"error": "message"}`: 400 for invalid input or CSRF, 401 for unauthenticated
API access, 404 for missing/inaccessible resources, and 409 for stock or username
conflicts. Search is trimmed, limited to 100 characters and ASCII case-insensitive.

## Verify authorization

Run the automated tests (all test accounts and carts use temporary databases):

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The test `test_cannot_read_or_modify_another_users_cart_by_manipulating_requests`
creates Alice and Bob with separate authenticated sessions. Alice adds an item.
Bob uses his own valid CSRF token to attempt GET, POST, PATCH and DELETE on Alice's
actual cart ID. Each request must return 404, Alice's cart must remain unchanged,
and Bob must still be able to modify his own cart. Tests also cover spoofed owner
fields, CSRF, hashed passwords, validation, redirects, logout and cart persistence.

To demonstrate the same behavior manually:

1. Register Alice in a normal browser window and add a toy. In Developer Tools,
   run `await (await fetch('/api/cart')).json()` and note its `id`.
2. Register Bob in a separate private window. Open Developer Tools on the catalog.
3. Run the following, replacing `aliceCartId` with Alice's cart ID:

```js
const aliceCartId = 1; // Replace with Alice's actual cart ID.
const { csrf_token } = await (await fetch('/api/session')).json();
await fetch(`/api/carts/${aliceCartId}`).then(r => r.status); // 404
await fetch(`/api/carts/${aliceCartId}/items`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf_token },
  body: JSON.stringify({ product_id: 1, quantity: 1 })
}).then(r => r.status); // 404
await fetch(`/api/carts/${aliceCartId}/items/1`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf_token },
  body: JSON.stringify({ quantity: 2 })
}).then(r => r.status); // 404
await fetch(`/api/carts/${aliceCartId}/items/1`, {
  method: 'DELETE', headers: { 'X-CSRFToken': csrf_token }
}).then(r => r.status); // 404
```

4. Refresh Alice's cart to confirm it is unchanged. Capture the requests and responses
   for the assignment's authorization demonstration.

## Main files

- `app.py`: application factory, authentication, protected routes and cart APIs.
- `templates/auth.html`: server-rendered login and registration forms.
- `index.html`, `products/*.html`, `cart.html`: application pages.
- `script.js`, `style.css`: product/cart interactions and shared styling.
- `alembic.ini`, `db_migrations.py`, `migrations/env.py`: migration configuration.
- `migrations/versions/*.py`: versioned schema changes.
- `schema.sql`, `migrations/*.sql`: reference schema and historical SQL.
- `tests/test_auth_cart.py`: authentication, authorization and regression tests.

Commit the source, SQL migrations, tests and README. Keep the database, virtual
environment and `.session-secret` out of source control.

Migration tests in `tests/test_migrations.py` compare all product fields before and
after upgrading a Part 1 database, verify preservation of existing users and carts,
check repeat upgrades, and prove failed migrations roll back without losing data.

## Part 3: Logging and monitoring

Structured logs, isolated monitoring storage, Prometheus metrics, a provisioned
Grafana dashboard and reproducible traffic/failure demonstrations are implemented.
See [monitoring/README.md](monitoring/README.md) for setup, credentials location,
metric definitions, privacy rules, evidence and verification commands.

On this Linux machine, start the complete monitored application with:

```sh
.venv/bin/python monitoring/stack.py --app-port 5001 --demo
```

This serves the app on port 5001, Prometheus on 9090, and Grafana on 3000. Monitoring
events use a separate `monitoring/runtime/monitoring.db`; Prometheus uses its own
time-series database. Neither stores monitoring data in `products.db`.
