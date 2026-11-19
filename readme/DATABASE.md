# Database schema and migrations

Run commands from the repository root. The application uses SQLite; no database server or SQL account is required.

## Application database

The default file is `products.db`. [schema.sql](../schema.sql) describes the final schema and sample products. Use Alembic for setup and upgrades, rather than importing this reference file over an existing database.

| Table | Purpose and constraints |
| --- | --- |
| `products` | Existing catalog: ID, name, description, integer `price_paise`, image URL and stock. Prices and stock cannot be negative. |
| `users` | ID, name, case-insensitive unique username, password hash and creation timestamp. Plaintext passwords are never stored. |
| `carts` | ID and unique user ID; one cart per user, with a foreign key to `users`. |
| `cart_items` | Composite primary key `(cart_id, product_id)`, quantity between 1 and 99, and foreign keys to carts and products. |
| `alembic_version` | Applied schema revision maintained by Alembic. |

The database enforces foreign keys and uniqueness. The backend additionally validates current stock and ownership. Prices are stored in paise (100 paise = ₹1) to avoid floating-point rounding. A session identifies the user; the cart's contents remain in SQL across logout, browser closure and application restarts.

## Apply migrations

```sh
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

Expected final revision: `0002_users_and_carts`. The application also runs the migration setup during initialization. For a custom database, set `DATABASE_PATH` consistently for both migration commands and application startup.

| Revision | Behavior |
| --- | --- |
| [0001_products](../migrations/versions/0001_products.py) | Adopts an existing Part 1 products table without replacing its records; seeds the catalog only when creating a fresh database. |
| [0002_users_and_carts](../migrations/versions/0002_users_and_carts.py) | Adds or adopts users, carts and cart items while preserving existing data. |

Configuration is in [alembic.ini](../alembic.ini), [migrations/env.py](../migrations/env.py), and [db_migrations.py](../db_migrations.py). Historical SQL files also remain in [migrations](../migrations), but Alembic revisions are the supported upgrade path. Migration transactions roll back on failure. Destructive downgrades are deliberately unsupported.

Before upgrading an important existing database, stop the application and make a backup of the database file. Do not delete it to resolve a migration or port error.

## Preservation evidence

[Migration tests](../tests/test_migrations.py) exercise upgrades of an existing Part 1 database, preservation of product records including custom values, adoption of existing user/cart records, and rollback after a failed upgrade. Run:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_migrations.py' -v
```

These tests use temporary databases; they do not reset your working catalog.

## Separate monitoring storage

| Storage | Contents |
| --- | --- |
| `monitoring/runtime/monitoring.db` | Structured operational events written asynchronously by the logging worker. |
| `monitoring/runtime/logs/application.jsonl` | Rotating structured JSON log files. |
| Prometheus data under `monitoring/runtime/` | Time-series metrics in Prometheus's own storage format. |
| Grafana data under `monitoring/runtime/` | Grafana settings and internal state, separate from application users. |

The monitoring event schema is initialized by [observability.py](../observability.py). It is independent of the application Alembic schema. Prometheus scrapes in-memory counters and histograms; it does not query `products.db`. Separating these stores avoids monitoring SQL traffic on the shopping database, though the processes still share the computer's CPU, memory and disk.

Runtime databases, generated secrets and binary downloads should not be committed. A fresh checkout reconstructs the schema, monitoring configuration and dashboard using the documented setup commands.
