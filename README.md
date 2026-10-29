# Legendry Vehicles

A small product catalog built with HTML, CSS, JavaScript, Python (Flask), and SQLite.
The homepage only introduces the site and links to the catalog.

## Run locally (Windows PowerShell)

Prerequisite: Python 3.9 or newer, with pip.
Run these commands from this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/ in a browser. Stop the server with Ctrl+C.
The Python server serves both the pages and the API.
This is a local development server.

### Using VS Code Live Server

You can also open the HTML pages with Live Server on port **5500**, but keep
`app.py` running on port **5000**. The shared `script.js` detects Live Server and
requests product data from `http://127.0.0.1:5000/api/products`. Flask permits
these API requests from `http://127.0.0.1:5500` and `http://localhost:5500`.
Detail links use `details.html?id=1`, which works with either server.

If you see an API connection error, start the Python server using the command
above. Live Server itself does not run Python or connect to SQLite.

## Files

```text
index.html             Homepage with a Browse Catalog link
products/index.html    Product listing and search
products/details.html  One reusable product detail page
products/images/      Replaceable product images named 1.jpg, 2.jpg, etc.
style.css              Shared styles
script.js              Fetch and display product data
vehicle.svg            Source illustration and favicon
app.py                 Page routes and product API
schema.sql             Product table and three sample vehicles
products.db            SQLite database, generated on first run
requirements.txt       Python dependency
```

## Database

No separate SQL server or database installation is required. On the first run,
`app.py` creates `products.db` using `schema.sql`. Subsequent runs keep existing data.
The `products` table stores `id`, `name`, `description`, `price_paise`, `image_url`, and `stock`.
Prices use integer paise (100 paise = 1 rupee). Product images are sample illustrations.
Each product uses `/products/images/<id>.jpg`. The current JPEGs are copies of
the same sample illustration. Replace `products/images/1.jpg` to change product 1's
image, `2.jpg` for product 2, and so on. Use real JPEG files with the `.jpg` extension.
Both Flask and Live Server can serve these files.

To set these image paths for all existing products, run `update_product_images.sql`
against `products.db`, or execute:

```sql
UPDATE products
SET image_url = '/products/images/' || id || '.jpg';
```

Add a matching image file whenever you insert a new product, and refresh the browser
with Ctrl+F5 after replacing an image if the old one is cached.

To change existing data, use Python's `sqlite3` module or a SQLite editor.
Editing `schema.sql` alone does not update an existing database. For a fresh local
sample database, stop the server, remove `products.db`, and start the server again.
This discards existing product data. Keep `schema.sql` in Git; the generated database is ignored.

## Page routes

- `/` or `/index.html`: homepage.
- `/products/index.html` or `/products/`: catalog.
- `/products/details?id=1`: serves `products/details.html`.
- `/products/details.html?id=1`: also works directly.

## API

| Request | Result |
| --- | --- |
| `GET /api/products` | JSON array of all products |
| `GET /api/products?q=sedan` | Case-insensitive search of names and descriptions |
| `GET /api/products/1` | JSON object for product 1 |

Product fields: `id`, `name`, `description`, `price_paise`, `image_url`, `stock`.
Successful requests return HTTP 200. Invalid IDs or search strings longer than
100 characters return 400. A valid ID with no matching product returns 404.
API errors use the shape `{"error": "message"}`; no search matches returns `[]`.
Search input is trimmed. SQLite's built-in case conversion handles ASCII text.

The browser reads the URL's `id`, requests `/api/products/<id>`, and displays the response.
Only Python connects to SQLite. SQL values use bound parameters. The server exposes
only the selected HTML and asset files, not the database, SQL, or Python source.

## Future work

Keep this structure while adding login: add a `users` table with unique emails and
password hashes, plus login/logout routes in `app.py`. Keep catalog browsing public.
Later, add cart tables referencing product IDs and user IDs, with server-side access checks.
Record future database alterations as separate SQL migration files as the course requires.

## Submission

Commit the source files, `schema.sql`, and this README. Capture screenshots of the
catalog and one product detail page for the assignment submission.
